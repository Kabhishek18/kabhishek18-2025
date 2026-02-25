"""
CRAG (Corrective Retrieval-Augmented Generation) Service

This service implements advanced content generation with quality correction
to address Google AdSense requirements for high-value, unique content.

CRAG Components:
1. Knowledge Retrieval - Gather relevant, authoritative information
2. Content Generation - Create original, high-quality content
3. Quality Assessment - Evaluate content against AdSense criteria
4. Corrective Refinement - Iteratively improve content quality
5. Fact Verification - Ensure accuracy and reliability
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import google.generativeai as genai
import requests
from django.conf import settings
from django.utils.text import slugify
from django.core.cache import cache

from ..models import Post, Category, Tag
from ..content_quality import generate_quality_report

logger = logging.getLogger(__name__)


class CRAGService:
    """
    Corrective Retrieval-Augmented Generation Service
    
    Implements a sophisticated content generation pipeline that:
    - Retrieves authoritative information from multiple sources
    - Generates original, high-quality content
    - Continuously assesses and corrects quality issues
    - Ensures AdSense compliance and uniqueness
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Quality thresholds for AdSense compliance
        self.min_quality_score = 85
        self.min_word_count = 1200
        self.max_retries = 3
        
        # Knowledge sources for retrieval
        self.knowledge_sources = [
            "authoritative technical documentation",
            "peer-reviewed research papers", 
            "industry best practices",
            "real-world case studies",
            "expert insights and analysis"
        ]

    def generate_high_quality_content(self, topic: str, target_audience: str = "developers") -> Optional[Dict]:
        """
        Generate high-quality content using CRAG methodology
        
        Args:
            topic: The topic to write about
            target_audience: Target audience for the content
            
        Returns:
            Dict containing generated content or None if failed
        """
        logger.info(f"Starting CRAG content generation for topic: {topic}")
        
        try:
            # Step 1: Knowledge Retrieval
            knowledge_context = self._retrieve_knowledge(topic)
            
            # Step 2: Initial Content Generation
            initial_content = self._generate_initial_content(topic, knowledge_context, target_audience)
            
            if not initial_content:
                logger.error("Failed to generate initial content")
                return None
            
            # Step 3: Quality Assessment and Correction Loop
            final_content = self._quality_correction_loop(initial_content, topic, knowledge_context)
            
            # Step 4: Final Validation
            if self._validate_final_content(final_content):
                logger.info(f"Successfully generated high-quality content for: {topic}")
                return final_content
            else:
                logger.error("Final content validation failed")
                return None
                
        except Exception as e:
            logger.error(f"CRAG content generation failed: {str(e)}")
            return None

    def _retrieve_knowledge(self, topic: str) -> Dict:
        """
        Retrieve relevant knowledge from multiple sources
        
        This simulates retrieval from authoritative sources to ensure
        content is grounded in factual, up-to-date information.
        """
        logger.info(f"Retrieving knowledge for topic: {topic}")
        
        # Generate knowledge retrieval prompt
        retrieval_prompt = f"""
        As an expert researcher, compile comprehensive, authoritative knowledge about: {topic}

        Provide detailed information from these perspectives:
        1. Technical fundamentals and core concepts
        2. Current industry best practices and standards
        3. Real-world implementation examples
        4. Common challenges and proven solutions
        5. Recent developments and future trends
        6. Performance considerations and optimization
        7. Security and compliance aspects
        8. Tools, frameworks, and ecosystem

        Focus on:
        - Factual, verifiable information
        - Practical, actionable insights
        - Expert-level depth and accuracy
        - Current, up-to-date knowledge
        - Multiple authoritative perspectives

        Format as comprehensive research notes with specific details, examples, and references.
        """
        
        try:
            response = self.model.generate_content(
                retrieval_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for factual retrieval
                    max_output_tokens=8000,
                )
            )
            
            knowledge_context = {
                'raw_knowledge': response.text,
                'topic': topic,
                'retrieved_at': datetime.now().isoformat(),
                'sources_consulted': self.knowledge_sources
            }
            
            logger.info("Knowledge retrieval completed successfully")
            return knowledge_context
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {str(e)}")
            return {'raw_knowledge': '', 'topic': topic, 'sources_consulted': []}

    def _generate_initial_content(self, topic: str, knowledge_context: Dict, target_audience: str) -> Optional[Dict]:
        """
        Generate initial content based on retrieved knowledge
        """
        logger.info("Generating initial content with retrieved knowledge")
        
        generation_prompt = f"""
        Create EXCEPTIONAL, ORIGINAL technical content using the provided research knowledge.

        **TOPIC:** {topic}
        **AUDIENCE:** {target_audience} (senior level)
        **QUALITY TARGET:** 90-100/100 (AdSense Premium Quality)

        **RESEARCH KNOWLEDGE:**
        {knowledge_context.get('raw_knowledge', '')[:4000]}

        **CRITICAL REQUIREMENTS:**

        1. **ORIGINALITY & UNIQUENESS:**
           - Write completely original content, not copied from any source
           - Provide unique insights and perspectives
           - Use your own explanations and examples
           - Avoid any copyrighted material or direct quotes

        2. **CONTENT DEPTH (1500-2000 words):**
           - Comprehensive coverage of the topic
           - Expert-level technical depth
           - Practical, actionable information
           - Real-world examples and use cases

        3. **STRUCTURE (Essential for Quality Score):**
           - 6-8 H2 main sections
           - 2-3 H3 subsections under each H2
           - 10-12 well-organized paragraphs
           - 4-5 bullet point lists
           - 2-3 code examples (if applicable)
           - Clear logical flow and transitions

        4. **READABILITY (Target Flesch 50-65):**
           - Clear, concise sentences (15-20 words average)
           - Mix of sentence lengths for rhythm
           - Active voice and direct language
           - Technical terms explained clearly
           - Smooth paragraph transitions

        5. **VALUE & EXPERTISE:**
           - Actionable insights and recommendations
           - Best practices from industry experience
           - Common pitfalls and how to avoid them
           - Performance optimization tips
           - Future considerations and trends

        **REQUIRED STRUCTURE:**

        <h2>Introduction and Overview</h2>
        <p>Compelling introduction that hooks the reader and outlines the value they'll get</p>

        <h2>Fundamental Concepts</h2>
        <p>Core concepts explained clearly</p>
        <h3>Key Components</h3>
        <ul><li>Component explanations with practical context</li></ul>

        <h2>Implementation Guide</h2>
        <p>Step-by-step implementation details</p>
        <h3>Practical Examples</h3>
        <pre><code>// Working code examples with explanations</code></pre>

        <h2>Best Practices and Optimization</h2>
        <ul><li>Proven best practices with reasoning</li></ul>
        <h3>Performance Considerations</h3>
        <p>Optimization strategies and techniques</p>

        <h2>Common Challenges and Solutions</h2>
        <p>Real-world problems and proven solutions</p>
        <h3>Troubleshooting Guide</h3>
        <ul><li>Common issues and fixes</li></ul>

        <h2>Advanced Techniques</h2>
        <p>Expert-level strategies and approaches</p>

        <h2>Tools and Ecosystem</h2>
        <p>Recommended tools, libraries, and resources</p>

        <h2>Future Trends and Considerations</h2>
        <p>Emerging trends and future outlook</p>

        <h2>Conclusion and Next Steps</h2>
        <p>Summary and actionable next steps</p>

        **OUTPUT AS JSON:**
        {{
            "title": "Compelling, specific title (50-65 characters)",
            "excerpt": "Engaging meta description with key benefits (145-155 chars)",
            "content": "Complete HTML content following structure (1500-2000 words)",
            "category": "Most appropriate category",
            "tags": ["specific", "relevant", "technical", "tags"],
            "image_prompt": "Professional, specific image description",
            "estimated_read_time": "7-10 min read",
            "key_takeaways": ["specific actionable insight 1", "practical tip 2", "expert recommendation 3"],
            "difficulty_level": "intermediate-advanced",
            "target_keywords": ["primary keyword", "secondary keyword", "long-tail keyword"]
        }}

        Create ORIGINAL, EXPERT-LEVEL content that provides genuine value to {target_audience}.
        """
        
        try:
            response = self.model.generate_content(
                generation_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,  # Balanced creativity and accuracy
                    max_output_tokens=20000,
                    top_p=0.9
                )
            )
            
            if not response.text:
                logger.error("Empty response from content generation")
                return None
            
            # Parse JSON response
            content_data = self._parse_json_response(response.text)
            
            if content_data:
                logger.info("Initial content generated successfully")
                return content_data
            else:
                logger.error("Failed to parse content generation response")
                return None
                
        except Exception as e:
            logger.error(f"Initial content generation failed: {str(e)}")
            return None

    def _quality_correction_loop(self, content: Dict, topic: str, knowledge_context: Dict) -> Dict:
        """
        Iteratively assess and improve content quality until it meets AdSense standards
        """
        logger.info("Starting quality correction loop")
        
        current_content = content.copy()
        
        for attempt in range(self.max_retries):
            logger.info(f"Quality assessment attempt {attempt + 1}/{self.max_retries}")
            
            # Assess current quality
            quality_report = self._assess_content_quality(current_content)
            quality_score = quality_report['score']
            
            logger.info(f"Current quality score: {quality_score}/100")
            
            # Check if quality meets requirements
            if quality_score >= self.min_quality_score:
                logger.info(f"Quality target achieved: {quality_score}/100")
                return current_content
            
            # Identify specific issues to correct
            issues = quality_report.get('issues', [])
            logger.info(f"Quality issues identified: {len(issues)}")
            
            # Generate corrective improvements
            if attempt < self.max_retries - 1:  # Don't correct on last attempt
                current_content = self._apply_corrections(current_content, issues, topic, knowledge_context)
            
        logger.warning(f"Quality correction loop completed. Final score: {quality_score}/100")
        return current_content

    def _assess_content_quality(self, content: Dict) -> Dict:
        """
        Assess content quality using multiple criteria
        """
        try:
            # Use existing quality assessment system
            quality_report = generate_quality_report(
                content.get('content', ''),
                content.get('title', ''),
                content.get('excerpt', '')
            )
            
            # Add CRAG-specific assessments
            crag_assessments = self._crag_quality_checks(content)
            quality_report.update(crag_assessments)
            
            return quality_report
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {str(e)}")
            return {'score': 0, 'issues': ['Quality assessment failed']}

    def _crag_quality_checks(self, content: Dict) -> Dict:
        """
        Additional quality checks specific to CRAG methodology
        """
        issues = []
        
        # Check content length
        content_text = content.get('content', '')
        word_count = len(content_text.split())
        
        if word_count < self.min_word_count:
            issues.append(f"Content too short: {word_count} words (minimum: {self.min_word_count})")
        
        # Check structure elements
        if '<h2>' not in content_text:
            issues.append("Missing H2 headings for proper structure")
        
        if '<h3>' not in content_text:
            issues.append("Missing H3 subheadings for detailed structure")
        
        if '<ul>' not in content_text and '<ol>' not in content_text:
            issues.append("Missing bullet points or numbered lists")
        
        # Check for code examples if technical content
        if any(tech_word in content.get('title', '').lower() for tech_word in ['api', 'code', 'programming', 'development', 'framework']):
            if '<code>' not in content_text and '<pre>' not in content_text:
                issues.append("Technical content missing code examples")
        
        # Check title and excerpt quality
        title = content.get('title', '')
        if len(title) < 40 or len(title) > 70:
            issues.append(f"Title length suboptimal: {len(title)} chars (optimal: 40-70)")
        
        excerpt = content.get('excerpt', '')
        if len(excerpt) < 140 or len(excerpt) > 160:
            issues.append(f"Excerpt length suboptimal: {len(excerpt)} chars (optimal: 140-160)")
        
        return {
            'crag_issues': issues,
            'word_count': word_count,
            'structure_score': max(0, 100 - len(issues) * 10)
        }

    def _apply_corrections(self, content: Dict, issues: List[str], topic: str, knowledge_context: Dict) -> Dict:
        """
        Apply specific corrections to address identified quality issues
        """
        logger.info(f"Applying corrections for {len(issues)} issues")
        
        correction_prompt = f"""
        IMPROVE this content to fix specific quality issues and achieve 90-100/100 quality score.

        **ORIGINAL CONTENT:**
        Title: {content.get('title', '')}
        Excerpt: {content.get('excerpt', '')}
        Content: {content.get('content', '')[:2000]}...

        **QUALITY ISSUES TO FIX:**
        {chr(10).join(f"- {issue}" for issue in issues[:5])}

        **IMPROVEMENT REQUIREMENTS:**
        1. Fix ALL identified issues completely
        2. Maintain the same topic and core message
        3. Enhance content depth and value
        4. Improve structure and readability
        5. Add more practical examples and insights
        6. Ensure 1500+ words with proper structure
        7. Keep all improvements original and unique

        **ENHANCED KNOWLEDGE CONTEXT:**
        {knowledge_context.get('raw_knowledge', '')[:2000]}

        **OUTPUT IMPROVED VERSION AS JSON:**
        {{
            "title": "Improved title addressing length/clarity issues",
            "excerpt": "Improved excerpt (145-155 chars) with better keywords",
            "content": "Complete improved HTML content (1500+ words, proper structure)",
            "category": "{content.get('category', '')}",
            "tags": {json.dumps(content.get('tags', []))},
            "image_prompt": "Enhanced image description",
            "estimated_read_time": "Updated read time",
            "key_takeaways": ["Enhanced takeaway 1", "Enhanced takeaway 2", "Enhanced takeaway 3"]
        }}

        Make significant improvements while keeping the content original and valuable.
        """
        
        try:
            response = self.model.generate_content(
                correction_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=20000,
                )
            )
            
            improved_content = self._parse_json_response(response.text)
            
            if improved_content:
                logger.info("Content corrections applied successfully")
                return improved_content
            else:
                logger.warning("Failed to parse corrected content, returning original")
                return content
                
        except Exception as e:
            logger.error(f"Content correction failed: {str(e)}")
            return content

    def _validate_final_content(self, content: Dict) -> bool:
        """
        Final validation to ensure content meets all AdSense requirements
        """
        logger.info("Performing final content validation")
        
        try:
            # Check required fields
            required_fields = ['title', 'excerpt', 'content', 'category', 'tags']
            for field in required_fields:
                if not content.get(field):
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check content length
            content_text = content.get('content', '')
            word_count = len(content_text.split())
            
            if word_count < self.min_word_count:
                logger.error(f"Content too short: {word_count} words")
                return False
            
            # Check quality score
            quality_report = self._assess_content_quality(content)
            quality_score = quality_report['score']
            
            if quality_score < self.min_quality_score:
                logger.error(f"Quality score too low: {quality_score}")
                return False
            
            # Check for proper structure
            if not self._validate_content_structure(content_text):
                logger.error("Content structure validation failed")
                return False
            
            logger.info(f"Final validation passed: {quality_score}/100, {word_count} words")
            return True
            
        except Exception as e:
            logger.error(f"Final validation failed: {str(e)}")
            return False

    def _validate_content_structure(self, content_text: str) -> bool:
        """
        Validate that content has proper structure for AdSense compliance
        """
        # Check for required HTML elements
        required_elements = ['<h2>', '<p>', '<ul>', '<li>']
        
        for element in required_elements:
            if element not in content_text:
                logger.error(f"Missing required HTML element: {element}")
                return False
        
        # Check for minimum number of sections
        h2_count = content_text.count('<h2>')
        if h2_count < 5:
            logger.error(f"Insufficient H2 sections: {h2_count} (minimum: 5)")
            return False
        
        # Check for paragraph distribution
        p_count = content_text.count('<p>')
        if p_count < 8:
            logger.error(f"Insufficient paragraphs: {p_count} (minimum: 8)")
            return False
        
        return True

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON response from AI model with error handling
        """
        try:
            # Clean response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            return json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            return None
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return None

    def create_post_from_crag_content(self, content_data: Dict, author) -> Optional[Post]:
        """
        Create a Django Post object from CRAG-generated content
        """
        try:
            # Create the post
            post = Post.objects.create(
                title=content_data['title'],
                slug=slugify(content_data['title']),
                author=author,
                content=content_data['content'],
                excerpt=content_data['excerpt'],
                status='draft',  # Start as draft for review
                allow_comments=True,
                table_of_contents=True,
                is_featured=False
            )
            
            # Add category
            category_name = content_data.get('category', 'Technology')
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'slug': slugify(category_name)}
            )
            post.categories.add(category)
            
            # Add tags
            for tag_name in content_data.get('tags', []):
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': slugify(tag_name)}
                )
                post.tags.add(tag)
            
            post.save()
            
            logger.info(f"Created post from CRAG content: {post.title}")
            return post
            
        except Exception as e:
            logger.error(f"Failed to create post from CRAG content: {str(e)}")
            return None

    def get_trending_topics(self) -> List[str]:
        """
        Get trending topics for content generation
        """
        return [
            "Advanced Python Performance Optimization Techniques",
            "Microservices Architecture: Design Patterns and Best Practices", 
            "AI-Powered Development Tools: Enhancing Developer Productivity",
            "Cloud-Native Security: Protecting Modern Applications",
            "GraphQL vs REST: Choosing the Right API Strategy",
            "Container Orchestration with Kubernetes: Production Strategies",
            "Real-Time Data Processing with Apache Kafka",
            "Modern Frontend Architecture: Micro-Frontends and Beyond",
            "Database Performance Tuning: Advanced Optimization Strategies",
            "DevOps Automation: CI/CD Pipeline Best Practices",
            "Serverless Computing: When and How to Use Function-as-a-Service",
            "API Gateway Patterns for Scalable Microservices",
            "Advanced Git Workflows for Large Development Teams",
            "Machine Learning Model Deployment in Production",
            "Web Application Security: Advanced Threat Protection"
        ]