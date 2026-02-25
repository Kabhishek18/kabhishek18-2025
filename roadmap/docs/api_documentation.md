# Resume Parser API Documentation

## Overview

The Resume Parser API allows you to upload PDF resumes and extract structured information using AI-powered natural language processing. The system supports multiple AI backends (Gemini AI, spaCy, rule-based) with automatic fallback for reliability.

## Base URL

```
https://your-domain.com/api/roadmap/
```

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Rate Limiting

- Maximum file size: 10MB (configurable)
- Recommended: No more than 10 requests per minute per IP

## API Endpoints

### 1. Parse Resume

**Endpoint:** `POST /api/roadmap/parse-resume/`

**Description:** Upload a PDF resume and extract structured information including personal details, skills, experience, and education.

#### Request

**Content-Type:** `multipart/form-data`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `resume_file` | File | Yes | - | PDF file containing the resume to parse |
| `processing_backend` | String | No | `auto` | AI backend to use (`auto`, `gemini`, `spacy`, `rule_based`) |
| `include_raw_text` | Boolean | No | `false` | Include extracted raw text in response (for debugging) |

**Example Request:**

```bash
curl -X POST \
  https://your-domain.com/api/roadmap/parse-resume/ \
  -H 'Content-Type: multipart/form-data' \
  -F 'resume_file=@/path/to/resume.pdf' \
  -F 'processing_backend=auto' \
  -F 'include_raw_text=false'
```

#### Response

**Success Response (200 OK):**

```json
{
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone": "+1-555-123-4567",
  "location": "San Francisco, CA",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "website_url": "https://johndoe.dev",
  "summary": "Experienced software engineer with 5+ years in full-stack development...",
  "skills": [
    "Python",
    "JavaScript",
    "React",
    "Django",
    "PostgreSQL",
    "AWS"
  ],
  "categorized_skills": [
    {
      "category": "Programming Languages",
      "skills": ["Python", "JavaScript", "TypeScript"]
    },
    {
      "category": "Frameworks",
      "skills": ["React", "Django", "Node.js"]
    },
    {
      "category": "Databases",
      "skills": ["PostgreSQL", "MongoDB", "Redis"]
    }
  ],
  "experience": [
    {
      "job_title": "Senior Software Engineer",
      "company": "Tech Corp",
      "start_date": "2021-01",
      "end_date": "2024-01",
      "description": "Led development of microservices architecture...",
      "location": "San Francisco, CA",
      "is_current": false
    }
  ],
  "education": [
    {
      "degree": "Bachelor of Science",
      "institution": "University of California",
      "field_of_study": "Computer Science",
      "start_date": "2015",
      "end_date": "2019",
      "gpa": "3.8",
      "location": "Berkeley, CA"
    }
  ],
  "languages": ["English", "Spanish"],
  "certifications": [
    "AWS Certified Solutions Architect",
    "Certified Kubernetes Administrator"
  ],
  "processing_backend_used": "gemini",
  "confidence_score": 0.92,
  "processing_time_seconds": 2.34,
  "warnings": []
}
```

**Error Responses:**

**400 Bad Request - Invalid File Format:**
```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Only PDF files are supported",
    "details": {
      "file_name": "resume.docx",
      "error": "File type not supported"
    }
  }
}
```

**413 Payload Too Large:**
```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File size exceeds maximum limit",
    "details": {
      "file_size_mb": 15.2,
      "max_size_mb": 10
    }
  }
}
```

**422 Unprocessable Entity - Processing Error:**
```json
{
  "error": {
    "code": "AI_PROCESSING_ERROR",
    "message": "Failed to process resume text",
    "details": {
      "backend_requested": "gemini",
      "error": "API rate limit exceeded"
    }
  }
}
```

### 2. Health Check

**Endpoint:** `GET /api/roadmap/health/`

**Description:** Check the health and availability of AI backends and system resources.

#### Request

**Method:** `GET`

