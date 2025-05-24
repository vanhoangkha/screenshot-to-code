import os
import json
import base64
import boto3
import uuid
import requests
import datetime
import shutil
import logging
from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure AWS Bedrock client with proper error handling
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    logger.info("AWS Bedrock client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS Bedrock client: {str(e)}")
    bedrock_runtime = None

# Claude model ID - use Claude 3.7 Sonnet
MODEL_ID = 'anthropic.claude-3-7-sonnet-20240620-v1:0'

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

# Maximum file size (5MB)
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

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

def clean_old_files(folder, max_age_days=7):
    """
    Clean up old files from a folder
    """
    now = datetime.datetime.now()
    count = 0
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            file_age = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            if (now - file_age).days > max_age_days:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {str(e)}")
    
    return count

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
                    logger.error(f"Error loading project {project_id}: {str(e)}")
    
    # Sort by creation date (newest first)
    projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return projects
def process_image(image_data):
    """
    Process the image and convert to base64 for Bedrock API
    """
    try:
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
        img.save(buffer, format="JPEG", quality=85)  # Reduced quality for smaller size
        buffer.seek(0)
        
        # Convert to base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_base64
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise ValueError(f"Failed to process image: {str(e)}")

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
        
        # Check file size
        content_length = int(response.headers.get('Content-Length', 0))
        if content_length > MAX_CONTENT_LENGTH:
            raise ValueError(f"Image is too large ({content_length / (1024 * 1024):.2f}MB). Maximum size is 5MB.")
        
        return response.content
    except requests.RequestException as e:
        logger.error(f"Error downloading image: {str(e)}")
        raise Exception(f"Failed to download image: {str(e)}")

def generate_code_from_image(image_base64, framework="default", responsive=True, animations=False, dark_mode=False):
    """
    Use AWS Bedrock with Claude to generate HTML/CSS code from the image
    """
    if not bedrock_runtime:
        raise Exception("AWS Bedrock client is not initialized. Check your credentials.")
        
    # Base prompt
    prompt = f"""
    You are an expert front-end developer. I'm showing you a screenshot of a user interface.
    
    Please analyze this image and generate the exact HTML, CSS, and JavaScript code needed to recreate this interface.
    
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
    8. Pay close attention to details like fonts, spacing, colors, and alignment
    9. Ensure the code is accessible and follows best practices
    10. Optimize the code for performance
    """
    # Framework-specific instructions
    if framework == "bootstrap":
        prompt += """
        11. Use Bootstrap 5 for styling and components
        12. Include the necessary Bootstrap CDN links
        13. Utilize Bootstrap's grid system and utility classes
        14. Follow Bootstrap's component guidelines
        """
    elif framework == "tailwind":
        prompt += """
        11. Use Tailwind CSS for styling
        12. Include the necessary Tailwind CDN links
        13. Use Tailwind's utility classes for all styling
        14. Follow Tailwind's design patterns
        """
    elif framework == "material":
        prompt += """
        11. Use Material UI styling and components
        12. Include the necessary Material UI CDN links
        13. Follow Material Design principles
        14. Use appropriate Material Design icons
        """
    
    # Animation instructions
    if animations:
        prompt += """
        15. Add subtle animations for interactive elements
        16. Use CSS transitions for smooth effects
        17. Consider adding hover animations for buttons and links
        18. Ensure animations are not excessive or distracting
        """
    
    # Dark mode instructions
    if dark_mode:
        prompt += """
        19. Implement dark mode support using CSS variables
        20. Provide a toggle mechanism for switching between light and dark modes
        21. Ensure good contrast in both modes
        22. Use appropriate color schemes for each mode
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
        logger.info(f"Generating code with framework: {framework}, responsive: {responsive}, animations: {animations}, dark_mode: {dark_mode}")
        
        # Prepare the request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.2,  # Lower temperature for more consistent results
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
        
        logger.info("Code generation successful")
        
        return {
            "html": html_code,
            "css": css_code,
            "js": js_code,
            "full_response": generated_text
        }
        
    except Exception as e:
        logger.error(f"Error generating code: {str(e)}")
        return {
            "error": str(e),
            "html": "",
            "css": "",
            "js": ""
        }
@app.route('/')
def index():
    # Clean up old files
    try:
        uploads_cleaned = clean_old_files(UPLOAD_FOLDER)
        exports_cleaned = clean_old_files(EXPORT_FOLDER)
        if uploads_cleaned > 0 or exports_cleaned > 0:
            logger.info(f"Cleaned up {uploads_cleaned} old uploads and {exports_cleaned} old exports")
    except Exception as e:
        logger.error(f"Error cleaning up old files: {str(e)}")
    
    return render_template('index.html')

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring
    """
    status = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "bedrock_client": "initialized" if bedrock_runtime else "not initialized"
    }
    return jsonify(status)

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
        logger.error(f"Error loading project {project_id}: {str(e)}")
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
        logger.error(f"Export failed for project {project_id}: {str(e)}")
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
            logger.error(f"Error processing image URL: {str(e)}")
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
        logger.error(f"Error in generate endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
@app.route('/delete-project/<project_id>', methods=['POST'])
def delete_project(project_id):
    project_folder = os.path.join(HISTORY_FOLDER, project_id)
    
    if not os.path.exists(project_folder):
        return jsonify({"error": "Project not found"}), 404
    
    try:
        # Delete the project folder
        shutil.rmtree(project_folder)
        logger.info(f"Project {project_id} deleted successfully")
        return jsonify({"success": True})
    
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {str(e)}")
        return jsonify({"error": f"Failed to delete project: {str(e)}"}), 500

@app.route('/duplicate-project/<project_id>', methods=['POST'])
def duplicate_project(project_id):
    source_folder = os.path.join(HISTORY_FOLDER, project_id)
    
    if not os.path.exists(source_folder):
        return jsonify({"error": "Project not found"}), 404
    
    try:
        # Generate a new project ID
        new_project_id = str(uuid.uuid4())
        target_folder = os.path.join(HISTORY_FOLDER, new_project_id)
        
        # Copy the project folder
        shutil.copytree(source_folder, target_folder)
        
        # Update metadata
        metadata_path = os.path.join(target_folder, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            metadata['name'] = f"Copy of {metadata.get('name', 'Untitled Project')}"
            metadata['created_at'] = datetime.datetime.now().isoformat()
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
        
        logger.info(f"Project {project_id} duplicated as {new_project_id}")
        return jsonify({"success": True, "new_project_id": new_project_id})
    
    except Exception as e:
        logger.error(f"Failed to duplicate project {project_id}: {str(e)}")
        return jsonify({"error": f"Failed to duplicate project: {str(e)}"}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('error.html', message="File too large. Maximum size is 5MB."), 413

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', message="Page not found."), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', message="Internal server error. Please try again later."), 500

if __name__ == '__main__':
    # Clean up old files on startup
    try:
        uploads_cleaned = clean_old_files(UPLOAD_FOLDER)
        exports_cleaned = clean_old_files(EXPORT_FOLDER)
        logger.info(f"Startup cleanup: removed {uploads_cleaned} old uploads and {exports_cleaned} old exports")
    except Exception as e:
        logger.error(f"Error during startup cleanup: {str(e)}")
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(debug=debug, host='0.0.0.0', port=port)
