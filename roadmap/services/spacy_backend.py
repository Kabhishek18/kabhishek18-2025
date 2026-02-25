"""
spaCy NLP backend service for resume processing
"""
import re
import logging
from typing import Dict, List, Any, Optional, Set
from .ai_processor import BaseAIBackend, AIProcessingError

logger = logging.getLogger(__name__)


class SpacyBackend(BaseAIBackend):
    """
    spaCy NLP backend for resume processing using entity recognition and pattern matching
    """
    
    def __init__(self):
        self.nlp = None
        self.model_name = "en_core_web_sm"
        self._initialize_model()
        
        # Predefined skill categories and keywords
        self.technical_skills = {
            'programming_languages': {
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 
                'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell',
                'bash', 'powershell', 'sql', 'html', 'css', 'xml', 'json'
            },
            'frameworks': {
                'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'node.js', 'express',
                'spring', 'hibernate', 'laravel', 'rails', 'asp.net', 'xamarin', 'flutter',
                'react native', 'ionic', 'cordova', 'electron'
            },
            'databases': {
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite',
                'oracle', 'sql server', 'cassandra', 'dynamodb', 'firebase', 'couchdb'
            },
            'cloud_platforms': {
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean', 'linode',
                'cloudflare', 'netlify', 'vercel'
            },
            'tools': {
                'git', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github', 'bitbucket',
                'jira', 'confluence', 'slack', 'teams', 'zoom', 'figma', 'sketch', 'photoshop',
                'illustrator', 'postman', 'insomnia', 'swagger', 'terraform', 'ansible'
            }
        }
        
        # Common job title patterns
        self.job_title_patterns = [
            r'\b(?:senior|junior|lead|principal|staff|associate)\s+(?:software\s+)?(?:engineer|developer|programmer)\b',
            r'\b(?:full\s+stack|frontend|backend|front-end|back-end)\s+(?:engineer|developer)\b',
            r'\b(?:data|machine\s+learning|ml|ai)\s+(?:scientist|engineer|analyst)\b',
            r'\b(?:product|project|program)\s+manager\b',
            r'\b(?:devops|site\s+reliability)\s+engineer\b',
            r'\b(?:ui|ux|user\s+experience|user\s+interface)\s+(?:designer|engineer)\b',
            r'\b(?:quality\s+assurance|qa)\s+(?:engineer|analyst|tester)\b',
            r'\b(?:business|systems|data)\s+analyst\b',
            r'\b(?:technical|solution)\s+architect\b',
            r'\b(?:software|application|web)\s+developer\b'
        ]
    
    def _initialize_model(self):
        """Initialize the spaCy model"""
        try:
            import spacy
            
            # Try to load the model
            try:
                self.nlp = spacy.load(self.model_name)
                logger.info(f"spaCy model {self.model_name} loaded successfully")
            except OSError:
                # Try alternative model names
                alternative_models = ["en_core_web_md", "en_core_web_lg", "en"]
                for model in alternative_models:
                    try:
                        self.nlp = spacy.load(model)
                        self.model_name = model
                        logger.info(f"spaCy model {model} loaded successfully")
                        break
                    except OSError:
                        continue
                
                if not self.nlp:
                    logger.error("No spaCy English model found. Please install with: python -m spacy download en_core_web_sm")
                    
        except ImportError:
            logger.error("spaCy not installed. Please install with: pip install spacy")
            self.nlp = None
    
    def is_available(self) -> bool:
        """Check if spaCy backend is available"""
        return self.nlp is not None
    
    def get_backend_name(self) -> str:
        """Return the name of this backend"""
        return f"spaCy NLP ({self.model_name})"
    
    def process_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Process resume text using spaCy NLP
        
        Args:
            text: Raw text extracted from resume
            
        Returns:
            Dict containing extracted information
            
        Raises:
            AIProcessingError: If processing fails
        """
        if not self.is_available():
            raise AIProcessingError("spaCy backend is not available")
        
        try:
            # Process text with spaCy
            doc = self.nlp(text)
            
            # Extract information using various methods
            extracted_data = {
                'name': self._extract_name(doc, text),
                'email': self._extract_email(text),
                'phone': self._extract_phone(text),
                'skills': self._extract_skills(doc, text),
                'experience': self._extract_experience(doc, text),
                'education': self._extract_education(doc, text),
                'confidence_score': self._calculate_confidence_score(doc, text)
            }
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"spaCy processing failed: {e}")
            raise AIProcessingError(f"spaCy processing failed: {str(e)}")
    
    def _extract_name(self, doc, text: str) -> Optional[str]:
        """Extract person's name using NER and heuristics"""
        # First try to find PERSON entities
        person_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
        
        if person_entities:
            # Return the first person entity that looks like a full name
            for name in person_entities:
                if len(name.split()) >= 2 and len(name) > 3:
                    return name
        
        # Fallback: look for name patterns at the beginning of the resume
        lines = text.split('\n')[:5]  # Check first 5 lines
        for line in lines:
            line = line.strip()
            if line and not any(keyword in line.lower() for keyword in ['email', 'phone', 'address', 'linkedin']):
                # Check if line looks like a name (2-4 words, mostly alphabetic)
                words = line.split()
                if 2 <= len(words) <= 4 and all(word.replace('.', '').isalpha() for word in words):
                    return line
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        if emails:
            # Return the first valid email
            for email in emails:
                if '.' in email.split('@')[1]:  # Basic validation
                    return email.lower()
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number using regex patterns"""
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 123.456.7890 or 1234567890
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',    # (123) 456-7890
            r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-123-456-7890
            r'\b\d{3}\s\d{3}\s\d{4}\b'         # 123 456 7890
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None
    
    def _extract_skills(self, doc, text: str) -> List[str]:
        """Extract skills using keyword matching and NER"""
        skills = set()
        text_lower = text.lower()
        
        # Extract from predefined skill categories
        for category, skill_set in self.technical_skills.items():
            for skill in skill_set:
                if skill in text_lower:
                    skills.add(skill.title())
        
        # Look for skills in common sections
        skills_section = self._extract_section_content(text, ['skills', 'technical skills', 'technologies'])
        if skills_section:
            # Split by common delimiters
            skill_items = re.split(r'[,;•\n\t]', skills_section)
            for item in skill_items:
                item = item.strip()
                if item and len(item) > 1 and len(item) < 30:
                    skills.add(item)
        
        # Extract technology mentions using NER and patterns
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG"] and len(ent.text) < 20:
                ent_lower = ent.text.lower()
                # Check if it's a known technology
                for category, skill_set in self.technical_skills.items():
                    if ent_lower in skill_set:
                        skills.add(ent.text)
        
        return sorted(list(skills))
    
    def _extract_experience(self, doc, text: str) -> List[Dict[str, str]]:
        """Extract work experience using pattern matching and NER"""
        experience = []
        
        # Look for experience/work sections
        exp_section = self._extract_section_content(text, [
            'experience', 'work experience', 'employment', 'professional experience',
            'work history', 'career history'
        ])
        
        if not exp_section:
            return experience
        
        # Split into potential job entries
        job_entries = re.split(r'\n\s*\n', exp_section)
        
        for entry in job_entries:
            if not entry.strip():
                continue
            
            job_info = self._parse_job_entry(entry)
            if job_info:
                experience.append(job_info)
        
        return experience
    
    def _parse_job_entry(self, entry: str) -> Optional[Dict[str, str]]:
        """Parse individual job entry"""
        lines = [line.strip() for line in entry.split('\n') if line.strip()]
        if not lines:
            return None
        
        job_info = {
            'job_title': '',
            'company': '',
            'duration': '',
            'description': ''
        }
        
        # First line often contains job title and/or company
        first_line = lines[0]
        
        # Look for job title patterns
        for pattern in self.job_title_patterns:
            match = re.search(pattern, first_line, re.IGNORECASE)
            if match:
                job_info['job_title'] = match.group().strip()
                break
        
        # Look for company names (often after "at" or in parentheses)
        company_patterns = [
            r'\bat\s+([A-Z][A-Za-z\s&.,]+?)(?:\s*[-–—]\s*|\s*\(|\s*$)',
            r'([A-Z][A-Za-z\s&.,]+?)\s*[-–—]\s*',
            r'\(([A-Z][A-Za-z\s&.,]+?)\)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, first_line)
            if match:
                job_info['company'] = match.group(1).strip()
                break
        
        # Look for dates/duration
        date_patterns = [
            r'\b\d{4}\s*[-–—]\s*\d{4}\b',
            r'\b\d{4}\s*[-–—]\s*(?:present|current)\b',
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\s*[-–—]\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b',
            r'\b\d{1,2}/\d{4}\s*[-–—]\s*\d{1,2}/\d{4}\b'
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    job_info['duration'] = match.group().strip()
                    break
            if job_info['duration']:
                break
        
        # Use remaining lines as description
        desc_lines = []
        for line in lines[1:]:
            if not any(re.search(pattern, line, re.IGNORECASE) for pattern in date_patterns):
                desc_lines.append(line)
        
        if desc_lines:
            job_info['description'] = ' '.join(desc_lines)[:200]  # Limit description length
        
        # Only return if we have at least a job title or company
        if job_info['job_title'] or job_info['company']:
            return job_info
        
        return None
    
    def _extract_education(self, doc, text: str) -> List[Dict[str, str]]:
        """Extract education information"""
        education = []
        
        # Look for education sections
        edu_section = self._extract_section_content(text, [
            'education', 'academic background', 'qualifications', 'degrees',
            'certifications', 'academic qualifications'
        ])
        
        if not edu_section:
            return education
        
        # Common degree patterns
        degree_patterns = [
            r'\b(?:bachelor|master|phd|doctorate|associate|diploma|certificate)\s+(?:of\s+)?(?:science|arts|engineering|business|computer\s+science|information\s+technology)\b',
            r'\b(?:bs|ba|ms|ma|mba|phd|bsc|msc|beng|meng)\b',
            r'\b(?:b\.s\.|b\.a\.|m\.s\.|m\.a\.|ph\.d\.)\b'
        ]
        
        # Split into potential education entries
        edu_entries = re.split(r'\n\s*\n', edu_section)
        
        for entry in edu_entries:
            if not entry.strip():
                continue
            
            edu_info = self._parse_education_entry(entry, degree_patterns)
            if edu_info:
                education.append(edu_info)
        
        return education
    
    def _parse_education_entry(self, entry: str, degree_patterns: List[str]) -> Optional[Dict[str, str]]:
        """Parse individual education entry"""
        lines = [line.strip() for line in entry.split('\n') if line.strip()]
        if not lines:
            return None
        
        edu_info = {
            'degree': '',
            'institution': '',
            'year': '',
            'field': ''
        }
        
        # Look for degree patterns
        for line in lines:
            for pattern in degree_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    edu_info['degree'] = match.group().strip()
                    break
            if edu_info['degree']:
                break
        
        # Look for institution names (often capitalized words)
        for line in lines:
            # Look for patterns like "University of X" or "X College"
            institution_patterns = [
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:University|College|Institute|School)\b',
                r'\b(?:University|College|Institute|School)\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            ]
            
            for pattern in institution_patterns:
                match = re.search(pattern, line)
                if match:
                    edu_info['institution'] = match.group().strip()
                    break
            if edu_info['institution']:
                break
        
        # Look for graduation year
        year_pattern = r'\b(19|20)\d{2}\b'
        for line in lines:
            match = re.search(year_pattern, line)
            if match:
                edu_info['year'] = match.group().strip()
                break
        
        # Only return if we have at least degree or institution
        if edu_info['degree'] or edu_info['institution']:
            return edu_info
        
        return None
    
    def _extract_section_content(self, text: str, section_headers: List[str]) -> Optional[str]:
        """Extract content from a specific section"""
        text_lower = text.lower()
        
        for header in section_headers:
            # Look for section header
            pattern = rf'\b{re.escape(header.lower())}\b'
            match = re.search(pattern, text_lower)
            
            if match:
                start_pos = match.end()
                
                # Find the end of this section (next major header or end of text)
                next_section_patterns = [
                    r'\n\s*(?:experience|education|skills|projects|certifications|awards|references)\s*\n',
                    r'\n\s*[A-Z][A-Z\s]{3,}\s*\n'  # All caps headers
                ]
                
                end_pos = len(text)
                for pattern in next_section_patterns:
                    next_match = re.search(pattern, text[start_pos:], re.IGNORECASE)
                    if next_match:
                        end_pos = start_pos + next_match.start()
                        break
                
                section_content = text[start_pos:end_pos].strip()
                if section_content:
                    return section_content
        
        return None
    
    def _calculate_confidence_score(self, doc, text: str) -> float:
        """Calculate confidence score based on extracted information quality"""
        score = 0.0
        
        # Check for presence of key information
        if self._extract_name(doc, text):
            score += 0.2
        if self._extract_email(text):
            score += 0.2
        if self._extract_phone(text):
            score += 0.1
        if self._extract_skills(doc, text):
            score += 0.2
        if self._extract_experience(doc, text):
            score += 0.2
        if self._extract_education(doc, text):
            score += 0.1
        
        # Bonus for well-structured text
        if len(text.split('\n')) > 10:  # Multi-line document
            score += 0.05
        if len(doc.ents) > 5:  # Good entity recognition
            score += 0.05
        
        return min(1.0, score)