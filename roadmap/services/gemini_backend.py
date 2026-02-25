"""
Gemini AI backend service for resume processing
"""
import json
import logging
import re
from typing import Dict, List, Any, Optional
from django.conf import settings
import google.generativeai as genai
from .ai_processor import BaseAIBackend, AIProcessingError

logger = logging.getLogger(__name__)


class GeminiBackend(BaseAIBackend):
    """
    Google Gemini AI backend for resume processing
    """
    
    def __init__(self):
        self.model_name = "gemini-1.5-flash"
        self.api_key = self._get_api_key()
        self.model = None
        self._initialize_model()
    
    def _get_api_key(self) -> Optional[str]:
        """Get Gemini API key from settings or environment"""
        # Try to get from ResumeParserConfig model first
        try:
            from ..models import ResumeParserConfig
            config = ResumeParserConfig.objects.first()
            if config:
                return config.get_effective_gemini_api_key()
        except Exception:
            pass
        
        # Fallback to environment variable
        import os
        return os.getenv('GEMINI_API_KEY')
    
    def _initialize_model(self):
        """Initialize the Gemini model"""
        if not self.api_key:
            logger.warning("Gemini API key not found")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Gemini backend is available and properly configured"""
        if not self.api_key:
            return False
        
        if not self.model:
            self._initialize_model()
        
        return self.model is not None
    
    def get_backend_name(self) -> str:
        """Return the name of this backend"""
        return "Gemini AI"
    
    def process_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Process resume text using Gemini AI
        
        Args:
            text: Raw text extracted from resume
            
        Returns:
            Dict containing extracted information
            
        Raises:
            AIProcessingError: If processing fails
        """
        if not self.is_available():
            raise AIProcessingError("Gemini backend is not available")
        
        try:
            prompt = self._create_extraction_prompt(text)
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise AIProcessingError("Empty response from Gemini API")
            
            # Parse the JSON response
            extracted_data = self._parse_gemini_response(response.text)
            
            # Validate and clean the extracted data
            cleaned_data = self._validate_and_clean_data(extracted_data)
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            raise AIProcessingError(f"Gemini processing failed: {str(e)}")
    
    def _create_extraction_prompt(self, text: str) -> str:
        """
        Create structured prompt for resume data extraction
        
        Args:
            text: Resume text to process
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
You are an expert resume parser. Extract structured information from the following resume text and return it as valid JSON.

Resume Text:
{text}

Please extract the following information and return it as a JSON object with these exact keys:

{{
    "name": "Full name of the person (string or null)",
    "email": "Primary email address (string or null)",
    "phone": "Phone number (string or null)",
    "skills": ["List of technical and professional skills"],
    "experience": [
        {{
            "job_title": "Job title",
            "company": "Company name",
            "duration": "Employment duration or dates",
            "description": "Brief job description"
        }}
    ],
    "education": [
        {{
            "degree": "Degree or certification",
            "institution": "School or institution name",
            "year": "Graduation year or duration",
            "field": "Field of study"
        }}
    ],
    "confidence_score": 0.85
}}

Rules:
1. Return ONLY valid JSON, no additional text or formatting
2. Use null for missing information, not empty strings
3. Extract skills from throughout the resume (technical skills, tools, languages, etc.)
4. For experience, focus on professional work history
5. Include education, certifications, and relevant training
6. Set confidence_score between 0.0 and 1.0 based on how clear the information is
7. If you cannot find certain information, use null or empty arrays as appropriate

Resume text to parse:
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Gemini API
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Parsed JSON data
            
        Raises:
            AIProcessingError: If JSON parsing fails
        """
        try:
            # Clean the response text - remove any markdown formatting
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            data = json.loads(cleaned_text)
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise AIProcessingError(f"Invalid JSON response from Gemini: {str(e)}")
    
    def _validate_and_clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean extracted data
        
        Args:
            data: Raw extracted data from Gemini
            
        Returns:
            Cleaned and validated data
        """
        cleaned = {
            'name': self._clean_string(data.get('name')),
            'email': self._clean_email(data.get('email')),
            'phone': self._clean_phone(data.get('phone')),
            'skills': self._clean_skills(data.get('skills', [])),
            'experience': self._clean_experience(data.get('experience', [])),
            'education': self._clean_education(data.get('education', [])),
            'confidence_score': self._clean_confidence_score(data.get('confidence_score', 0.5))
        }
        
        return cleaned
    
    def _clean_string(self, value: Any) -> Optional[str]:
        """Clean and validate string values"""
        if not value or not isinstance(value, str):
            return None
        
        cleaned = value.strip()
        return cleaned if cleaned else None
    
    def _clean_email(self, value: Any) -> Optional[str]:
        """Clean and validate email addresses"""
        if not value or not isinstance(value, str):
            return None
        
        email = value.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return email
        
        return None
    
    def _clean_phone(self, value: Any) -> Optional[str]:
        """Clean and validate phone numbers"""
        if not value or not isinstance(value, str):
            return None
        
        # Remove common phone number formatting
        phone = re.sub(r'[^\d+\-\(\)\s]', '', value.strip())
        
        # Basic phone number validation (at least 10 digits)
        digits_only = re.sub(r'[^\d]', '', phone)
        if len(digits_only) >= 10:
            return phone.strip()
        
        return None
    
    def _clean_skills(self, value: Any) -> List[str]:
        """Clean and validate skills list"""
        if not isinstance(value, list):
            return []
        
        skills = []
        for skill in value:
            if isinstance(skill, str) and skill.strip():
                skills.append(skill.strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)
        
        return unique_skills
    
    def _clean_experience(self, value: Any) -> List[Dict[str, str]]:
        """Clean and validate experience list"""
        if not isinstance(value, list):
            return []
        
        experience = []
        for exp in value:
            if isinstance(exp, dict):
                cleaned_exp = {
                    'job_title': self._clean_string(exp.get('job_title')) or '',
                    'company': self._clean_string(exp.get('company')) or '',
                    'duration': self._clean_string(exp.get('duration')) or '',
                    'description': self._clean_string(exp.get('description')) or ''
                }
                
                # Only include if we have at least job title or company
                if cleaned_exp['job_title'] or cleaned_exp['company']:
                    experience.append(cleaned_exp)
        
        return experience
    
    def _clean_education(self, value: Any) -> List[Dict[str, str]]:
        """Clean and validate education list"""
        if not isinstance(value, list):
            return []
        
        education = []
        for edu in value:
            if isinstance(edu, dict):
                cleaned_edu = {
                    'degree': self._clean_string(edu.get('degree')) or '',
                    'institution': self._clean_string(edu.get('institution')) or '',
                    'year': self._clean_string(edu.get('year')) or '',
                    'field': self._clean_string(edu.get('field')) or ''
                }
                
                # Only include if we have at least degree or institution
                if cleaned_edu['degree'] or cleaned_edu['institution']:
                    education.append(cleaned_edu)
        
        return education
    
    def _clean_confidence_score(self, value: Any) -> float:
        """Clean and validate confidence score"""
        try:
            score = float(value)
            return max(0.0, min(1.0, score))  # Clamp between 0 and 1
        except (ValueError, TypeError):
            return 0.5  # Default confidence score