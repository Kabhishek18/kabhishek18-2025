"""
Rule-based fallback backend for resume processing
"""
import re
import logging
from typing import Dict, List, Any, Optional, Set
from .ai_processor import BaseAIBackend, AIProcessingError

logger = logging.getLogger(__name__)


class RuleBasedBackend(BaseAIBackend):
    """
    Rule-based fallback processor using regex patterns and keyword matching
    """
    
    def __init__(self):
        # Common skill keywords organized by category
        self.skill_keywords = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby',
                'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell',
                'bash', 'powershell', 'sql', 'html', 'css', 'xml', 'json', 'yaml'
            ],
            'frameworks_libraries': [
                'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'node.js', 'express',
                'spring', 'hibernate', 'laravel', 'rails', 'asp.net', 'xamarin', 'flutter',
                'react native', 'ionic', 'cordova', 'electron', 'bootstrap', 'jquery',
                'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite',
                'oracle', 'sql server', 'cassandra', 'dynamodb', 'firebase', 'couchdb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean', 'linode',
                'cloudflare', 'netlify', 'vercel', 'amazon web services', 'microsoft azure'
            ],
            'tools_technologies': [
                'git', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github', 'bitbucket',
                'jira', 'confluence', 'slack', 'teams', 'figma', 'sketch', 'photoshop',
                'illustrator', 'postman', 'insomnia', 'swagger', 'terraform', 'ansible',
                'linux', 'unix', 'windows', 'macos', 'nginx', 'apache'
            ]
        }
        
        # Flatten all skills for easier searching
        self.all_skills = set()
        for category_skills in self.skill_keywords.values():
            self.all_skills.update(skill.lower() for skill in category_skills)
        
        # Common job title patterns
        self.job_title_patterns = [
            r'\b(?:senior|junior|lead|principal|staff|associate|chief)\s+(?:software\s+)?(?:engineer|developer|programmer|architect)\b',
            r'\b(?:full\s+stack|frontend|backend|front-end|back-end)\s+(?:engineer|developer)\b',
            r'\b(?:data|machine\s+learning|ml|ai|artificial\s+intelligence)\s+(?:scientist|engineer|analyst|specialist)\b',
            r'\b(?:product|project|program|technical)\s+manager\b',
            r'\b(?:devops|site\s+reliability|sre)\s+engineer\b',
            r'\b(?:ui|ux|user\s+experience|user\s+interface)\s+(?:designer|engineer|developer)\b',
            r'\b(?:quality\s+assurance|qa|test|testing)\s+(?:engineer|analyst|specialist|manager)\b',
            r'\b(?:business|systems|data|financial)\s+analyst\b',
            r'\b(?:software|application|web|mobile)\s+(?:developer|engineer)\b',
            r'\b(?:database|system)\s+administrator\b',
            r'\b(?:network|security|cyber\s+security)\s+(?:engineer|specialist|analyst)\b'
        ]
        
        # Education degree patterns
        self.degree_patterns = [
            r'\b(?:bachelor|master|phd|doctorate|associate|diploma|certificate)\s+(?:of\s+)?(?:science|arts|engineering|business|computer\s+science|information\s+technology|mathematics|physics|chemistry)\b',
            r'\b(?:bs|ba|ms|ma|mba|phd|bsc|msc|beng|meng|btech|mtech)\b',
            r'\b(?:b\.s\.|b\.a\.|m\.s\.|m\.a\.|ph\.d\.|b\.sc\.|m\.sc\.|b\.eng\.|m\.eng\.)\b'
        ]
        
        # Institution patterns
        self.institution_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:University|College|Institute|School|Academy)\b',
            r'\b(?:University|College|Institute|School|Academy)\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            r'\b[A-Z]{2,}\b'  # Acronyms like MIT, UCLA, etc.
        ]
    
    def is_available(self) -> bool:
        """Rule-based backend is always available"""
        return True
    
    def get_backend_name(self) -> str:
        """Return the name of this backend"""
        return "Rule-based Processor"
    
    def process_resume_text(self, text: str) -> Dict[str, Any]:
        """
        Process resume text using rule-based extraction
        
        Args:
            text: Raw text extracted from resume
            
        Returns:
            Dict containing extracted information
        """
        try:
            extracted_data = {
                'name': self._extract_name(text),
                'email': self._extract_email(text),
                'phone': self._extract_phone(text),
                'skills': self._extract_skills(text),
                'experience': self._extract_experience(text),
                'education': self._extract_education(text),
                'confidence_score': 0.6  # Lower confidence for rule-based extraction
            }
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Rule-based processing failed: {e}")
            raise AIProcessingError(f"Rule-based processing failed: {str(e)}")
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract person's name using heuristics"""
        lines = text.split('\n')
        
        # Check first few lines for potential names
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that look like headers or contact info
            if any(keyword in line.lower() for keyword in [
                'resume', 'cv', 'curriculum vitae', 'email', 'phone', 'address',
                'linkedin', 'github', 'portfolio', 'website', 'objective', 'summary'
            ]):
                continue
            
            # Check if line looks like a name
            words = line.split()
            if 2 <= len(words) <= 4:
                # Check if all words are likely name parts (mostly alphabetic)
                if all(self._is_likely_name_word(word) for word in words):
                    return line
        
        return None
    
    def _is_likely_name_word(self, word: str) -> bool:
        """Check if a word is likely part of a name"""
        # Remove common punctuation
        clean_word = word.replace('.', '').replace(',', '')
        
        # Must be mostly alphabetic
        if not clean_word.isalpha():
            return False
        
        # Must be reasonable length
        if len(clean_word) < 2 or len(clean_word) > 20:
            return False
        
        # Must start with capital letter
        if not clean_word[0].isupper():
            return False
        
        return True
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        if emails:
            # Return the first valid email
            for email in emails:
                if self._is_valid_email(email):
                    return email.lower()
        
        return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        if '@' not in email:
            return False
        
        local, domain = email.split('@', 1)
        
        # Basic checks
        if not local or not domain:
            return False
        
        if '.' not in domain:
            return False
        
        # Check for reasonable length
        if len(email) > 254 or len(local) > 64:
            return False
        
        return True
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number using regex patterns"""
        phone_patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 123.456.7890 or 1234567890
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',    # (123) 456-7890
            r'\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # International
            r'\b\d{3}\s\d{3}\s\d{4}\b'         # 123 456 7890
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    # Pattern with groups
                    phone = ''.join(matches[0])
                else:
                    phone = matches[0]
                
                # Basic validation - must have at least 10 digits
                digits = re.sub(r'[^\d]', '', phone)
                if len(digits) >= 10:
                    return matches[0] if not isinstance(matches[0], tuple) else f"({matches[0][0]}) {matches[0][1]}-{matches[0][2]}"
        
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills using keyword matching"""
        skills = set()
        text_lower = text.lower()
        
        # Look for skills in the entire text
        for skill in self.all_skills:
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, text_lower):
                skills.add(skill.title())
        
        # Look for skills in dedicated skills section
        skills_section = self._extract_section_content(text, [
            'skills', 'technical skills', 'technologies', 'tools', 'programming languages',
            'software', 'platforms', 'frameworks', 'languages'
        ])
        
        if skills_section:
            # Split by common delimiters and extract potential skills
            skill_items = re.split(r'[,;•\n\t\|]', skills_section)
            for item in skill_items:
                item = item.strip()
                if item and 2 <= len(item) <= 30:
                    # Check if it's a known skill or looks like a technology
                    if item.lower() in self.all_skills or self._looks_like_skill(item):
                        skills.add(item)
        
        return sorted(list(skills))
    
    def _looks_like_skill(self, text: str) -> bool:
        """Check if text looks like a skill/technology"""
        # Skip common words that aren't skills
        common_words = {
            'and', 'or', 'with', 'using', 'including', 'such', 'as', 'for', 'in', 'on',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'have', 'has', 'had', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'do', 'does', 'did'
        }
        
        if text.lower() in common_words:
            return False
        
        # Look for patterns that suggest it's a technology
        tech_patterns = [
            r'^\d+\.\d+$',  # Version numbers like 3.8
            r'^[A-Z]+$',    # Acronyms like API, REST
            r'^[A-Z][a-z]+(?:[A-Z][a-z]*)*$',  # CamelCase like JavaScript
            r'.*(?:js|py|sql|css|html)$',  # File extensions
        ]
        
        for pattern in tech_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _extract_experience(self, text: str) -> List[Dict[str, str]]:
        """Extract work experience using pattern matching"""
        experience = []
        
        # Look for experience sections
        exp_section = self._extract_section_content(text, [
            'experience', 'work experience', 'employment', 'professional experience',
            'work history', 'career history', 'employment history'
        ])
        
        if not exp_section:
            return experience
        
        # Split into potential job entries (by double newlines or clear separators)
        job_entries = re.split(r'\n\s*\n|(?=\d{4})', exp_section)
        
        for entry in job_entries:
            if not entry.strip():
                continue
            
            job_info = self._parse_job_entry(entry)
            if job_info:
                experience.append(job_info)
        
        return experience
    
    def _parse_job_entry(self, entry: str) -> Optional[Dict[str, str]]:
        """Parse individual job entry using patterns"""
        lines = [line.strip() for line in entry.split('\n') if line.strip()]
        if not lines:
            return None
        
        job_info = {
            'job_title': '',
            'company': '',
            'duration': '',
            'description': ''
        }
        
        # Look for job title in the first few lines
        for line in lines[:3]:
            for pattern in self.job_title_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    job_info['job_title'] = match.group().strip()
                    break
            if job_info['job_title']:
                break
        
        # Look for company names
        company_patterns = [
            r'\bat\s+([A-Z][A-Za-z\s&.,Inc]+?)(?:\s*[-–—]\s*|\s*\(|\s*,|\s*$)',
            r'([A-Z][A-Za-z\s&.,Inc]+?)\s*[-–—]\s*',
            r'\(([A-Z][A-Za-z\s&.,Inc]+?)\)',
            r'^([A-Z][A-Za-z\s&.,Inc]{3,}?)(?:\s*[-–—]|\s*,|\s*$)'
        ]
        
        for line in lines[:3]:
            for pattern in company_patterns:
                match = re.search(pattern, line)
                if match:
                    company = match.group(1).strip()
                    # Clean up common suffixes
                    company = re.sub(r'\s*(?:Inc\.?|LLC|Corp\.?|Ltd\.?|Co\.?)$', '', company)
                    if len(company) > 2:
                        job_info['company'] = company
                        break
            if job_info['company']:
                break
        
        # Look for dates/duration
        date_patterns = [
            r'\b((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2}|present|current)\b',
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+((?:19|20)\d{2})\s*[-–—]\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+((?:19|20)\d{2}|present|current)\b',
            r'\b(\d{1,2}/(?:19|20)\d{2})\s*[-–—]\s*(\d{1,2}/(?:19|20)\d{2}|present|current)\b'
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if isinstance(match.groups(), tuple) and len(match.groups()) >= 2:
                        job_info['duration'] = f"{match.group(1)} - {match.group(2)}"
                    else:
                        job_info['duration'] = match.group().strip()
                    break
            if job_info['duration']:
                break
        
        # Use remaining content as description
        desc_lines = []
        for line in lines:
            # Skip lines that contain job title, company, or dates
            if (job_info['job_title'] and job_info['job_title'].lower() in line.lower()) or \
               (job_info['company'] and job_info['company'].lower() in line.lower()) or \
               (job_info['duration'] and any(date_part in line for date_part in job_info['duration'].split())):
                continue
            
            # Skip lines that are just dates or company info
            if re.search(r'^\d{4}|^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', line, re.IGNORECASE):
                continue
            
            desc_lines.append(line)
        
        if desc_lines:
            job_info['description'] = ' '.join(desc_lines)[:200]  # Limit description length
        
        # Only return if we have at least a job title or company
        if job_info['job_title'] or job_info['company']:
            return job_info
        
        return None
    
    def _extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information using patterns"""
        education = []
        
        # Look for education sections
        edu_section = self._extract_section_content(text, [
            'education', 'academic background', 'qualifications', 'degrees',
            'certifications', 'academic qualifications', 'schooling'
        ])
        
        if not edu_section:
            return education
        
        # Split into potential education entries
        edu_entries = re.split(r'\n\s*\n', edu_section)
        
        for entry in edu_entries:
            if not entry.strip():
                continue
            
            edu_info = self._parse_education_entry(entry)
            if edu_info:
                education.append(edu_info)
        
        return education
    
    def _parse_education_entry(self, entry: str) -> Optional[Dict[str, str]]:
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
            for pattern in self.degree_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    edu_info['degree'] = match.group().strip()
                    break
            if edu_info['degree']:
                break
        
        # Look for institution names
        for line in lines:
            for pattern in self.institution_patterns:
                match = re.search(pattern, line)
                if match:
                    institution = match.group().strip()
                    if len(institution) > 2:
                        edu_info['institution'] = institution
                        break
            if edu_info['institution']:
                break
        
        # Look for graduation year
        year_pattern = r'\b((?:19|20)\d{2})\b'
        for line in lines:
            matches = re.findall(year_pattern, line)
            if matches:
                # Take the most recent year if multiple found
                edu_info['year'] = max(matches)
                break
        
        # Try to extract field of study
        field_patterns = [
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:major|concentration|specialization):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:degree|major|studies)'
        ]
        
        for line in lines:
            for pattern in field_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    field = match.group(1).strip()
                    if len(field) > 2:
                        edu_info['field'] = field
                        break
            if edu_info['field']:
                break
        
        # Only return if we have at least degree or institution
        if edu_info['degree'] or edu_info['institution']:
            return edu_info
        
        return None
    
    def _extract_section_content(self, text: str, section_headers: List[str]) -> Optional[str]:
        """Extract content from a specific section"""
        text_lower = text.lower()
        
        for header in section_headers:
            # Look for section header (case insensitive)
            patterns = [
                rf'\n\s*{re.escape(header.lower())}\s*\n',  # Header on its own line
                rf'\n\s*{re.escape(header.lower())}\s*:',   # Header with colon
                rf'^{re.escape(header.lower())}\s*\n',      # Header at start
                rf'^{re.escape(header.lower())}\s*:'        # Header with colon at start
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.MULTILINE)
                if match:
                    start_pos = match.end()
                    
                    # Find the end of this section
                    next_section_patterns = [
                        r'\n\s*(?:experience|education|skills|projects|certifications|awards|references|summary|objective|contact)\s*\n',
                        r'\n\s*[A-Z][A-Z\s]{3,}\s*\n',  # All caps headers
                        r'\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*:\s*\n'  # Title case headers with colon
                    ]
                    
                    end_pos = len(text)
                    for end_pattern in next_section_patterns:
                        next_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
                        if next_match:
                            end_pos = start_pos + next_match.start()
                            break
                    
                    section_content = text[start_pos:end_pos].strip()
                    if section_content:
                        return section_content
        
        return None