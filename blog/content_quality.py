"""
Content Quality Checker for AdSense Compliance

This module provides comprehensive content quality validation including:
- Plagiarism/uniqueness checking
- Readability scoring
- SEO optimization validation
- Content structure analysis
- AdSense compliance checks
"""

import re
import requests
from typing import Dict, List, Tuple
from django.utils.html import strip_tags
from django.core.cache import cache
import hashlib
import logging

logger = logging.getLogger(__name__)


class ContentQualityChecker:
    """Comprehensive content quality validation for AdSense compliance"""
    
    # Minimum requirements for AdSense
    MIN_WORD_COUNT = 300
    RECOMMENDED_WORD_COUNT = 800  # Lowered from 1000 for more realistic scoring
    MIN_READABILITY_SCORE = 30  # Flesch Reading Ease
    MAX_KEYWORD_DENSITY = 3.0  # Percentage
    MIN_UNIQUENESS_SCORE = 85  # Percentage
    EXCELLENT_WORD_COUNT = 1500  # For 100 score
    
    def __init__(self, content: str, title: str = "", excerpt: str = ""):
        self.content = content
        self.title = title
        self.excerpt = excerpt
        self.plain_text = strip_tags(content)
        self.words = self._extract_words()
        
    def _extract_words(self) -> List[str]:
        """Extract words from plain text"""
        # Remove extra whitespace and split
        text = re.sub(r'\s+', ' ', self.plain_text)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return words
    
    def check_all(self) -> Dict:
        """Run all quality checks and return comprehensive report"""
        results = {
            'passed': False,
            'score': 0,
            'issues': [],
            'warnings': [],
            'recommendations': [],
            'metrics': {}
        }
        
        # Word count check
        word_count_result = self.check_word_count()
        results['metrics']['word_count'] = word_count_result
        
        # Readability check
        readability_result = self.check_readability()
        results['metrics']['readability'] = readability_result
        
        # Content structure check
        structure_result = self.check_content_structure()
        results['metrics']['structure'] = structure_result
        
        # Keyword density check
        keyword_result = self.check_keyword_density()
        results['metrics']['keyword_density'] = keyword_result
        
        # Uniqueness check (basic)
        uniqueness_result = self.check_uniqueness()
        results['metrics']['uniqueness'] = uniqueness_result
        
        # SEO check
        seo_result = self.check_seo()
        results['metrics']['seo'] = seo_result
        
        # Compile issues and warnings
        all_checks = [
            word_count_result,
            readability_result,
            structure_result,
            keyword_result,
            uniqueness_result,
            seo_result
        ]
        
        for check in all_checks:
            if not check.get('passed', False):
                results['issues'].extend(check.get('issues', []))
            results['warnings'].extend(check.get('warnings', []))
            results['recommendations'].extend(check.get('recommendations', []))
        
        # Calculate overall score (0-100)
        scores = [check.get('score', 0) for check in all_checks]
        results['score'] = sum(scores) / len(scores) if scores else 0
        
        # Pass if score >= 70 and no critical issues
        results['passed'] = results['score'] >= 70 and len(results['issues']) == 0
        
        return results
    
    def check_word_count(self) -> Dict:
        """Check if content meets minimum word count requirements"""
        word_count = len(self.words)
        
        # Improved scoring: 
        # 300 words = 50 score
        # 800 words = 85 score
        # 1500+ words = 100 score
        if word_count >= self.EXCELLENT_WORD_COUNT:
            score = 100
        elif word_count >= self.RECOMMENDED_WORD_COUNT:
            # Scale from 85 to 100 between 800-1500 words
            score = 85 + ((word_count - self.RECOMMENDED_WORD_COUNT) / (self.EXCELLENT_WORD_COUNT - self.RECOMMENDED_WORD_COUNT)) * 15
        elif word_count >= self.MIN_WORD_COUNT:
            # Scale from 50 to 85 between 300-800 words
            score = 50 + ((word_count - self.MIN_WORD_COUNT) / (self.RECOMMENDED_WORD_COUNT - self.MIN_WORD_COUNT)) * 35
        else:
            # Below minimum
            score = (word_count / self.MIN_WORD_COUNT) * 50
        
        result = {
            'name': 'Word Count',
            'value': word_count,
            'passed': word_count >= self.MIN_WORD_COUNT,
            'score': min(100, score),
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        if word_count < self.MIN_WORD_COUNT:
            result['issues'].append(
                f"Content too short ({word_count} words). Minimum: {self.MIN_WORD_COUNT} words."
            )
        elif word_count < self.RECOMMENDED_WORD_COUNT:
            result['warnings'].append(
                f"Content length ({word_count} words) is below recommended {self.RECOMMENDED_WORD_COUNT} words for higher score."
            )
            result['recommendations'].append(
                f"Add more content to reach {self.RECOMMENDED_WORD_COUNT}+ words for better score."
            )
        elif word_count < self.EXCELLENT_WORD_COUNT:
            result['recommendations'].append(
                f"Excellent! Add {self.EXCELLENT_WORD_COUNT - word_count} more words to reach perfect score."
            )
        
        return result
    
    def check_readability(self) -> Dict:
        """Calculate Flesch Reading Ease score"""
        sentences = self._count_sentences()
        words = len(self.words)
        syllables = self._count_syllables()
        
        if sentences == 0 or words == 0:
            return {
                'name': 'Readability',
                'value': 0,
                'passed': False,
                'score': 0,
                'issues': ['Cannot calculate readability - insufficient content'],
                'warnings': [],
                'recommendations': []
            }
        
        # Flesch Reading Ease formula
        flesch_score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        flesch_score = max(0, min(100, flesch_score))  # Clamp between 0-100
        
        # Adjusted scoring for technical content:
        # 30-40 = 70 score (acceptable for technical)
        # 40-50 = 80 score (good)
        # 50-60 = 90 score (very good)
        # 60+ = 100 score (excellent)
        if flesch_score >= 60:
            adjusted_score = 100
        elif flesch_score >= 50:
            adjusted_score = 90 + ((flesch_score - 50) / 10) * 10
        elif flesch_score >= 40:
            adjusted_score = 80 + ((flesch_score - 40) / 10) * 10
        elif flesch_score >= 30:
            adjusted_score = 70 + ((flesch_score - 30) / 10) * 10
        else:
            adjusted_score = (flesch_score / 30) * 70
        
        result = {
            'name': 'Readability',
            'value': round(flesch_score, 1),
            'passed': flesch_score >= self.MIN_READABILITY_SCORE,
            'score': adjusted_score,
            'issues': [],
            'warnings': [],
            'recommendations': [],
            'interpretation': self._interpret_readability(flesch_score)
        }
        
        if flesch_score < self.MIN_READABILITY_SCORE:
            result['issues'].append(
                f"Readability score too low ({flesch_score:.1f}). Content may be too difficult to read."
            )
            result['recommendations'].append(
                "Use shorter sentences and simpler words to improve readability."
            )
        elif flesch_score < 40:
            result['warnings'].append(
                f"Readability score ({flesch_score:.1f}) is acceptable for technical content but could be improved."
            )
        
        return result
    
    def _count_sentences(self) -> int:
        """Count sentences in text"""
        sentences = re.split(r'[.!?]+', self.plain_text)
        return len([s for s in sentences if s.strip()])
    
    def _count_syllables(self) -> int:
        """Estimate syllable count (simplified)"""
        total = 0
        for word in self.words:
            # Simple syllable counting heuristic
            word = word.lower()
            count = 0
            vowels = 'aeiouy'
            previous_was_vowel = False
            
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not previous_was_vowel:
                    count += 1
                previous_was_vowel = is_vowel
            
            # Adjust for silent e
            if word.endswith('e'):
                count -= 1
            
            # Ensure at least 1 syllable
            if count == 0:
                count = 1
            
            total += count
        
        return total
    
    def _interpret_readability(self, score: float) -> str:
        """Interpret Flesch Reading Ease score"""
        if score >= 90:
            return "Very Easy (5th grade)"
        elif score >= 80:
            return "Easy (6th grade)"
        elif score >= 70:
            return "Fairly Easy (7th grade)"
        elif score >= 60:
            return "Standard (8th-9th grade)"
        elif score >= 50:
            return "Fairly Difficult (10th-12th grade)"
        elif score >= 30:
            return "Difficult (College)"
        else:
            return "Very Difficult (College graduate)"
    
    def check_content_structure(self) -> Dict:
        """Check HTML structure and formatting"""
        score = 100
        
        # Check for headings
        h2_count = len(re.findall(r'<h2[^>]*>', self.content, re.IGNORECASE))
        h3_count = len(re.findall(r'<h3[^>]*>', self.content, re.IGNORECASE))
        
        # Check for lists
        ul_count = len(re.findall(r'<ul[^>]*>', self.content, re.IGNORECASE))
        ol_count = len(re.findall(r'<ol[^>]*>', self.content, re.IGNORECASE))
        
        # Check for paragraphs
        p_count = len(re.findall(r'<p[^>]*>', self.content, re.IGNORECASE))
        
        # Check for code blocks (good for technical content)
        code_count = len(re.findall(r'<code[^>]*>|<pre[^>]*>', self.content, re.IGNORECASE))
        
        # Check for images
        img_count = len(re.findall(r'<img[^>]*>', self.content, re.IGNORECASE))
        
        # Improved scoring system
        result = {
            'name': 'Content Structure',
            'passed': True,
            'score': score,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # H2 headings (important)
        if h2_count == 0:
            result['warnings'].append("No H2 headings found. Add section headings for better structure.")
            score -= 15  # Reduced from 20
        elif h2_count >= 3:
            # Bonus for good structure
            score = min(100, score + 5)
        
        # Lists (nice to have)
        if ul_count + ol_count == 0:
            result['recommendations'].append("Consider adding bullet points or numbered lists for better readability.")
            score -= 5  # Reduced from 10
        elif ul_count + ol_count >= 2:
            # Bonus for lists
            score = min(100, score + 5)
        
        # Paragraphs (important)
        if p_count < 3:
            result['warnings'].append("Few paragraphs detected. Break content into smaller sections.")
            score -= 10  # Reduced from 15
        elif p_count >= 5:
            # Bonus for good paragraph structure
            score = min(100, score + 5)
        
        # Code blocks (bonus for technical content)
        if code_count > 0:
            score = min(100, score + 5)
        
        # Images (bonus)
        if img_count > 0:
            score = min(100, score + 5)
        
        result['score'] = max(0, score)
        result['value'] = {
            'h2_headings': h2_count,
            'h3_headings': h3_count,
            'lists': ul_count + ol_count,
            'paragraphs': p_count,
            'code_blocks': code_count,
            'images': img_count
        }
        
        result['passed'] = result['score'] >= 70
        
        return result
    
    def check_keyword_density(self) -> Dict:
        """Check for keyword stuffing"""
        if not self.words:
            return {
                'name': 'Keyword Density',
                'passed': True,
                'score': 100,
                'issues': [],
                'warnings': [],
                'recommendations': []
            }
        
        # Count word frequency
        word_freq = {}
        for word in self.words:
            if len(word) > 3:  # Only count words longer than 3 chars
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Find most common words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_words = sorted_words[:5]
        
        total_words = len(self.words)
        max_density = 0
        problematic_words = []
        
        for word, count in top_words:
            density = (count / total_words) * 100
            if density > self.MAX_KEYWORD_DENSITY:
                max_density = max(max_density, density)
                problematic_words.append((word, density))
        
        result = {
            'name': 'Keyword Density',
            'value': top_words,
            'passed': len(problematic_words) == 0,
            'score': 100 if len(problematic_words) == 0 else max(0, 100 - (max_density * 10)),
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        if problematic_words:
            result['warnings'].append(
                f"High keyword density detected: {', '.join([f'{w} ({d:.1f}%)' for w, d in problematic_words])}"
            )
            result['recommendations'].append(
                "Use synonyms and varied vocabulary to avoid keyword stuffing."
            )
        
        return result
    
    def check_uniqueness(self) -> Dict:
        """Basic uniqueness check using content fingerprinting"""
        # Create content fingerprint
        content_hash = hashlib.md5(self.plain_text.encode()).hexdigest()
        
        # Check cache for similar content
        cache_key = f"content_fingerprint_{content_hash}"
        existing = cache.get(cache_key)
        
        result = {
            'name': 'Content Uniqueness',
            'value': content_hash,
            'passed': existing is None,
            'score': 100 if existing is None else 0,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        if existing:
            result['issues'].append(
                "Duplicate content detected. This content appears to be identical to existing content."
            )
        else:
            # Store fingerprint for 90 days
            cache.set(cache_key, True, 60 * 60 * 24 * 90)
        
        # Additional check: look for common AI-generated phrases
        ai_phrases = [
            "in this comprehensive guide",
            "in this article, we will explore",
            "let's dive into",
            "it's important to note that",
            "in today's digital landscape"
        ]
        
        ai_phrase_count = sum(1 for phrase in ai_phrases if phrase in self.plain_text.lower())
        
        if ai_phrase_count >= 3:
            result['warnings'].append(
                "Content contains common AI-generated phrases. Consider adding more original voice."
            )
            result['score'] = max(70, result['score'])
        
        return result
    
    def check_seo(self) -> Dict:
        """Check SEO optimization"""
        result = {
            'name': 'SEO Optimization',
            'passed': True,
            'score': 100,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check title length
        if self.title:
            title_len = len(self.title)
            if title_len < 30:
                result['warnings'].append(f"Title too short ({title_len} chars). Aim for 50-60 characters.")
                result['score'] -= 15
            elif title_len > 60:
                result['warnings'].append(f"Title too long ({title_len} chars). May be truncated in search results.")
                result['score'] -= 10
        else:
            result['issues'].append("No title provided.")
            result['score'] -= 30
        
        # Check excerpt/meta description
        if self.excerpt:
            excerpt_len = len(self.excerpt)
            if excerpt_len < 120:
                result['warnings'].append(f"Meta description too short ({excerpt_len} chars). Aim for 150-160.")
                result['score'] -= 10
            elif excerpt_len > 160:
                result['warnings'].append(f"Meta description too long ({excerpt_len} chars). May be truncated.")
                result['score'] -= 5
        else:
            result['warnings'].append("No meta description provided.")
            result['score'] -= 20
        
        # Check for images
        img_count = len(re.findall(r'<img[^>]*>', self.content, re.IGNORECASE))
        if img_count == 0:
            result['recommendations'].append("Add images to improve engagement and SEO.")
            result['score'] -= 10
        
        # Check for internal/external links
        link_count = len(re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>', self.content, re.IGNORECASE))
        if link_count == 0:
            result['recommendations'].append("Add relevant internal and external links.")
            result['score'] -= 10
        
        result['passed'] = result['score'] >= 70
        
        return result


class PlagiarismChecker:
    """Check content for plagiarism using various methods"""
    
    def __init__(self, content: str):
        self.content = strip_tags(content)
        self.sentences = self._extract_sentences()
    
    def _extract_sentences(self) -> List[str]:
        """Extract sentences from content"""
        sentences = re.split(r'[.!?]+', self.content)
        return [s.strip() for s in sentences if len(s.strip()) > 20]
    
    def check_online(self, api_key: str = None) -> Dict:
        """
        Check content against online sources
        Note: This is a placeholder. In production, integrate with:
        - Copyscape API
        - Grammarly Plagiarism Checker
        - Quetext API
        - PlagScan API
        """
        result = {
            'checked': False,
            'uniqueness_score': 100,
            'matches_found': 0,
            'sources': [],
            'message': 'Online plagiarism checking not configured'
        }
        
        if not api_key:
            logger.warning("No plagiarism checker API key configured")
            return result
        
        # Placeholder for actual API integration
        # Example: Copyscape, Grammarly, etc.
        
        return result
    
    def check_local_database(self) -> Dict:
        """Check against previously published content in database"""
        from blog.models import Post
        
        result = {
            'checked': True,
            'uniqueness_score': 100,
            'matches_found': 0,
            'similar_posts': []
        }
        
        # Get all published posts
        posts = Post.objects.filter(status='published').values('id', 'title', 'content')
        
        # Simple similarity check using sentence overlap
        for post in posts:
            post_sentences = set(re.split(r'[.!?]+', strip_tags(post['content'])))
            our_sentences = set(self.sentences)
            
            # Calculate Jaccard similarity
            intersection = len(our_sentences.intersection(post_sentences))
            union = len(our_sentences.union(post_sentences))
            
            if union > 0:
                similarity = (intersection / union) * 100
                
                if similarity > 15:  # More than 15% similar
                    result['matches_found'] += 1
                    result['similar_posts'].append({
                        'post_id': post['id'],
                        'title': post['title'],
                        'similarity': round(similarity, 2)
                    })
        
        if result['matches_found'] > 0:
            # Reduce uniqueness score based on matches
            result['uniqueness_score'] = max(0, 100 - (result['matches_found'] * 20))
        
        return result


def generate_quality_report(content: str, title: str = "", excerpt: str = "") -> Dict:
    """Generate comprehensive quality report for content"""
    checker = ContentQualityChecker(content, title, excerpt)
    quality_results = checker.check_all()
    
    # Add plagiarism check
    plag_checker = PlagiarismChecker(content)
    plag_results = plag_checker.check_local_database()
    
    quality_results['plagiarism'] = plag_results
    
    # Adjust overall score based on plagiarism
    if plag_results['uniqueness_score'] < 85:
        quality_results['score'] = min(quality_results['score'], plag_results['uniqueness_score'])
        quality_results['passed'] = False
        quality_results['issues'].append(
            f"Content similarity detected ({100 - plag_results['uniqueness_score']:.0f}% similar to existing content)"
        )
    
    return quality_results
