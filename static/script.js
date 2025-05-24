document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const imageUpload = document.getElementById('imageUpload');
    const imagePreview = document.getElementById('imagePreview');
    const preview = document.getElementById('preview');
    const generateBtn = document.getElementById('generateBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const codeOutput = document.getElementById('codeOutput');
    const errorMessage = document.getElementById('errorMessage');
    const htmlCode = document.getElementById('htmlCode');
    const cssCode = document.getElementById('cssCode');
    const previewFrame = document.getElementById('previewFrame');
    const copyHtmlBtn = document.getElementById('copyHtmlBtn');
    const copyCssBtn = document.getElementById('copyCssBtn');

    // Handle image upload and preview
    imageUpload.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                preview.src = e.target.result;
                imagePreview.classList.remove('d-none');
            };
            
            reader.readAsDataURL(this.files[0]);
        }
    });

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!imageUpload.files || !imageUpload.files[0]) {
            showError('Please select an image first.');
            return;
        }
        
        const formData = new FormData();
        formData.append('image', imageUpload.files[0]);
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        codeOutput.classList.add('d-none');
        errorMessage.classList.add('d-none');
        generateBtn.disabled = true;
        
        // Send request to server
        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server error: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            // Display the generated code
            htmlCode.textContent = data.html;
            cssCode.textContent = data.css;
            
            // Create preview
            updatePreview(data.html, data.css);
            
            // Show code output
            loadingIndicator.classList.add('d-none');
            codeOutput.classList.remove('d-none');
            generateBtn.disabled = false;
            
            // Initialize syntax highlighting
            document.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        })
        .catch(error => {
            showError(error.message);
            generateBtn.disabled = false;
        });
    });

    // Copy buttons functionality
    copyHtmlBtn.addEventListener('click', function() {
        copyToClipboard(htmlCode.textContent);
        showCopyTooltip(this);
    });
    
    copyCssBtn.addEventListener('click', function() {
        copyToClipboard(cssCode.textContent);
        showCopyTooltip(this);
    });

    // Helper functions
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
        loadingIndicator.classList.add('d-none');
        codeOutput.classList.add('d-none');
    }
    
    function updatePreview(html, css) {
        const frameDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
        frameDoc.open();
        frameDoc.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <style>${css}</style>
            </head>
            <body>${html}</body>
            </html>
        `);
        frameDoc.close();
    }
    
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).catch(err => {
            console.error('Could not copy text: ', err);
        });
    }
    
    function showCopyTooltip(button) {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 2000);
    }
});