**Example Request:**

```bash
curl -X GET https://your-domain.com/api/roadmap/health/
```

#### Response

**Success Response (200 OK):**

```json
{
  "status": "healthy",
  "backends": {
    "gemini": {
      "status": "available",
      "response_time_ms": 245,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "spacy": {
      "status": "available",
      "model_loaded": "en_core_web_sm",
      "last_check": "2024-01-15T10:30:00Z"
    },
    "rule_based": {
      "status": "available",
      "last_check": "2024-01-15T10:30:00Z"
    }
  },
  "configuration": {
    "available_backends": ["gemini", "spacy", "rule_based"],
    "total_backends": 3,
    "temp_directory": "/tmp/resume_parser",
    "temp_files_count": 0,
    "temp_files_size_mb": 0.0,
    "oldest_temp_file_age_minutes": 0
  }
}
```

**Degraded Service Response (503 Service Unavailable):**

```json
{
  "status": "degraded",
  "backends": {
    "gemini": {
      "status": "unavailable",
      "error": "API key not configured",
      "last_check": "2024-01-15T10:30:00Z"
    },
    "spacy": {
      "status": "available",
      "model_loaded": "en_core_web_sm",
      "last_check": "2024-01-15T10:30:00Z"
    },
    "rule_based": {
      "status": "available",
      "last_check": "2024-01-15T10:30:00Z"
    }
  },
  "configuration": {
    "available_backends": ["spacy", "rule_based"],
    "total_backends": 3,
    "temp_directory": "/tmp/resume_parser",
    "temp_files_count": 2,
    "temp_files_size_mb": 1.5,
    "oldest_temp_file_age_minutes": 15
  }
}
```

## Data Models

### ResumeData Schema

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Full name of the candidate |
| `email` | String | Primary email address |
| `phone` | String | Phone number |
| `location` | String | Current location/address |
| `linkedin_url` | String | LinkedIn profile URL |
| `website_url` | String | Personal website or portfolio URL |
| `summary` | String | Professional summary or objective |
| `skills` | Array[String] | Flat list of all identified skills |
| `categorized_skills` | Array[SkillCategory] | Skills organized by category |
| `experience` | Array[Experience] | Work experience entries |
| `education` | Array[Education] | Education entries |
| `languages` | Array[String] | Known languages |
| `certifications` | Array[String] | Professional certifications |
| `processing_backend_used` | String | Backend that processed the resume |
| `confidence_score` | Float | Confidence score (0.0 to 1.0) |
| `processing_time_seconds` | Float | Processing time in seconds |
| `warnings` | Array[String] | Non-fatal warnings |

### Experience Schema

| Field | Type | Description |
|-------|------|-------------|
| `job_title` | String | Job title or position |
| `company` | String | Company name |
| `start_date` | String | Start date (various formats) |
| `end_date` | String | End date or "Present" |
| `description` | String | Job description or responsibilities |
| `location` | String | Job location |
| `is_current` | Boolean | Whether this is the current job |

### Education Schema

| Field | Type | Description |
|-------|------|-------------|
| `degree` | String | Degree type (Bachelor's, Master's, etc.) |
| `institution` | String | School or university name |
| `field_of_study` | String | Major or field of study |
| `start_date` | String | Start date |
| `end_date` | String | Graduation date |
| `gpa` | String | Grade point average |
| `location` | String | Institution location |

### SkillCategory Schema

| Field | Type | Description |
|-------|------|-------------|
| `category` | String | Skill category name |
| `skills` | Array[String] | Skills in this category |

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `INVALID_FILE_FORMAT` | 400 | File is not a valid PDF |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `PDF_EXTRACTION_ERROR` | 422 | Failed to extract text from PDF |
| `AI_PROCESSING_ERROR` | 422 | AI backend processing failed |
| `HEALTH_CHECK_ERROR` | 500 | Health check system error |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | - | Google Gemini AI API key |
| `RESUME_PARSER_MAX_FILE_SIZE` | 10 | Maximum file size in MB |
| `RESUME_PARSER_DEFAULT_BACKEND` | auto | Default processing backend |
| `SPACY_MODEL` | en_core_web_sm | spaCy model to use |
| `RESUME_PARSER_TEMP_DIR` | /tmp | Temporary file directory |
| `RESUME_PARSER_CLEANUP_TIMEOUT` | 300 | File cleanup timeout in seconds |

