import os
import json
import base64
import boto3
from flask import Flask, render_template, request, jsonify
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# Configure AWS Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

# Claude model ID - use the latest available Claude model with vision capabilities
MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'  # Update as needed

def process_image(image_data):
    """
    Process the image and convert to base64 for Bedrock API
    """
    # Open the image using PIL
    img = Image.open(BytesIO(image_data))
    
    # Resize if needed (optional)
    max_size = 2000  # Claude has an 8000px limit, but we'll use a smaller size
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Convert to JPEG format
    buffer = BytesIO()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    
    # Convert to base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64

def generate_code_from_image(image_base64):
    """
    Use AWS Bedrock with Claude to generate HTML/CSS code from the image
    """
    prompt = """
    You are an expert front-end developer. I'm showing you a screenshot of a user interface.
    
    Please analyze this image and generate the exact HTML and CSS code needed to recreate this interface.
    
    Follow these guidelines:
    1. Use modern HTML5 and CSS3 practices
    2. Make the design responsive
    3. Use semantic HTML elements where appropriate
    4. Include any necessary CSS for styling
    5. Organize the CSS in a clean, maintainable way
    6. Add helpful comments to explain your code
    7. If there are interactive elements like buttons, add basic functionality
    
    Return your response in the following format:
    
    ```html
    <!-- Your HTML code here -->
    ```
    
    ```css
    /* Your CSS code here */
    ```
    
    If you need to make any assumptions about the design, please note them briefly.
    """
    
    try:
        # Prepare the request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Call Bedrock with Claude model
        response = bedrock_runtime.invoke_model(
            body=json.dumps(request_body),
            modelId=MODEL_ID
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        generated_text = response_body['content'][0]['text']
        
        # Extract HTML and CSS from the response
        html_code = ""
        css_code = ""
        
        # Parse the response to extract HTML and CSS code blocks
        if "```html" in generated_text and "```css" in generated_text:
            html_start = generated_text.find("```html") + 7
            html_end = generated_text.find("```", html_start)
            html_code = generated_text[html_start:html_end].strip()
            
            css_start = generated_text.find("```css") + 7
            css_end = generated_text.find("```", css_start)
            css_code = generated_text[css_start:css_end].strip()
        
        return {
            "html": html_code,
            "css": css_code,
            "full_response": generated_text
        }
        
    except Exception as e:
        print(f"Error generating code: {str(e)}")
        return {
            "error": str(e),
            "html": "",
            "css": ""
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "No image selected"}), 400
    
    try:
        # Read and process the image
        image_data = image_file.read()
        image_base64 = process_image(image_data)
        
        # Generate code from the image
        result = generate_code_from_image(image_base64)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
