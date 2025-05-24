import os
import json
import base64
import boto3
import uuid
import requests
import datetime
import shutil
from flask import Flask, render_template, request, jsonify, send_file, url_for
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure AWS Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

# Claude model ID - use Claude 3.7 Sonnet
MODEL_ID = 'anthropic.claude-3-7-sonnet-20240620-v1:0'  # Updated to Claude 3.7

# Configure upload folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
HISTORY_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history')
EXPORT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Custom template filters
@app.template_filter('datetime')
def format_datetime(value):
    """Format ISO datetime string to readable format"""
    if not value:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(value)
        return dt.strftime("%b %d, %Y at %H:%M")
    except:
        return value

def allowed_file(filename):
    """
    Check if the file has an allowed extension
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_project(project_id, image_path, html_code, css_code, js_code, framework, metadata):
    """
    Save project data to the history folder
    """
    project_folder = os.path.join(HISTORY_FOLDER, project_id)
    os.makedirs(project_folder, exist_ok=True)
    
    # Save image
    if image_path and os.path.exists(image_path):
        shutil.copy2(image_path, os.path.join(project_folder, 'screenshot.jpg'))
    
    # Save code files
    with open(os.path.join(project_folder, 'index.html'), 'w') as f:
        f.write(html_code)
    
    with open(os.path.join(project_folder, 'style.css'), 'w') as f:
        f.write(css_code)
    
    if js_code:
        with open(os.path.join(project_folder, 'script.js'), 'w') as f:
            f.write(js_code)
    
    # Save metadata
    with open(os.path.join(project_folder, 'metadata.json'), 'w') as f:
        json.dump(metadata, f)
    
    return project_folder

def get_projects():
    """
    Get list of saved projects
    """
    projects = []
    
    if os.path.exists(HISTORY_FOLDER):
        for project_id in os.listdir(HISTORY_FOLDER):
            project_folder = os.path.join(HISTORY_FOLDER, project_id)
            metadata_file = os.path.join(project_folder, 'metadata.json')
            
            if os.path.isdir(project_folder) and os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        
                    screenshot_path = os.path.join(project_folder, 'screenshot.jpg')
                    has_screenshot = os.path.exists(screenshot_path)
                    
                    projects.append({
                        'id': project_id,
                        'name': metadata.get('name', 'Unnamed Project'),
                        'created_at': metadata.get('created_at'),
                        'framework': metadata.get('framework', 'default'),
                        'has_screenshot': has_screenshot
                    })
                except Exception as e:
                    print(f"Error loading project {project_id}: {str(e)}")
    
    # Sort by creation date (newest first)
    projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return projects

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

def download_image(url):
    """
    Download image from URL
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Check if the content is an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"URL does not point to an image (Content-Type: {content_type})")
        
        return response.content
    except Exception as e:
        raise Exception(f"Failed to download image: {str(e)}")