### Django Settings

```python
RESUME_PARSER_SETTINGS = {
    'MAX_FILE_SIZE_MB': 10,
    'ALLOWED_FILE_TYPES': ['application/pdf'],
    'DEFAULT_BACKEND': 'auto',
    'TEMP_FILE_CLEANUP_TIMEOUT': 300,  # seconds
    'AI_BACKENDS': {
        'gemini': {
            'enabled': True,
            'api_key_env': 'GEMINI_API_KEY',
            'timeout': 30,
        },
        'spacy': {
            'enabled': True,
            'model': 'en_core_web_sm',
        },
        'rule_based': {
            'enabled': True,
        }
    }
}
```

## Usage Examples

### Python Example

```python
import requests

# Upload and parse resume
url = "https://your-domain.com/api/roadmap/parse-resume/"
files = {'resume_file': open('resume.pdf', 'rb')}
data = {
    'processing_backend': 'auto',
    'include_raw_text': False
}

response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    resume_data = response.json()
    print(f"Candidate: {resume_data['name']}")
    print(f"Email: {resume_data['email']}")
    print(f"Skills: {', '.join(resume_data['skills'])}")
else:
    error = response.json()
    print(f"Error: {error['error']['message']}")
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('resume_file', fileInput.files[0]);
formData.append('processing_backend', 'auto');

fetch('https://your-domain.com/api/roadmap/parse-resume/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.error) {
        console.error('Error:', data.error.message);
    } else {
        console.log('Candidate:', data.name);
        console.log('Skills:', data.skills);
    }
})
.catch(error => console.error('Request failed:', error));
```

### cURL Example

```bash
# Parse resume with Gemini AI
curl -X POST \
  https://your-domain.com/api/roadmap/parse-resume/ \
  -H 'Content-Type: multipart/form-data' \
  -F 'resume_file=@resume.pdf' \
  -F 'processing_backend=gemini'

# Check system health
curl -X GET https://your-domain.com/api/roadmap/health/
```

## Best Practices

### File Upload
- Always validate file type on client-side before upload
- Compress large PDFs when possible
- Handle upload progress for better user experience

### Error Handling
- Always check the response status code
- Parse error responses to show meaningful messages to users
- Implement retry logic for temporary failures

### Performance
- Use appropriate backend based on your needs:
  - `gemini`: Best accuracy, requires API key and internet
  - `spacy`: Good accuracy, works offline, faster
  - `rule_based`: Basic extraction, very fast, always available
  - `auto`: Automatic fallback for reliability

### Security
- Validate file types on both client and server
- Never store uploaded files permanently
- Sanitize extracted data before displaying to users

## Troubleshooting

### Common Issues

**"Invalid file format" error:**
- Ensure the file is a valid PDF
- Check if the PDF is password-protected or corrupted
- Try re-saving the PDF from another application

**"Processing timeout" error:**
- Large files may take longer to process
- Try using a smaller file or different backend
- Check system resources and AI backend availability

**"AI backend unavailable" error:**
- Check if API keys are configured correctly
- Verify internet connectivity for cloud-based backends
- Use health check endpoint to diagnose backend issues

### Support

For technical support or feature requests, please contact the development team or create an issue in the project repository.

## Changelog

### Version 1.0.0
- Initial release with Gemini AI, spaCy, and rule-based backends
- Support for PDF resume parsing
- Health check endpoint
- Comprehensive error handling and cleanup