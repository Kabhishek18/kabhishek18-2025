# Resume Parser Admin Interface Guide

## Overview

The Resume Parser admin interface provides a user-friendly way to configure and test the AI backends used for resume processing. This guide explains how to use the various features available in the Django admin.

## Accessing the Admin Interface

1. Navigate to `/admin/` in your Django application
2. Log in with your admin credentials
3. Go to **Roadmap** → **Resume Parser Configurations**

## Configuration Sections

### API Configuration
- **Gemini API Key**: Your Google Gemini API key for AI processing
  - Use the "Show/Hide" button to toggle visibility
  - Leave blank to disable Gemini backend
  - Get your key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### File Processing Settings
- **Max File Size (MB)**: Maximum PDF file size allowed (1-100 MB)
- **Processing Timeout**: Maximum time to wait for processing (30-3600 seconds)
- **Cleanup Timeout**: Time to keep temporary files (60-3600 seconds)

### AI Backend Configuration
- **Default Backend**: Choose which AI backend to use by default
  - **Auto**: Tries backends in order (Gemini → spaCy → Rule-based)
  - **Gemini AI**: Use Google Gemini exclusively
  - **spaCy NLP**: Use local spaCy models
  - **Rule-based**: Use pattern matching only
- **spaCy Model**: Name of the spaCy model to use (e.g., `en_core_web_sm`)
- **Enable Fallback Processing**: Allow trying alternative backends if primary fails
- **Enable Confidence Scoring**: Include quality scores in API responses

## Backend Status Display

The admin interface shows real-time status of all AI backends:
- ✓ **Green**: Backend is available and ready
- ✗ **Red**: Backend is unavailable (with error details)

## Testing Backends

Use the admin actions to test your AI backends:

### Available Actions
1. **Test all AI backends**: Tests all available backends with sample resume
2. **Test Gemini AI backend**: Tests only the Gemini backend
3. **Test spaCy NLP backend**: Tests only the spaCy backend  
4. **Test rule-based backend**: Tests only the rule-based backend

### How to Test
1. Select the configuration record (there's only one)
2. Choose an action from the "Action" dropdown
3. Click "Go"
4. View the test results in the success/error messages

### Test Results
Test results show:
- Backend availability status
- Extracted information from sample resume:
  - Name, email, phone number
  - Number of skills found
  - Number of experience entries
  - Number of education entries
  - Confidence score
  - Which backend was actually used

## Troubleshooting

### Common Issues

**Gemini Backend Unavailable**
- Check your API key is correct
- Verify you have API quota remaining
- Ensure network connectivity to Google's servers

**spaCy Backend Unavailable**
- Install spaCy: `pip install spacy`
- Download language model: `python -m spacy download en_core_web_sm`
- Check the model name matches your installation

**Rule-based Backend Unavailable**
- This should always be available
- If not, check for Python import errors

### Configuration Tips

1. **File Size Limits**: Start with 10MB and adjust based on your server's memory
2. **Timeouts**: Increase for complex resumes or slow network connections
3. **Backend Selection**: Use "Auto" for best reliability with fallback
4. **API Keys**: Store securely and rotate regularly

## Security Notes

- API keys are stored encrypted in the database
- Temporary files are automatically cleaned up
- No resume content is permanently stored
- Admin actions use sample data only

## Support

If you encounter issues:
1. Check the backend status display for error details
2. Use the test actions to diagnose problems
3. Review Django logs for detailed error messages
4. Ensure all dependencies are properly installed