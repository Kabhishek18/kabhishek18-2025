# Resume Parser Usage Examples

## Overview

This document provides comprehensive examples of how to use the Resume Parser API in various programming languages and scenarios.

## Table of Contents

1. [Python Examples](#python-examples)
2. [JavaScript Examples](#javascript-examples)
3. [cURL Examples](#curl-examples)
4. [Integration Examples](#integration-examples)
5. [Error Handling Examples](#error-handling-examples)
6. [Advanced Usage](#advanced-usage)

## Python Examples

### Basic Usage

```python
import requests
import json

def parse_resume(file_path, backend='auto'):
    """
    Parse a resume PDF and return structured data
    """
    url = "https://your-domain.com/api/roadmap/parse-resume/"
    
    with open(file_path, 'rb') as file:
        files = {'resume_file': file}
        data = {
            'processing_backend': backend,
            'include_raw_text': False
        }
        
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

# Usage
try:
    resume_data = parse_resume('john_doe_resume.pdf')
    print(f"Candidate: {resume_data['name']}")
    print(f"Email: {resume_data['email']}")
    print(f"Skills: {', '.join(resume_data['skills'])}")
except Exception as e:
    print(f"Error: {e}")
```

### Advanced Python Client

```python
import requests
import time
from typing import Optional, Dict, Any
from pathlib import Path

class ResumeParserClient:
    """
    Advanced client for Resume Parser API
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def parse_resume(
        self, 
        file_path: str, 
        backend: str = 'auto',
        include_raw_text: bool = False,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Parse resume with retry logic and comprehensive error handling
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Resume file not found: {file_path}")
        
        if file_path.suffix.lower() != '.pdf':
            raise ValueError("Only PDF files are supported")
        
        url = f"{self.base_url}/api/roadmap/parse-resume/"
        
        for attempt in range(retry_count):
            try:
                with open(file_path, 'rb') as file:
                    files = {'resume_file': file}
                    data = {
                        'processing_backend': backend,
                        'include_raw_text': include_raw_text
                    }
                    
                    response = self.session.post(
                        url, 
                        files=files, 
                        data=data, 
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code in [500, 502, 503, 504] and attempt < retry_count - 1:
                        # Retry on server errors
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        error_data = response.json() if response.content else {}
                        raise APIError(
                            response.status_code, 
                            error_data.get('error', {}).get('message', 'Unknown error'),
                            error_data
                        )
            
            except requests.exceptions.Timeout:
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TimeoutError("Request timed out after multiple attempts")
            
            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise ConnectionError(f"Network error: {e}")
        
        raise Exception("Max retry attempts exceeded")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health status
        """
        url = f"{self.base_url}/api/roadmap/health/"
        
        try:
            response = self.session.get(url, timeout=10)
            return response.json()
        except Exception as e:
            return {
                'status': 'unavailable',
                'error': str(e)
            }
    
    def batch_process(self, file_paths: list, backend: str = 'auto') -> Dict[str, Any]:
        """
        Process multiple resumes
        """
        results = {}
        
        for file_path in file_paths:
            try:
                result = self.parse_resume(file_path, backend)
                results[file_path] = {
                    'success': True,
                    'data': result
                }
            except Exception as e:
                results[file_path] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, status_code: int, message: str, details: Dict = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"API Error {status_code}: {message}")

# Usage example
client = ResumeParserClient("https://your-domain.com")

# Single resume
try:
    result = client.parse_resume("resume.pdf", backend="gemini")
    print(f"Parsed resume for: {result['name']}")
except APIError as e:
    print(f"API Error: {e.message}")
except Exception as e:
    print(f"Error: {e}")

# Health check
health = client.health_check()
print(f"API Status: {health['status']}")

# Batch processing
files = ["resume1.pdf", "resume2.pdf", "resume3.pdf"]
batch_results = client.batch_process(files)
for file_path, result in batch_results.items():
    if result['success']:
        print(f"✓ {file_path}: {result['data']['name']}")
    else:
        print(f"✗ {file_path}: {result['error']}")
```

## JavaScript Examples

### Basic Frontend Usage

```javascript
// Basic resume upload with vanilla JavaScript
async function parseResume(fileInput, backend = 'auto') {
    const formData = new FormData();
    formData.append('resume_file', fileInput.files[0]);
    formData.append('processing_backend', backend);
    formData.append('include_raw_text', false);
    
    try {
        const response = await fetch('/api/roadmap/parse-resume/', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error.message);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Resume parsing failed:', error);
        throw error;
    }
}

// Usage with file input
document.getElementById('resume-upload').addEventListener('change', async (event) => {
    const fileInput = event.target;
    
    if (fileInput.files.length === 0) return;
    
    try {
        showLoading(true);
        const result = await parseResume(fileInput);
        displayResumeData(result);
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
});

function displayResumeData(data) {
    document.getElementById('candidate-name').textContent = data.name || 'N/A';
    document.getElementById('candidate-email').textContent = data.email || 'N/A';
    
    const skillsList = document.getElementById('skills-list');
    skillsList.innerHTML = '';
    data.skills.forEach(skill => {
        const li = document.createElement('li');
        li.textContent = skill;
        skillsList.appendChild(li);
    });
}
```

### React Component Example

```jsx
import React, { useState, useCallback } from 'react';
import axios from 'axios';

const ResumeUploader = () => {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [backend, setBackend] = useState('auto');

    const handleFileChange = useCallback((event) => {
        const selectedFile = event.target.files[0];
        
        if (selectedFile && selectedFile.type !== 'application/pdf') {
            setError('Please select a PDF file');
            return;
        }
        
        setFile(selectedFile);
        setError(null);
    }, []);

    const handleUpload = useCallback(async () => {
        if (!file) {
            setError('Please select a file');
            return;
        }

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('resume_file', file);
        formData.append('processing_backend', backend);

        try {
            const response = await axios.post('/api/roadmap/parse-resume/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                timeout: 60000, // 60 seconds
            });

            setResult(response.data);
        } catch (err) {
            if (err.response?.data?.error) {
                setError(err.response.data.error.message);
            } else if (err.code === 'ECONNABORTED') {
                setError('Request timed out. Please try again.');
            } else {
                setError('An unexpected error occurred');
            }
        } finally {
            setLoading(false);
        }
    }, [file, backend]);

    return (
        <div className="resume-uploader">
            <div className="upload-section">
                <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    disabled={loading}
                />
                
                <select 
                    value={backend} 
                    onChange={(e) => setBackend(e.target.value)}
                    disabled={loading}
                >
                    <option value="auto">Auto (Recommended)</option>
                    <option value="gemini">Gemini AI</option>
                    <option value="spacy">spaCy</option>
                    <option value="rule_based">Rule-based</option>
                </select>
                
                <button 
                    onClick={handleUpload} 
                    disabled={!file || loading}
                >
                    {loading ? 'Processing...' : 'Parse Resume'}
                </button>
            </div>

            {error && (
                <div className="error-message">
                    Error: {error}
                </div>
            )}

            {result && (
                <div className="result-section">
                    <h3>Parsed Resume Data</h3>
                    <div className="candidate-info">
                        <p><strong>Name:</strong> {result.name || 'N/A'}</p>
                        <p><strong>Email:</strong> {result.email || 'N/A'}</p>
                        <p><strong>Phone:</strong> {result.phone || 'N/A'}</p>
                        <p><strong>Location:</strong> {result.location || 'N/A'}</p>
                    </div>
                    
                    <div className="skills-section">
                        <h4>Skills</h4>
                        <div className="skills-list">
                            {result.skills?.map((skill, index) => (
                                <span key={index} className="skill-tag">
                                    {skill}
                                </span>
                            ))}
                        </div>
                    </div>
                    
                    <div className="experience-section">
                        <h4>Experience</h4>
                        {result.experience?.map((exp, index) => (
                            <div key={index} className="experience-item">
                                <h5>{exp.job_title} at {exp.company}</h5>
                                <p>{exp.start_date} - {exp.end_date}</p>
                                <p>{exp.description}</p>
                            </div>
                        ))}
                    </div>
                    
                    <div className="metadata">
                        <p><strong>Backend Used:</strong> {result.processing_backend_used}</p>
                        <p><strong>Confidence:</strong> {(result.confidence_score * 100).toFixed(1)}%</p>
                        <p><strong>Processing Time:</strong> {result.processing_time_seconds}s</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ResumeUploader;
```

### Node.js Backend Integration

```javascript
const express = require('express');
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

const app = express();
const upload = multer({ dest: 'uploads/' });

// Proxy endpoint for resume parsing
app.post('/parse-resume', upload.single('resume'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({
                error: { message: 'No file uploaded' }
            });
        }

        // Create form data for the API request
        const formData = new FormData();
        formData.append('resume_file', fs.createReadStream(req.file.path));
        formData.append('processing_backend', req.body.backend || 'auto');

        // Forward request to Resume Parser API
        const response = await axios.post(
            'https://your-domain.com/api/roadmap/parse-resume/',
            formData,
            {
                headers: {
                    ...formData.getHeaders(),
                },
                timeout: 60000,
            }
        );

        // Clean up uploaded file
        fs.unlinkSync(req.file.path);

        // Return parsed data
        res.json(response.data);

    } catch (error) {
        // Clean up uploaded file on error
        if (req.file) {
            fs.unlinkSync(req.file.path);
        }

        if (error.response) {
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({
                error: { message: 'Internal server error' }
            });
        }
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

## cURL Examples

### Basic Resume Parsing

```bash
# Parse resume with auto backend selection
curl -X POST \
  https://your-domain.com/api/roadmap/parse-resume/ \
  -H 'Content-Type: multipart/form-data' \
  -F 'resume_file=@/path/to/resume.pdf' \
  -F 'processing_backend=auto'

# Parse with specific backend
curl -X POST \
  https://your-domain.com/api/roadmap/parse-resume/ \
  -H 'Content-Type: multipart/form-data' \
  -F 'resume_file=@/path/to/resume.pdf' \
  -F 'processing_backend=gemini' \
  -F 'include_raw_text=true'

# Health check
curl -X GET https://your-domain.com/api/roadmap/health/
```

### Advanced cURL with Error Handling

```bash
#!/bin/bash

# Resume parsing script with error handling
parse_resume() {
    local file_path="$1"
    local backend="${2:-auto}"
    local output_file="${3:-result.json}"
    
    if [[ ! -f "$file_path" ]]; then
        echo "Error: File not found: $file_path"
        return 1
    fi
    
    echo "Parsing resume: $file_path with backend: $backend"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        https://your-domain.com/api/roadmap/parse-resume/ \
        -H 'Content-Type: multipart/form-data' \
        -F "resume_file=@$file_path" \
        -F "processing_backend=$backend")
    
    # Extract HTTP status code
    http_code=$(echo "$response" | tail -n1)
    json_response=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" -eq 200 ]]; then
        echo "✓ Success! Saving result to $output_file"
        echo "$json_response" | jq '.' > "$output_file"
        
        # Extract key information
        name=$(echo "$json_response" | jq -r '.name // "N/A"')
        email=$(echo "$json_response" | jq -r '.email // "N/A"')
        skills_count=$(echo "$json_response" | jq '.skills | length')
        
        echo "Candidate: $name"
        echo "Email: $email"
        echo "Skills found: $skills_count"
        
        return 0
    else
        echo "✗ Error (HTTP $http_code):"
        echo "$json_response" | jq -r '.error.message // "Unknown error"'
        return 1
    fi
}

# Usage examples
parse_resume "john_doe_resume.pdf" "auto" "john_doe_result.json"
parse_resume "jane_smith_resume.pdf" "gemini" "jane_smith_result.json"

# Batch processing
for resume in *.pdf; do
    if [[ -f "$resume" ]]; then
        output="${resume%.pdf}_result.json"
        parse_resume "$resume" "auto" "$output"
        sleep 1  # Rate limiting
    fi
done
```

## Integration Examples

### Django Integration

```python
# views.py - Integrate with existing Django application
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests

@csrf_exempt
@require_http_methods(["POST"])
def upload_candidate_resume(request):
    """
    Handle resume upload for candidate application
    """
    if 'resume_file' not in request.FILES:
        return JsonResponse({'error': 'No resume file provided'}, status=400)
    
    resume_file = request.FILES['resume_file']
    
    # Validate file
    if not resume_file.name.endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF files allowed'}, status=400)
    
    try:
        # Call Resume Parser API
        files = {'resume_file': resume_file}
        data = {'processing_backend': 'auto'}
        
        response = requests.post(
            'http://localhost:8000/api/roadmap/parse-resume/',
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            resume_data = response.json()
            
            # Create candidate record with parsed data
            candidate = Candidate.objects.create(
                name=resume_data.get('name'),
                email=resume_data.get('email'),
                phone=resume_data.get('phone'),
                location=resume_data.get('location'),
                skills=resume_data.get('skills', []),
                raw_resume_data=resume_data
            )
            
            return JsonResponse({
                'success': True,
                'candidate_id': candidate.id,
                'parsed_data': resume_data
            })
        else:
            error_data = response.json()
            return JsonResponse({
                'error': error_data.get('error', {}).get('message', 'Parsing failed')
            }, status=response.status_code)
            
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Resume parsing timed out'}, status=408)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField

class Candidate(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    skills = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    raw_resume_data = JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name or f"Candidate {self.id}"
```

### Flask Integration

```python
from flask import Flask, request, jsonify
import requests
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/api/candidates/upload-resume', methods=['POST'])
def upload_resume():
    """
    Flask endpoint for resume upload and parsing
    """
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        # Forward to Resume Parser API
        files = {'resume_file': (file.filename, file.stream, file.content_type)}
        data = {
            'processing_backend': request.form.get('backend', 'auto'),
            'include_raw_text': request.form.get('include_raw_text', 'false')
        }
        
        response = requests.post(
            'https://your-domain.com/api/roadmap/parse-resume/',
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            parsed_data = response.json()
            
            # Store in database (example with SQLAlchemy)
            candidate = Candidate(
                name=parsed_data.get('name'),
                email=parsed_data.get('email'),
                phone=parsed_data.get('phone'),
                skills=','.join(parsed_data.get('skills', [])),
                resume_data=parsed_data
            )
            db.session.add(candidate)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'candidate_id': candidate.id,
                'parsed_data': parsed_data
            })
        else:
            error_data = response.json()
            return jsonify(error_data), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'API request failed: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## Error Handling Examples

### Comprehensive Error Handling

```python
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ResumeParserError(Exception):
    """Base exception for resume parser errors"""
    pass

class ValidationError(ResumeParserError):
    """File validation error"""
    pass

class ProcessingError(ResumeParserError):
    """Resume processing error"""
    pass

class APIError(ResumeParserError):
    """API communication error"""
    pass

def parse_resume_with_error_handling(
    file_path: str, 
    backend: str = 'auto'
) -> Optional[Dict[str, Any]]:
    """
    Parse resume with comprehensive error handling
    """
    try:
        # Validate file before upload
        if not os.path.exists(file_path):
            raise ValidationError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError(f"File too large: {file_size / 1024 / 1024:.1f}MB")
        
        if not file_path.lower().endswith('.pdf'):
            raise ValidationError("Only PDF files are supported")
        
        # Make API request
        with open(file_path, 'rb') as file:
            files = {'resume_file': file}
            data = {'processing_backend': backend}
            
            response = requests.post(
                'https://your-domain.com/api/roadmap/parse-resume/',
                files=files,
                data=data,
                timeout=60
            )
        
        # Handle different response codes
        if response.status_code == 200:
            data = response.json()
            
            # Validate response data
            if not data.get('processing_backend_used'):
                logger.warning("Response missing processing backend info")
            
            confidence = data.get('confidence_score', 0)
            if confidence < 0.5:
                logger.warning(f"Low confidence score: {confidence}")
            
            return data
            
        elif response.status_code == 400:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', 'UNKNOWN')
            
            if error_code == 'INVALID_FILE_FORMAT':
                raise ValidationError("Invalid PDF file format")
            elif error_code == 'VALIDATION_ERROR':
                raise ValidationError("File validation failed")
            else:
                raise ValidationError(f"Bad request: {error_data}")
                
        elif response.status_code == 413:
            raise ValidationError("File size too large")
            
        elif response.status_code == 422:
            error_data = response.json()
            error_code = error_data.get('error', {}).get('code', 'UNKNOWN')
            
            if error_code == 'PDF_EXTRACTION_ERROR':
                raise ProcessingError("Failed to extract text from PDF")
            elif error_code == 'AI_PROCESSING_ERROR':
                raise ProcessingError("AI processing failed")
            else:
                raise ProcessingError(f"Processing error: {error_data}")
                
        elif response.status_code >= 500:
            raise APIError(f"Server error: {response.status_code}")
            
        else:
            raise APIError(f"Unexpected response: {response.status_code}")
    
    except requests.exceptions.Timeout:
        raise APIError("Request timed out")
    except requests.exceptions.ConnectionError:
        raise APIError("Connection failed")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Request failed: {e}")
    except (ValidationError, ProcessingError, APIError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        logger.exception("Unexpected error during resume parsing")
        raise ResumeParserError(f"Unexpected error: {e}")

# Usage with error handling
def process_candidate_resume(file_path: str) -> Dict[str, Any]:
    """
    Process candidate resume with user-friendly error messages
    """
    try:
        result = parse_resume_with_error_handling(file_path)
        return {
            'success': True,
            'data': result,
            'message': 'Resume parsed successfully'
        }
        
    except ValidationError as e:
        return {
            'success': False,
            'error_type': 'validation',
            'message': f"File validation failed: {e}",
            'user_message': 'Please check your file and try again'
        }
        
    except ProcessingError as e:
        return {
            'success': False,
            'error_type': 'processing',
            'message': f"Processing failed: {e}",
            'user_message': 'Unable to process this resume. Please try a different file.'
        }
        
    except APIError as e:
        return {
            'success': False,
            'error_type': 'api',
            'message': f"API error: {e}",
            'user_message': 'Service temporarily unavailable. Please try again later.'
        }
        
    except ResumeParserError as e:
        return {
            'success': False,
            'error_type': 'unknown',
            'message': f"Unknown error: {e}",
            'user_message': 'An unexpected error occurred. Please contact support.'
        }
```

## Advanced Usage

### Batch Processing with Progress Tracking

```python
import asyncio
import aiohttp
from typing import List, Dict, Callable
import time

class BatchResumeProcessor:
    """
    Process multiple resumes with progress tracking and rate limiting
    """
    
    def __init__(self, base_url: str, max_concurrent: int = 3):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_resume(
        self, 
        session: aiohttp.ClientSession,
        file_path: str,
        backend: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Process single resume asynchronously
        """
        async with self.semaphore:
            try:
                with open(file_path, 'rb') as file:
                    data = aiohttp.FormData()
                    data.add_field('resume_file', file, filename=os.path.basename(file_path))
                    data.add_field('processing_backend', backend)
                    
                    async with session.post(
                        f"{self.base_url}/api/roadmap/parse-resume/",
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        
                        result = await response.json()
                        
                        return {
                            'file_path': file_path,
                            'success': response.status == 200,
                            'data': result if response.status == 200 else None,
                            'error': result.get('error') if response.status != 200 else None,
                            'status_code': response.status
                        }
                        
            except Exception as e:
                return {
                    'file_path': file_path,
                    'success': False,
                    'data': None,
                    'error': {'message': str(e)},
                    'status_code': 0
                }
    
    async def process_batch(
        self, 
        file_paths: List[str],
        backend: str = 'auto',
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple resumes with progress tracking
        """
        results = []
        completed = 0
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.process_resume(session, file_path, backend)
                for file_path in file_paths
            ]
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(file_paths))
        
        return results

# Usage example
async def main():
    processor = BatchResumeProcessor("https://your-domain.com", max_concurrent=3)
    
    file_paths = [
        "resume1.pdf",
        "resume2.pdf", 
        "resume3.pdf",
        "resume4.pdf"
    ]
    
    def progress_callback(completed: int, total: int):
        percentage = (completed / total) * 100
        print(f"Progress: {completed}/{total} ({percentage:.1f}%)")
    
    results = await processor.process_batch(
        file_paths, 
        backend='auto',
        progress_callback=progress_callback
    )
    
    # Process results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\nCompleted: {len(successful)} successful, {len(failed)} failed")
    
    for result in successful:
        data = result['data']
        print(f"✓ {result['file_path']}: {data['name']} ({data['email']})")
    
    for result in failed:
        error_msg = result['error'].get('message', 'Unknown error')
        print(f"✗ {result['file_path']}: {error_msg}")

# Run batch processing
if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Skill Extraction

```python
def enhance_skills_extraction(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance skills extraction with custom logic
    """
    skills = resume_data.get('skills', [])
    
    # Define skill categories
    skill_categories = {
        'programming_languages': [
            'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'go', 'rust',
            'php', 'swift', 'kotlin', 'typescript', 'scala', 'r', 'matlab'
        ],
        'frameworks': [
            'django', 'flask', 'react', 'angular', 'vue', 'node.js', 'express',
            'spring', 'laravel', 'rails', 'asp.net', 'flutter', 'xamarin'
        ],
        'databases': [
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'cassandra', 'oracle', 'sqlite', 'dynamodb', 'neo4j'
        ],
        'cloud_platforms': [
            'aws', 'azure', 'google cloud', 'heroku', 'digitalocean',
            'linode', 'vultr', 'cloudflare', 'vercel', 'netlify'
        ],
        'tools': [
            'docker', 'kubernetes', 'jenkins', 'git', 'gitlab', 'github',
            'jira', 'confluence', 'slack', 'trello', 'asana'
        ]
    }
    
    # Categorize skills
    categorized_skills = {}
    uncategorized_skills = []
    
    for skill in skills:
        skill_lower = skill.lower()
        categorized = False
        
        for category, category_skills in skill_categories.items():
            if any(cat_skill in skill_lower for cat_skill in category_skills):
                if category not in categorized_skills:
                    categorized_skills[category] = []
                categorized_skills[category].append(skill)
                categorized = True
                break
        
        if not categorized:
            uncategorized_skills.append(skill)
    
    # Add uncategorized skills
    if uncategorized_skills:
        categorized_skills['other'] = uncategorized_skills
    
    # Update resume data
    resume_data['enhanced_skills'] = {
        'categorized': categorized_skills,
        'total_count': len(skills),
        'categories_count': len(categorized_skills)
    }
    
    return resume_data

# Usage
result = parse_resume('resume.pdf')
enhanced_result = enhance_skills_extraction(result)
print(enhanced_result['enhanced_skills'])
```

This comprehensive documentation provides examples for various use cases and programming languages, making it easy for developers to integrate the Resume Parser API into their applications.