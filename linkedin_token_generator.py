#!/usr/bin/env python3
"""
Simple web server to help generate LinkedIn access tokens.
Run this script and follow the instructions to get your LinkedIn access token.
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import requests
import json
import sys
from urllib.parse import urlparse, parse_qs

class LinkedInTokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_main_page()
        elif parsed_path.path == '/callback':
            self.handle_callback(parsed_path.query)
        else:
            self.send_error(404)
    
    def serve_main_page(self):
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>LinkedIn Token Generator</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .step { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .code { background: #e8e8e8; padding: 10px; font-family: monospace; border-radius: 3px; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        input[type="text"] { width: 300px; padding: 5px; }
        button { background: #0077b5; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        button:hover { background: #005885; }
    </style>
</head>
<body>
    <h1>🔗 LinkedIn Access Token Generator</h1>
    
    <div class="step">
        <h3>Step 1: Enter Your LinkedIn App Credentials</h3>
        <form id="tokenForm">
            <p>
                <label>Client ID:</label><br>
                <input type="text" id="clientId" placeholder="Your LinkedIn app Client ID" required>
            </p>
            <p>
                <label>Client Secret:</label><br>
                <input type="text" id="clientSecret" placeholder="Your LinkedIn app Client Secret" required>
            </p>
            <p>
                <button type="button" onclick="generateAuthUrl()">Generate Authorization URL</button>
            </p>
        </form>
    </div>
    
    <div class="step" id="authStep" style="display: none;">
        <h3>Step 2: Authorize Your App</h3>
        <p>Click the link below to authorize your LinkedIn app:</p>
        <p><a id="authLink" href="#" target="_blank" style="color: #0077b5; font-weight: bold;">Authorize LinkedIn App</a></p>
        <p><em>After authorization, you'll be redirected back here with your access token.</em></p>
    </div>
    
    <div class="step" id="resultStep" style="display: none;">
        <h3>Step 3: Your Access Token</h3>
        <div id="tokenResult"></div>
    </div>
    
    <div class="step">
        <h3>Prerequisites</h3>
        <p>Before using this tool, make sure you have:</p>
        <ul>
            <li>Created a LinkedIn app at <a href="https://developer.linkedin.com/" target="_blank">developer.linkedin.com</a></li>
            <li>Added <code>http://localhost:8080/callback</code> as a redirect URI in your app settings</li>
            <li>Requested access to "Share on LinkedIn" and "Sign In with LinkedIn" products</li>
        </ul>
    </div>

    <script>
        function generateAuthUrl() {
            const clientId = document.getElementById('clientId').value;
            const clientSecret = document.getElementById('clientSecret').value;
            
            if (!clientId || !clientSecret) {
                alert('Please enter both Client ID and Client Secret');
                return;
            }
            
            // Store credentials for later use
            sessionStorage.setItem('clientId', clientId);
            sessionStorage.setItem('clientSecret', clientSecret);
            
            const params = new URLSearchParams({
                response_type: 'code',
                client_id: clientId,
                redirect_uri: 'http://localhost:8080/callback',
                scope: 'profile w_member_social openid email',
                state: 'token_generator'
            });
            
            const authUrl = 'https://www.linkedin.com/oauth/v2/authorization?' + params.toString();
            
            document.getElementById('authLink').href = authUrl;
            document.getElementById('authStep').style.display = 'block';
        }
        
        // Check if we have token data in URL (from callback)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('access_token')) {
            document.getElementById('resultStep').style.display = 'block';
            document.getElementById('tokenResult').innerHTML = `
                <div class="success">
                    <h4>✅ Success! Your LinkedIn credentials:</h4>
                    <div class="code">
                        <strong>Access Token:</strong> ${urlParams.get('access_token')}<br>
                        <strong>Expires In:</strong> ${urlParams.get('expires_in')} seconds<br>
                        ${urlParams.get('refresh_token') ? '<strong>Refresh Token:</strong> ' + urlParams.get('refresh_token') + '<br>' : ''}
                    </div>
                    <p><strong>Next steps:</strong></p>
                    <ol>
                        <li>Copy the access token above</li>
                        <li>Run: <code>python manage.py linkedin_setup</code></li>
                        <li>Enter your credentials when prompted</li>
                    </ol>
                </div>
            `;
        } else if (urlParams.get('error')) {
            document.getElementById('resultStep').style.display = 'block';
            document.getElementById('tokenResult').innerHTML = `
                <div class="error">
                    <h4>❌ Error: ${urlParams.get('error')}</h4>
                    <p>${urlParams.get('error_description') || 'Unknown error occurred'}</p>
                </div>
            `;
        }
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_callback(self, query_string):
        params = parse_qs(query_string)
        
        if 'error' in params:
            # Handle error
            error = params['error'][0]
            error_description = params.get('error_description', [''])[0]
            self.redirect_with_params({'error': error, 'error_description': error_description})
            return
        
        if 'code' not in params:
            self.redirect_with_params({'error': 'no_code', 'error_description': 'No authorization code received'})
            return
        
        auth_code = params['code'][0]
        
        # Exchange code for token
        try:
            # We need the client credentials - in a real app, these would be stored securely
            # For this demo, we'll show an error message
            self.redirect_with_params({
                'error': 'manual_exchange', 
                'error_description': 'Please use the management command to exchange the code for a token',
                'auth_code': auth_code
            })
            
        except Exception as e:
            self.redirect_with_params({'error': 'exchange_failed', 'error_description': str(e)})
    
    def redirect_with_params(self, params):
        query_string = urllib.parse.urlencode(params)
        self.send_response(302)
        self.send_header('Location', f'/?{query_string}')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def main():
    PORT = 8080
    
    print("🔗 LinkedIn Token Generator")
    print("=" * 30)
    print(f"Starting server on http://localhost:{PORT}")
    print("\nMake sure you have added this redirect URI to your LinkedIn app:")
    print(f"  http://localhost:{PORT}/callback")
    print("\nPress Ctrl+C to stop the server")
    print()
    
    try:
        with socketserver.TCPServer(("", PORT), LinkedInTokenHandler) as httpd:
            # Open browser automatically
            webbrowser.open(f'http://localhost:{PORT}')
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use. Please stop any other servers and try again.")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == '__main__':
    main()