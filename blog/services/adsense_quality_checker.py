"""
AdSense Quality Checker

This service provides comprehensive quality assessment specifically designed
to meet Google AdSense requirements for high-value content.

Key Assessment Areas:
1. Content Uniqueness and Originality
2. Content Depth and Value
3. User Experience and Readability
4. Technical SEO Compliance
5. AdSense Policy Compliance
"""

import re
import logging
from typing import Dict, List, Tuple
from collections import Counter
from datetime import datetime

from django.utils.html import strip_tags
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AdSenseQualityChecker:
    """
    Comprehensive quality checker for AdSense compliance
    
    Evaluates content against Google's quality guidelines and
    provides actionable recommendations for improvement.
    """
    
    def __init__(self):
        # AdSense quality thresholds
        self.min_word_count = 1200
        self.optimal_word_count = 1800
        self.min_quality_score = 85
        self.target_quality_score = 95
        
        # Readability targets
        self.target_flesch_score = 55  # College level
        self.max_sentence_length = 25
        self.optimal_paragraph_length = 150
        
        # Structure requirements
        self.min_headings = 6
        self.min_paragraphs = 10
        self.min_lists = 3

    def comprehensive_quality_assessment(self, content: str, title: str, excerpt: str) -> Dict:
        """
        Perform comprehensive quality assessment for AdSense compliance
        
        Args:
            content: HTML content of the post
            title: Post title
            excerpt: Post excerpt/meta description
            
        Returns:
            Dict containing detailed quality assessment
        """
        logger.info("Starting comprehensive AdSense quality assessment")
        
        assessment = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': 0,
            'category': 'needs_improvement',
            'adsense_ready': False,
            'issues': [],
            'recommendations': [],
            'metrics': {},
            'compliance_checks': {}
        }
        
        try:
            # Extract plain text for analysis
            plain_text = strip_tags(content)
            
            # Core quality assessments
            content_metrics = self._assess_content_metrics(plain_text, content)
            readability_metrics = self._assess_readability(plain_text)
            structure_metrics = self._assess_structure(content)
            seo_metrics = self._assess_seo_quality(title, excerpt, content)
            uniqueness_metrics = self._assess_uniqueness(plain_text, title)
            adsense_compliance = self._assess_adsense_compliance(content, title)
            
            # Combine all metrics
            assessment['metrics'] = {
                'content': content_metrics,
                'readability': readability_metrics,
                'structure': structure_metrics,
                'seo': seo_metrics,
                'uniqueness': uniqueness_metrics
            }
            
            assessment['compliance_checks'] = adsense_compliance
            
            # Calculate overall score
            assessment['overall_score'] = self._calculate_overall_score(
                content_metrics, readability_metrics, structure_metrics,
                seo_metrics, uniqueness_metrics, adsense_compliance
            )
            
            # Determine category and AdSense readiness
            assessment['category'] = self._determine_quality_category(assessment['overall_score'])
            assessment['adsense_ready'] = assessment['overall_score'] >= self.min_quality_score
            
            # Generate issues and recommendations
            assessment['issues'] = self._identify_issues(assessment['metrics'], assessment['compliance_checks'])
            assessment['recommendations'] = self._generate_recommendations(assessment['issues'], assessment['metrics'])
            
            logger.info(f"Quality assessment completed: {assessment['overall_score']:.1f}/100")
            return assessment
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            assessment['overall_score'] = 0
            assessment['issues'] = [f"Assessment failed: {str(e)}"]
            return assessment

    def _assess_content_metrics(self, plain_text: str, html_content: str) -> Dict:
        """Assess basic content metrics"""
        words = plain_text.split()
        word_count = len(words)
        char_count = len(plain_text)
        
        # Calculate content density (text vs HTML)
        html_length = len(html_content)
        content_density = len(plain_text) / html_length if html_length > 0 else 0
        
        # Assess word count score
        if word_count >= self.optimal_word_count:
            word_score = 100
        elif word_count >= self.min_word_count:
            word_score = 70 + (word_count - self.min_word_count) / (self.optimal_word_count - self.min_word_count) * 30
        else:
            word_score = max(0, (word_count / self.min_word_count) * 70)
        
        return {
            'word_count': word_count,
            'character_count': char_count,
            'content_density': content_density,
            'word_score': word_score,
            'meets_min_length': word_count >= self.min_word_count
        }

    def _assess_readability(self, text: str) -> Dict:
        """Assess readability metrics"""
        sentences = self._split_sentences(text)
        words = text.split()
        
        if not sentences or not words:
            return {'flesch_score': 0, 'readability_score': 0}
        
        # Calculate basic readability metrics
        avg_sentence_length = len(words) / len(sentences)
        
        # Simplified Flesch Reading Ease calculation
        # (More complex syllable counting would require additional libraries)
        avg_syllables = self._estimate_syllables(words)
        
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        flesch_score = max(0, min(100, flesch_score))
        
        # Score readability (target around 50-60 for technical content)
        if 45 <= flesch_score <= 65:
            readability_score = 100
        elif 35 <= flesch_score <= 75:
            readability_score = 80
        else:
            readability_score = max(0, 60 - abs(flesch_score - 55))
        
        return {
            'flesch_score': flesch_score,
            'avg_sentence_length': avg_sentence_length,
            'sentence_count': len(sentences),
            'readability_score': readability_score,
            'optimal_readability': 45 <= flesch_score <= 65
        }

    def _assess_structure(self, html_content: str) -> Dict:
        """Assess content structure and organization"""
        
        # Count structural elements
        h1_count = html_content.count('<h1>')
        h2_count = html_content.count('<h2>')
        h3_count = html_content.count('<h3>')
        h4_count = html_content.count('<h4>')
        
        p_count = html_content.count('<p>')
        ul_count = html_content.count('<ul>')
        ol_count = html_content.count('<ol>')
        li_count = html_content.count('<li>')
        
        code_count = html_content.count('<code>') + html_content.count('<pre>')
        
        total_headings = h2_count + h3_count + h4_count
        total_lists = ul_count + ol_count
        
        # Calculate structure score
        structure_score = 0
        
        # Heading structure (30 points)
        if h2_count >= 5:
            structure_score += 20
        elif h2_count >= 3:
            structure_score += 15
        elif h2_count >= 1:
            structure_score += 10
        
        if h3_count >= 3:
            structure_score += 10
        elif h3_count >= 1:
            structure_score += 5
        
        # Paragraph structure (25 points)
        if p_count >= 10:
            structure_score += 25
        elif p_count >= 6:
            structure_score += 20
        elif p_count >= 3:
            structure_score += 15
        
        # List usage (20 points)
        if total_lists >= 3:
            structure_score += 20
        elif total_lists >= 2:
            structure_score += 15
        elif total_lists >= 1:
            structure_score += 10
        
        # Code examples for technical content (15 points)
        if code_count >= 2:
            structure_score += 15
        elif code_count >= 1:
            structure_score += 10
        
        # Balanced structure (10 points)
        if total_headings >= 6 and p_count >= 8 and total_lists >= 2:
            structure_score += 10
        
        return {
            'h1_count': h1_count,
            'h2_count': h2_count,
            'h3_count': h3_count,
            'h4_count': h4_count,
            'paragraph_count': p_count,
            'list_count': total_lists,
            'list_item_count': li_count,
            'code_example_count': code_count,
            'total_headings': total_headings,
            'structure_score': min(100, structure_score),
            'well_structured': structure_score >= 80
        }

    def _assess_seo_quality(self, title: str, excerpt: str, content: str) -> Dict:
        """Assess SEO quality factors"""
        
        # Title assessment
        title_length = len(title)
        title_score = 0
        
        if 50 <= title_length <= 65:
            title_score = 100
        elif 40 <= title_length <= 70:
            title_score = 80
        elif 30 <= title_length <= 80:
            title_score = 60
        else:
            title_score = 40
        
        # Excerpt assessment
        excerpt_length = len(excerpt)
        excerpt_score = 0
        
        if 145 <= excerpt_length <= 160:
            excerpt_score = 100
        elif 130 <= excerpt_length <= 170:
            excerpt_score = 80
        elif 120 <= excerpt_length <= 180:
            excerpt_score = 60
        else:
            excerpt_score = 40
        
        # Keyword density (basic check)
        plain_content = strip_tags(content).lower()
        title_words = title.lower().split()
        
        # Check if title keywords appear in content
        keyword_presence = 0
        for word in title_words:
            if len(word) > 3 and word in plain_content:
                keyword_presence += 1
        
        keyword_score = min(100, (keyword_presence / len(title_words)) * 100) if title_words else 0
        
        # Overall SEO score
        seo_score = (title_score * 0.4 + excerpt_score * 0.4 + keyword_score * 0.2)
        
        return {
            'title_length': title_length,
            'title_score': title_score,
            'excerpt_length': excerpt_length,
            'excerpt_score': excerpt_score,
            'keyword_presence': keyword_presence,
            'keyword_score': keyword_score,
            'seo_score': seo_score,
            'seo_optimized': seo_score >= 80
        }

    def _assess_uniqueness(self, text: str, title: str) -> Dict:
        """Assess content uniqueness and originality"""
        
        # Basic uniqueness indicators
        words = text.lower().split()
        word_count = len(words)
        unique_words = len(set(words))
        
        # Vocabulary diversity
        vocabulary_diversity = unique_words / word_count if word_count > 0 else 0
        
        # Check for repetitive patterns
        word_frequency = Counter(words)
        most_common = word_frequency.most_common(10)
        
        # Calculate repetition score (lower is better)
        repetition_penalty = 0
        for word, count in most_common:
            if len(word) > 4 and count > word_count * 0.02:  # Word appears more than 2% of the time
                repetition_penalty += (count / word_count) * 10
        
        # Uniqueness score
        uniqueness_score = min(100, (vocabulary_diversity * 100) - repetition_penalty)
        
        return {
            'total_words': word_count,
            'unique_words': unique_words,
            'vocabulary_diversity': vocabulary_diversity,
            'repetition_penalty': repetition_penalty,
            'uniqueness_score': max(0, uniqueness_score),
            'highly_unique': uniqueness_score >= 80
        }

    def _assess_adsense_compliance(self, content: str, title: str) -> Dict:
        """Assess AdSense policy compliance"""
        
        compliance_issues = []
        compliance_score = 100
        
        # Check for prohibited content indicators
        prohibited_keywords = [
            'click here', 'click now', 'free money', 'get rich quick',
            'guaranteed income', 'work from home', 'make money fast'
        ]
        
        content_lower = content.lower()
        title_lower = title.lower()
        
        for keyword in prohibited_keywords:
            if keyword in content_lower or keyword in title_lower:
                compliance_issues.append(f"Contains potentially prohibited phrase: '{keyword}'")
                compliance_score -= 10
        
        # Check content quality indicators
        if len(strip_tags(content).split()) < 300:
            compliance_issues.append("Content too short for AdSense (minimum 300 words recommended)")
            compliance_score -= 20
        
        # Check for proper content structure
        if '<h2>' not in content:
            compliance_issues.append("Missing proper heading structure (H2 tags)")
            compliance_score -= 10
        
        if content.count('<p>') < 5:
            compliance_issues.append("Insufficient paragraph structure")
            compliance_score -= 10
        
        # Check for value-added content
        value_indicators = ['example', 'tutorial', 'guide', 'how to', 'best practices', 'tips']
        value_score = sum(1 for indicator in value_indicators if indicator in content_lower)
        
        if value_score < 2:
            compliance_issues.append("Content may lack sufficient value-added information")
            compliance_score -= 15
        
        return {
            'compliance_score': max(0, compliance_score),
            'compliance_issues': compliance_issues,
            'adsense_compliant': compliance_score >= 80,
            'value_indicators': value_score
        }

    def _calculate_overall_score(self, content_metrics: Dict, readability_metrics: Dict,
                               structure_metrics: Dict, seo_metrics: Dict,
                               uniqueness_metrics: Dict, compliance_metrics: Dict) -> float:
        """Calculate weighted overall quality score"""
        
        # Weighted scoring
        weights = {
            'content': 0.25,      # 25% - Content length and density
            'readability': 0.20,  # 20% - Readability and clarity
            'structure': 0.20,    # 20% - Content organization
            'seo': 0.15,         # 15% - SEO optimization
            'uniqueness': 0.10,   # 10% - Content uniqueness
            'compliance': 0.10    # 10% - AdSense compliance
        }
        
        scores = {
            'content': content_metrics.get('word_score', 0),
            'readability': readability_metrics.get('readability_score', 0),
            'structure': structure_metrics.get('structure_score', 0),
            'seo': seo_metrics.get('seo_score', 0),
            'uniqueness': uniqueness_metrics.get('uniqueness_score', 0),
            'compliance': compliance_metrics.get('compliance_score', 0)
        }
        
        overall_score = sum(scores[key] * weights[key] for key in weights.keys())
        return round(overall_score, 1)

    def _determine_quality_category(self, score: float) -> str:
        """Determine quality category based on score"""
        if score >= 95:
            return 'excellent'
        elif score >= 85:
            return 'good'
        elif score >= 70:
            return 'acceptable'
        elif score >= 50:
            return 'needs_improvement'
        else:
            return 'poor'

    def _identify_issues(self, metrics: Dict, compliance: Dict) -> List[str]:
        """Identify specific quality issues"""
        issues = []
        
        # Content issues
        content = metrics.get('content', {})
        if not content.get('meets_min_length', False):
            issues.append(f"Content too short: {content.get('word_count', 0)} words (minimum: {self.min_word_count})")
        
        # Readability issues
        readability = metrics.get('readability', {})
        if not readability.get('optimal_readability', False):
            flesch = readability.get('flesch_score', 0)
            issues.append(f"Readability suboptimal: Flesch score {flesch:.1f} (target: 45-65)")
        
        # Structure issues
        structure = metrics.get('structure', {})
        if not structure.get('well_structured', False):
            if structure.get('h2_count', 0) < 3:
                issues.append("Insufficient H2 headings for proper structure")
            if structure.get('paragraph_count', 0) < 6:
                issues.append("Insufficient paragraphs for content depth")
            if structure.get('list_count', 0) < 2:
                issues.append("Missing bullet points or numbered lists")
        
        # SEO issues
        seo = metrics.get('seo', {})
        if not seo.get('seo_optimized', False):
            title_len = seo.get('title_length', 0)
            if title_len < 40 or title_len > 70:
                issues.append(f"Title length suboptimal: {title_len} chars (optimal: 50-65)")
            
            excerpt_len = seo.get('excerpt_length', 0)
            if excerpt_len < 130 or excerpt_len > 170:
                issues.append(f"Meta description length suboptimal: {excerpt_len} chars (optimal: 145-160)")
        
        # Uniqueness issues
        uniqueness = metrics.get('uniqueness', {})
        if not uniqueness.get('highly_unique', False):
            diversity = uniqueness.get('vocabulary_diversity', 0)
            issues.append(f"Low vocabulary diversity: {diversity:.2f} (target: >0.6)")
        
        # Compliance issues
        compliance_issues = compliance.get('compliance_issues', [])
        issues.extend(compliance_issues)
        
        return issues

    def _generate_recommendations(self, issues: List[str], metrics: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Content recommendations
        content = metrics.get('content', {})
        word_count = content.get('word_count', 0)
        
        if word_count < self.min_word_count:
            needed = self.min_word_count - word_count
            recommendations.append(f"Add {needed} more words to reach minimum length requirement")
        
        if word_count < self.optimal_word_count:
            recommendations.append("Consider expanding content with more examples, case studies, or detailed explanations")
        
        # Structure recommendations
        structure = metrics.get('structure', {})
        
        if structure.get('h2_count', 0) < 5:
            recommendations.append("Add more H2 section headings to improve content organization")
        
        if structure.get('h3_count', 0) < 3:
            recommendations.append("Add H3 subheadings to create better content hierarchy")
        
        if structure.get('list_count', 0) < 3:
            recommendations.append("Include more bullet points or numbered lists for better readability")
        
        if structure.get('code_example_count', 0) == 0:
            recommendations.append("Add code examples or practical demonstrations if applicable")
        
        # Readability recommendations
        readability = metrics.get('readability', {})
        flesch_score = readability.get('flesch_score', 0)
        
        if flesch_score < 45:
            recommendations.append("Simplify sentence structure and use shorter sentences for better readability")
        elif flesch_score > 65:
            recommendations.append("Add more technical depth and complexity to match target audience")
        
        # SEO recommendations
        seo = metrics.get('seo', {})
        
        if seo.get('title_score', 0) < 80:
            recommendations.append("Optimize title length (50-65 characters) and include target keywords")
        
        if seo.get('excerpt_score', 0) < 80:
            recommendations.append("Optimize meta description (145-160 characters) with compelling copy")
        
        # General quality recommendations
        recommendations.extend([
            "Ensure all claims are supported with examples or evidence",
            "Add practical, actionable advice that readers can implement",
            "Include relevant internal and external links for additional value",
            "Proofread for grammar, spelling, and technical accuracy"
        ])
        
        return recommendations[:10]  # Limit to top 10 recommendations

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (could be improved with NLTK)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _estimate_syllables(self, words: List[str]) -> float:
        """Estimate average syllables per word (simplified)"""
        if not words:
            return 0
        
        total_syllables = 0
        for word in words:
            # Simple syllable estimation based on vowel groups
            vowels = 'aeiouy'
            syllable_count = 0
            prev_was_vowel = False
            
            for char in word.lower():
                if char in vowels:
                    if not prev_was_vowel:
                        syllable_count += 1
                    prev_was_vowel = True
                else:
                    prev_was_vowel = False
            
            # Adjust for silent 'e'
            if word.lower().endswith('e') and syllable_count > 1:
                syllable_count -= 1
            
            # Minimum of 1 syllable per word
            total_syllables += max(1, syllable_count)
        
        return total_syllables / len(words)


# Integration function for existing quality system
def generate_adsense_quality_report(content: str, title: str, excerpt: str) -> Dict:
    """
    Generate comprehensive AdSense quality report
    
    This function integrates with the existing quality system while providing
    enhanced AdSense-specific assessments.
    """
    checker = AdSenseQualityChecker()
    return checker.comprehensive_quality_assessment(content, title, excerpt)