def generate_code_from_image(image_base64, framework="default", responsive=True, animations=False, dark_mode=False):
    """
    Use AWS Bedrock with Claude to generate HTML/CSS code from the image
    """
    # Base prompt
    prompt = f"""
    You are an expert front-end developer. I'm showing you a screenshot of a user interface.
    
    Please analyze this image and generate the exact HTML and CSS code needed to recreate this interface.
    
    Framework: {framework}
    Responsive Design: {"Yes" if responsive else "No"}
    Include Animations: {"Yes" if animations else "No"}
    Dark Mode Support: {"Yes" if dark_mode else "No"}
    
    Follow these guidelines:
    1. Use modern HTML5 and CSS3 practices
    2. {"Make the design responsive with mobile-first approach" if responsive else "Focus on desktop layout only"}
    3. Use semantic HTML elements where appropriate
    4. Include any necessary CSS for styling
    5. Organize the CSS in a clean, maintainable way
    6. Add helpful comments to explain your code
    7. If there are interactive elements like buttons, add basic functionality
    """
    
    # Framework-specific instructions
    if framework == "bootstrap":
        prompt += """
        8. Use Bootstrap 5 for styling and components
        9. Include the necessary Bootstrap CDN links
        10. Utilize Bootstrap's grid system and utility classes
        """
    elif framework == "tailwind":
        prompt += """
        8. Use Tailwind CSS for styling
        9. Include the necessary Tailwind CDN links
        10. Use Tailwind's utility classes for all styling
        """
    elif framework == "material":
        prompt += """
        8. Use Material UI styling and components
        9. Include the necessary Material UI CDN links
        10. Follow Material Design principles
        """
    
    # Animation instructions
    if animations:
        prompt += """
        11. Add subtle animations for interactive elements
        12. Use CSS transitions for smooth effects
        13. Consider adding hover animations for buttons and links
        """
    
    # Dark mode instructions
    if dark_mode:
        prompt += """
        14. Implement dark mode support using CSS variables
        15. Provide a toggle mechanism for switching between light and dark modes
        16. Ensure good contrast in both modes
        """
    
    prompt += """
    Return your response in the following format:
    
    ```html
    <!-- Your HTML code here -->
    ```
    
    ```css
    /* Your CSS code here */
    ```
    
    ```javascript
    // Your JavaScript code here (if needed)
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
        
        # Extract HTML, CSS, and JavaScript from the response
        html_code = ""
        css_code = ""
        js_code = ""
        
        # Parse the response to extract code blocks
        if "```html" in generated_text:
            html_start = generated_text.find("```html") + 7
            html_end = generated_text.find("```", html_start)
            html_code = generated_text[html_start:html_end].strip()
        
        if "```css" in generated_text:
            css_start = generated_text.find("```css") + 7
            css_end = generated_text.find("```", css_start)
            css_code = generated_text[css_start:css_end].strip()
        
        if "```javascript" in generated_text:
            js_start = generated_text.find("```javascript") + 14
            js_end = generated_text.find("```", js_start)
            js_code = generated_text[js_start:js_end].strip()
        elif "```js" in generated_text:
            js_start = generated_text.find("```js") + 6
            js_end = generated_text.find("```", js_start)
            js_code = generated_text[js_start:js_end].strip()
        
        return {
            "html": html_code,
            "css": css_code,
            "js": js_code,
            "full_response": generated_text
        }
        
    except Exception as e:
        print(f"Error generating code: {str(e)}")
        return {
            "error": str(e),
            "html": "",
            "css": "",
            "js": ""
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    projects = get_projects()
    return render_template('history.html', projects=projects)

@app.route('/project/<project_id>')
def view_project(project_id):
    project_folder = os.path.join(HISTORY_FOLDER, project_id)
    
    if not os.path.exists(project_folder):
        return render_template('error.html', message="Project not found"), 404
    
    try:
        # Load metadata
        with open(os.path.join(project_folder, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        # Load code files
        with open(os.path.join(project_folder, 'index.html'), 'r') as f:
            html_code = f.read()
        
        with open(os.path.join(project_folder, 'style.css'), 'r') as f:
            css_code = f.read()
        
        # Load JavaScript if it exists
        js_code = ""
        js_path = os.path.join(project_folder, 'script.js')
        if os.path.exists(js_path):
            with open(js_path, 'r') as f:
                js_code = f.read()
        
        # Check if screenshot exists
        screenshot_path = os.path.join(project_folder, 'screenshot.jpg')
        has_screenshot = os.path.exists(screenshot_path)
        
        return render_template(
            'project.html',
            project_id=project_id,
            metadata=metadata,
            html_code=html_code,
            css_code=css_code,
            js_code=js_code,
            has_screenshot=has_screenshot
        )
    
    except Exception as e:
        return render_template('error.html', message=f"Error loading project: {str(e)}"), 500

@app.route('/project/<project_id>/screenshot')
def project_screenshot(project_id):
    screenshot_path = os.path.join(HISTORY_FOLDER, project_id, 'screenshot.jpg')
    
    if os.path.exists(screenshot_path):
        return send_file(screenshot_path, mimetype='image/jpeg')
    else:
        return '', 404

@app.route('/project/<project_id>/export')
def export_project(project_id):
    project_folder = os.path.join(HISTORY_FOLDER, project_id)
    
    if not os.path.exists(project_folder):
        return jsonify({"error": "Project not found"}), 404
    
    try:
        # Create export folder for this project
        export_folder = os.path.join(EXPORT_FOLDER, project_id)
        os.makedirs(export_folder, exist_ok=True)
        
        # Copy project files
        for file_name in ['index.html', 'style.css', 'script.js', 'screenshot.jpg']:
            src_path = os.path.join(project_folder, file_name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(export_folder, file_name))
        
        # Create a zip file
        zip_path = os.path.join(EXPORT_FOLDER, f"{project_id}.zip")
        shutil.make_archive(zip_path[:-4], 'zip', export_folder)
        
        return send_file(zip_path, as_attachment=True, download_name=f"screenshot-to-code-{project_id}.zip")
    
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route('/generate', methods=['POST'])
def generate():
    # Get form data
    framework = request.form.get('framework', 'default')
    responsive = request.form.get('responsive', 'true') == 'true'
    animations = request.form.get('animations', 'false') == 'true'
    dark_mode = request.form.get('darkMode', 'false') == 'true'
    
    # Generate a unique project ID
    project_id = str(uuid.uuid4())
    
    # Process image from file upload or URL
    image_data = None
    image_path = None
    
    if 'image' in request.files and request.files['image'].filename:
        # Process uploaded file
        image_file = request.files['image']
        
        if not allowed_file(image_file.filename):
            return jsonify({"error": "Invalid file format. Allowed formats: png, jpg, jpeg, gif, webp"}), 400
        
        # Save the uploaded file
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, f"{project_id}_{filename}")
        image_file.save(image_path)
        
        # Read the image data
        with open(image_path, 'rb') as f:
            image_data = f.read()
    
    elif 'imageUrl' in request.form and request.form['imageUrl']:
        # Process image from URL
        try:
            image_url = request.form['imageUrl']
            image_data = download_image(image_url)
            
            # Save the downloaded image
            image_path = os.path.join(UPLOAD_FOLDER, f"{project_id}_from_url.jpg")
            with open(image_path, 'wb') as f:
                f.write(image_data)
        
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    else:
        return jsonify({"error": "No image provided. Please upload an image or provide an image URL"}), 400
    
    try:
        # Process the image for Bedrock API
        image_base64 = process_image(image_data)
        
        # Generate code from the image
        result = generate_code_from_image(
            image_base64,
            framework=framework,
            responsive=responsive,
            animations=animations,
            dark_mode=dark_mode
        )
        
        if 'error' in result and result['error']:
            return jsonify(result), 500
        
        # Save the project
        metadata = {
            'name': request.form.get('projectName', 'Untitled Project'),
            'created_at': datetime.datetime.now().isoformat(),
            'framework': framework,
            'responsive': responsive,
            'animations': animations,
            'dark_mode': dark_mode
        }
        
        save_project(
            project_id,
            image_path,
            result['html'],
            result['css'],
            result.get('js', ''),
            framework,
            metadata
        )
        
        # Add project ID to the result
        result['project_id'] = project_id
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-project/<project_id>', methods=['POST'])
def delete_project(project_id):
    project_folder = os.path.join(HISTORY_FOLDER, project_id)
    
    if not os.path.exists(project_folder):
        return jsonify({"error": "Project not found"}), 404
    
    try:
        # Delete the project folder
        shutil.rmtree(project_folder)
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"error": f"Failed to delete project: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
