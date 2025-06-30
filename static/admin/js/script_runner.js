// static/admin/js/script_runner.js

document.addEventListener('DOMContentLoaded', function() {
    const scriptCodeField = document.getElementById('id_script_code');
    const outputField = document.getElementById('id_output');
    
    if (scriptCodeField) {
        // Add basic editor enhancements
        initializeEditor(scriptCodeField);
        addQuickTemplates(scriptCodeField);
    }
    
    if (outputField) {
        // Add copy button for output
        addCopyButton(outputField);
    }
});

function initializeEditor(editor) {
    // Tab key handling for proper indentation
    editor.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            
            if (e.shiftKey) {
                // Shift+Tab: remove indentation
                const lines = this.value.substring(0, start).split('\n');
                const currentLine = lines[lines.length - 1];
                if (currentLine.startsWith('    ')) {
                    const newStart = start - 4;
                    this.value = this.value.substring(0, newStart) + 
                                this.value.substring(start);
                    this.selectionStart = this.selectionEnd = newStart;
                }
            } else {
                // Tab: add indentation
                this.value = this.value.substring(0, start) + '    ' + 
                           this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
            }
        }
        
        // Auto-indent on Enter
        if (e.key === 'Enter') {
            const lines = this.value.substring(0, this.selectionStart).split('\n');
            const currentLine = lines[lines.length - 1];
            const indentMatch = currentLine.match(/^(\s*)/);
            const currentIndent = indentMatch ? indentMatch[1] : '';
            
            // Add extra indent for colons
            const extraIndent = currentLine.trim().endsWith(':') ? '    ' : '';
            
            setTimeout(() => {
                const start = this.selectionStart;
                const newIndent = currentIndent + extraIndent;
                this.value = this.value.substring(0, start) + newIndent + 
                           this.value.substring(start);
                this.selectionStart = this.selectionEnd = start + newIndent.length;
            }, 0);
        }
    });
    
    // Add placeholder if empty
    if (!editor.value.trim()) {
        editor.placeholder = `# Write your Python script here
# Examples:
print("Hello World!")

# Pollinations AI image generation:
import urllib.parse
prompt = "Beautiful sunset"
encoded = urllib.parse.quote(prompt)
url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=768&model=flux"
print(f"Image URL: {url}")

# API testing:
result = api_test("https://httpbin.org/json")
print("API Response:", result)

# Database query:
users = db_query("SELECT COUNT(*) FROM auth_user")
print("Total users:", users)`;
    }
}

function addQuickTemplates(editor) {
    // Create templates button
    const templatesBtn = document.createElement('button');
    templatesBtn.type = 'button';
    templatesBtn.textContent = '📋 Quick Templates';
    templatesBtn.className = 'btn btn-secondary btn-sm';
    templatesBtn.style.margin = '10px 0';
    
    const templates = {
        'Pollinations AI': `# Pollinations AI Image Generator
import urllib.parse

def create_image_url(prompt, width=1024, height=768, model="flux"):
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model={model}&nologo=true"

# Generate images
prompts = ["Beautiful sunset", "Cute cat", "Mountain landscape"]
for prompt in prompts:
    url = create_image_url(prompt)
    print(f"{prompt}: {url}")`,

        'API Testing': `# API Testing Template
import json

def test_multiple_apis():
    apis = [
        "https://httpbin.org/json",
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://api.github.com/zen"
    ]
    
    for api_url in apis:
        result = api_test(api_url)
        print(f"\\n{api_url}:")
        print(f"Status: {result.get('status_code', 'Error')}")
        if 'error' not in result:
            print(f"Response: {str(result.get('content', ''))[:100]}...")

test_multiple_apis()`,

        'Database Stats': `# Database Analytics
def get_database_stats():
    try:
        # User statistics
        total_users = db_query("SELECT COUNT(*) FROM auth_user")[0][0]
        staff_users = db_query("SELECT COUNT(*) FROM auth_user WHERE is_staff = 1")[0][0]
        
        print(f"📊 Database Statistics:")
        print(f"   Total Users: {total_users}")
        print(f"   Staff Users: {staff_users}")
        
        # Script statistics
        total_scripts = db_query("SELECT COUNT(*) FROM api_scriptrunner")[0][0]
        print(f"   Total Scripts: {total_scripts}")
        
    except Exception as e:
        print(f"Error: {e}")

get_database_stats()`,

        'Data Generation': `# Test Data Generator
import random
from datetime import datetime, timedelta

def generate_sample_data():
    # Generate names
    names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']
    
    # Generate emails
    domains = ['example.com', 'test.org', 'demo.net']
    
    print("📋 Generated Test Data:")
    for i in range(5):
        name = random.choice(names)
        email = f"{name.lower()}{i}@{random.choice(domains)}"
        age = random.randint(18, 65)
        
        print(f"   {name} ({age}) - {email}")

generate_sample_data()`
    };
    
    templatesBtn.addEventListener('click', function() {
        const templateNames = Object.keys(templates);
        const choice = prompt(`Choose a template:\\n${templateNames.map((name, i) => `${i+1}. ${name}`).join('\\n')}`);
        
        if (choice) {
            const selectedTemplate = templateNames.find(name => 
                name.toLowerCase().includes(choice.toLowerCase()) ||
                choice === String(templateNames.indexOf(name) + 1)
            );
            
            if (selectedTemplate) {
                editor.value = templates[selectedTemplate];
                editor.focus();
                showNotification(`✅ ${selectedTemplate} template loaded!`);
            }
        }
    });
    
    // Insert button after the editor
    editor.parentNode.appendChild(templatesBtn);
}

function addCopyButton(output) {
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.textContent = '📋 Copy Output';
    copyBtn.className = 'btn btn-secondary btn-sm';
    copyBtn.style.margin = '10px 0';
    
    copyBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(output.value).then(() => {
            showNotification('📋 Output copied to clipboard!');
        }).catch(() => {
            // Fallback for older browsers
            output.select();
            document.execCommand('copy');
            showNotification('📋 Output copied!');
        });
    });
    
    output.parentNode.appendChild(copyBtn);
}

function showNotification(message) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        z-index: 9999;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}