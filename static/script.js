document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const uploadForm = document.getElementById('uploadForm');
    const imageUpload = document.getElementById('imageUpload');
    const imageUrl = document.getElementById('imageUrl');
    const imagePreview = document.getElementById('imagePreview');
    const preview = document.getElementById('preview');
    const generateBtn = document.getElementById('generateBtn');
    
    // Output elements
    const loadingIndicator = document.getElementById('loadingIndicator');
    const progressBar = loadingIndicator.querySelector('.progress-bar');
    const codeOutput = document.getElementById('codeOutput');
    const errorMessage = document.getElementById('errorMessage');
    const htmlCode = document.getElementById('htmlCode');
    const cssCode = document.getElementById('cssCode');
    const jsCode = document.getElementById('jsCode');
    const jsTabItem = document.getElementById('js-tab-item');
    const copyJsBtn = document.getElementById('copyJsBtn');
    const previewFrame = document.getElementById('previewFrame');
    
    // Action buttons
    const copyHtmlBtn = document.getElementById('copyHtmlBtn');
    const copyCssBtn = document.getElementById('copyCssBtn');
    const saveProjectBtn = document.getElementById('saveProjectBtn');
    const exportBtn = document.getElementById('exportBtn');
    
    // Current project ID
    let currentProjectId = null;

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
    
    // Handle image URL input
    imageUrl.addEventListener('change', function() {
        if (this.value) {
            preview.src = this.value;
            imagePreview.classList.remove('d-none');
        }
    });

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate input
        const isFileUpload = document.getElementById('upload-tab').classList.contains('active');
        
        if (isFileUpload && (!imageUpload.files || !imageUpload.files[0])) {
            showError('Please select an image file.');
            return;
        }
        
        if (!isFileUpload && !imageUrl.value) {
            showError('Please enter an image URL.');
            return;
        }
        
        // Create form data
        const formData = new FormData();
        
        // Add project name
        const projectName = document.getElementById('projectName').value || 'Untitled Project';
        formData.append('projectName', projectName);
        
        // Add image (file or URL)
        if (isFileUpload) {
            formData.append('image', imageUpload.files[0]);
        } else {
            formData.append('imageUrl', imageUrl.value);
        }
        
        // Add framework selection
        const framework = document.querySelector('input[name="framework"]:checked').value;
        formData.append('framework', framework);
        
        // Add options
        const responsive = document.getElementById('responsiveCheck').checked;
        const animations = document.getElementById('animationsCheck').checked;
        const darkMode = document.getElementById('darkModeCheck').checked;
        
        formData.append('responsive', responsive);
        formData.append('animations', animations);
        formData.append('darkMode', darkMode);
        
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        codeOutput.classList.add('d-none');
        errorMessage.classList.add('d-none');
        generateBtn.disabled = true;
        
        // Reset progress bar
        progressBar.style.width = '0%';
        
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
            
            // Store project ID
            currentProjectId = data.project_id;
            
            // Update export button
            if (currentProjectId) {
                exportBtn.href = `/project/${currentProjectId}/export`;
                saveProjectBtn.href = `/project/${currentProjectId}`;
            }
            
            // Display the generated code
            htmlCode.textContent = data.html;
            cssCode.textContent = data.css;
            
            // Handle JavaScript if present
            if (data.js && data.js.trim()) {
                jsCode.textContent = data.js;
                jsTabItem.classList.remove('d-none');
                copyJsBtn.classList.remove('d-none');
            } else {
                jsTabItem.classList.add('d-none');
                copyJsBtn.classList.add('d-none');
            }
            
            // Create preview
            updatePreview(data.html, data.css, data.js || '');
            
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
    
    copyJsBtn.addEventListener('click', function() {
        copyToClipboard(jsCode.textContent);
        showCopyTooltip(this);
    });
    
    // Handle device preview buttons
    document.querySelectorAll('.preview-controls button').forEach(button => {
        button.addEventListener('click', function() {
            const device = this.dataset.device;
            const container = document.querySelector('.preview-container');
            
            // Remove all device classes
            container.classList.remove('desktop', 'tablet', 'mobile');
            
            // Add the selected device class
            container.classList.add(device);
            
            // Update active button
            document.querySelectorAll('.preview-controls button').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    // Helper functions
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('d-none');
        loadingIndicator.classList.add('d-none');
        codeOutput.classList.add('d-none');
    }
    
    function updatePreview(html, css, js) {
        const frameDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
        frameDoc.open();
        frameDoc.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>${css}</style>
            </head>
            <body>
                ${html}
                <script>${js}</script>
            </body>
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
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check"></i> Copied!';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 2000);
    }
});
