# Screenshot-to-Code with AWS Bedrock

This application uses AWS Bedrock with Claude 3.7 Sonnet's vision capabilities to convert UI screenshots into HTML, CSS, and JavaScript code.

## Features

- Upload UI screenshots or provide image URLs
- Generate HTML/CSS/JS code using AWS Bedrock and Claude 3.7
- Multiple framework support (Default, Bootstrap, Tailwind CSS, Material UI)
- Responsive design options
- Animation and dark mode support
- Project history and management
- Code preview with responsive testing
- Export projects as complete packages

## Architecture

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│               │     │               │     │               │     │               │
│  Flask App    │────▶│  AWS Bedrock  │────▶│  Claude 3.7   │────▶│  HTML/CSS/JS  │
│               │     │               │     │   Sonnet      │     │  Generation   │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
```

## Prerequisites

- Python 3.8+
- AWS account with access to Amazon Bedrock
- AWS credentials with permissions to invoke Bedrock models, specifically Claude 3.7 Sonnet

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/screenshot-to-code.git
   cd screenshot-to-code
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:
   - Copy `.env.example` to `.env`
   - Update the AWS credentials in the `.env` file with your own credentials
   - **IMPORTANT**: Never commit your `.env` file to version control

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Upload a screenshot or provide an image URL
2. Choose your preferred framework (Default, Bootstrap, Tailwind, Material UI)
3. Configure options (responsive design, animations, dark mode)
4. Click "Generate Code"
5. View the generated HTML, CSS, and JavaScript code
6. Test the responsive design with desktop, tablet, and mobile views
7. Save or export your project

## AWS Bedrock Configuration

This application uses the Claude 3.7 Sonnet model from Anthropic via AWS Bedrock. Make sure your AWS account has:

1. Access to AWS Bedrock service
2. Permissions to invoke the Claude 3.7 Sonnet model
3. Proper IAM roles configured

## Project Structure

```
screenshot-to-code/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore file
├── README.md              # Project documentation
├── static/                # Static assets
│   ├── style.css          # CSS for the web interface
│   └── script.js          # JavaScript for the web interface
├── templates/             # HTML templates
│   ├── index.html         # Main page
│   ├── history.html       # Project history page
│   ├── project.html       # Project view page
│   └── error.html         # Error page
├── uploads/               # Uploaded images (not in version control)
├── history/               # Saved projects (not in version control)
└── exports/               # Exported projects (not in version control)
```

## Security Notes

- The application stores uploaded images and generated code locally
- AWS credentials should be kept secure and never committed to version control
- Use proper IAM roles and permissions for AWS Bedrock access

## License

MIT
