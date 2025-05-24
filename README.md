# Screenshot-to-Code with AWS Bedrock

This application uses AWS Bedrock with Claude's vision capabilities to convert UI screenshots into HTML and CSS code.

## Features

- Upload UI screenshots
- Generate HTML/CSS code using AWS Bedrock and Claude
- Preview the generated code
- Copy code to clipboard

## Architecture

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│               │     │               │     │               │     │               │
│  Flask App    │────▶│  AWS Bedrock  │────▶│    Claude     │────▶│  HTML/CSS     │
│               │     │               │     │               │     │  Generation   │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
```

## Prerequisites

- Python 3.8+
- AWS account with access to Amazon Bedrock
- AWS credentials with permissions to invoke Bedrock models

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
   - Update the AWS credentials in the `.env` file

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Upload a screenshot of a UI design
2. Click "Generate Code"
3. View the generated HTML and CSS code
4. Use the preview tab to see how the code renders
5. Copy the code to your clipboard using the copy buttons

## AWS Bedrock Configuration

This application uses the Claude 3 Sonnet model from Anthropic via AWS Bedrock. Make sure your AWS account has:

1. Access to AWS Bedrock service
2. Permissions to invoke the Claude 3 Sonnet model
3. Proper IAM roles configured

## Customization

You can modify the prompt in the `generate_code_from_image` function in `app.py` to customize the code generation instructions.

## License

MIT
