// static/admin/js/script_runner.js - Django Unfold Compatible

document.addEventListener('DOMContentLoaded', function() {
    const scriptCodeField = document.getElementById('id_script_code');
    const outputField = document.getElementById('id_output');
    
    if (scriptCodeField) {
        // Add line numbers and better editing experience
        scriptCodeField.addEventListener('keydown', function(e) {
            // Tab key handling for proper indentation
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                
                this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
            }
            
            // Auto-indent on Enter
            if (e.key === 'Enter') {
                const lines = this.value.substring(0, this.selectionStart).split('\n');
                const currentLine = lines[lines.length - 1];
                const indentMatch = currentLine.match(/^(\s*)/);
                const currentIndent = indentMatch ? indentMatch[1] : '';
                
                // Add extra indent for colons (if, for, def, etc.)
                const extraIndent = currentLine.trim().endsWith(':') ? '    ' : '';
                
                setTimeout(() => {
                    const start = this.selectionStart;
                    this.value = this.value.substring(0, start) + currentIndent + extraIndent + this.value.substring(start);
                    this.selectionStart = this.selectionEnd = start + currentIndent.length + extraIndent.length;
                }, 0);
            }
        });
        
        // Add placeholder text
        if (!scriptCodeField.value) {
            scriptCodeField.placeholder = `# Write your Python script here
# Example:
print("Hello World!")
import datetime
print("Current time:", datetime.datetime.now())

# You can use Django models:
# from django.contrib.auth.models import User
# print("Total users:", User.objects.count())`;
        }
    }
    
    // Auto-scroll output to bottom
    if (outputField && outputField.value) {
        outputField.scrollTop = outputField.scrollHeight;
    }
    
    // Add execute button near the script field (optional)
    if (scriptCodeField) {
        const executeButton = document.createElement('button');
        executeButton.type = 'button';
        executeButton.className = 'btn btn-primary btn-sm';
        executeButton.textContent = 'Quick Execute';
        executeButton.style.marginTop = '10px';
        executeButton.style.marginLeft = '5px';
        
        executeButton.addEventListener('click', function() {
            // You could add AJAX execution here if needed
            alert('Use the "Execute Selected Scripts" action from the admin actions dropdown');
        });
        
        scriptCodeField.parentNode.appendChild(executeButton);
    }
});

// Add syntax highlighting classes (basic)
document.addEventListener('DOMContentLoaded', function() {
    const scriptField = document.getElementById('id_script_code');
    if (scriptField) {
        scriptField.addEventListener('input', function() {
            // Basic syntax highlighting could be added here
            // For now, just ensure proper formatting
        });
    }
});