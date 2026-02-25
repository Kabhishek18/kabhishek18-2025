"""
LinkedIn Content Formatting Utilities

This module provides utilities for formatting blog post content for LinkedIn posting.
Handles character limits, hashtag generation, and media URL extraction.
"""

import re
import logging
import time
from typing import List, Optional, Dict, Tuple, Any
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.conf import settings
from urllib.parse import urljoin
from django.core.cache import cache
from .linkedin_image_service import LinkedInImageService
from .linkedin_metrics_logger import linkedin_metrics_logger


logger = logging.getLogger(__name__)


class HashtagGenerator:
    """
    Intelligent hashtag generation for LinkedIn posts.
    
    This class provides comprehensive hashtag generation capabilities for LinkedIn posts,
    supporting multiple generation sources, custom rules, blacklists, and validation.
    
    Features:
    - Multi-source hashtag generation (tags, categories, content analysis)
    - Custom category-specific hashtag rules
    - Hashtag blacklist filtering
    - LinkedIn-compliant hashtag validation
    - Performance monitoring and error handling
    - Fallback mechanisms for reliability
    
    Usage:
        # Initialize with configuration
        generator = HashtagGenerator(config)
        
        # Generate hashtags for a blog post
        hashtags = generator.generate_hashtags(blog_post, max_count=5)
        
        # Generate from specific sources
        tag_hashtags = generator.generate_from_tags(blog_post, 3)
        category_hashtags = generator.generate_from_categories(blog_post, 3)
        content_hashtags = generator.generate_from_content(blog_post, 3)
    
    Configuration Format:
        {
            'enable_hashtags': True,
            'max_hashtags': 5,
            'custom_hashtag_rules': {
                'category_slug': {
                    'required_hashtags': ['#RequiredTag'],
                    'suggested_hashtags': ['#SuggestedTag1', '#SuggestedTag2'],
                    'max_hashtags': 4,
                    'priority': 1
                }
            },
            'hashtag_blacklist': ['spam', 'clickbait', 'urgent']
        }
    
    Hashtag Generation Priority (highest to lowest):
        1. Custom rules (required hashtags)
        2. Post tags
        3. Post categories
        4. Content analysis
    
    Validation Rules:
        - Must start with letter or underscore
        - Can contain letters, numbers, underscores only
        - Length between 1-100 characters
        - Must not be in blacklist
        - Proper LinkedIn formatting (#hashtag)
    
    Error Handling:
        - Graceful degradation on generation failures
        - Comprehensive logging for debugging
        - Fallback hashtag generation
        - Performance metrics tracking
    """
    
    # Default hashtag limits and validation rules
    DEFAULT_MAX_HASHTAGS = 5
    MIN_HASHTAG_LENGTH = 2
    MAX_HASHTAG_LENGTH = 100
    
    def __init__(self, config=None):
        """
        Initialize the hashtag generator with configuration.
        
        Args:
            config: Dictionary with hashtag configuration or LinkedInConfig instance
        """
        try:
            if hasattr(config, 'get_hashtag_config'):
                # LinkedInConfig instance
                self.config = config.get_hashtag_config()
            elif isinstance(config, dict):
                # Dictionary configuration
                self.config = config
            else:
                # Default configuration
                self.config = {
                    'enable_hashtags': True,
                    'max_hashtags': self.DEFAULT_MAX_HASHTAGS,
                    'custom_hashtag_rules': {},
                    'hashtag_blacklist': []
                }
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            logger.error(f"Error initializing HashtagGenerator: {e}")
            # Fallback to safe default configuration
            self.config = {
                'enable_hashtags': True,
                'max_hashtags': self.DEFAULT_MAX_HASHTAGS,
                'custom_hashtag_rules': {},
                'hashtag_blacklist': []
            }
    
    def _validate_config(self):
        """
        Validate hashtag configuration and apply fallbacks for invalid values.
        """
        try:
            # Ensure config is a dictionary
            if not isinstance(self.config, dict):
                logger.warning("Invalid hashtag config format, using defaults")
                self.config = {
                    'enable_hashtags': True,
                    'max_hashtags': self.DEFAULT_MAX_HASHTAGS,
                    'custom_hashtag_rules': {},
                    'hashtag_blacklist': []
                }
                return
            
            # Validate enable_hashtags
            if 'enable_hashtags' not in self.config or not isinstance(self.config['enable_hashtags'], bool):
                logger.warning("Invalid enable_hashtags setting, defaulting to True")
                self.config['enable_hashtags'] = True
            
            # Validate max_hashtags
            max_hashtags = self.config.get('max_hashtags', self.DEFAULT_MAX_HASHTAGS)
            if not isinstance(max_hashtags, int) or max_hashtags < 0 or max_hashtags > 30:
                logger.warning(f"Invalid max_hashtags value: {max_hashtags}, using default: {self.DEFAULT_MAX_HASHTAGS}")
                self.config['max_hashtags'] = self.DEFAULT_MAX_HASHTAGS
            
            # Validate custom_hashtag_rules
            if 'custom_hashtag_rules' not in self.config or not isinstance(self.config['custom_hashtag_rules'], dict):
                logger.warning("Invalid custom_hashtag_rules format, using empty dict")
                self.config['custom_hashtag_rules'] = {}
            
            # Validate hashtag_blacklist
            if 'hashtag_blacklist' not in self.config or not isinstance(self.config['hashtag_blacklist'], list):
                logger.warning("Invalid hashtag_blacklist format, using empty list")
                self.config['hashtag_blacklist'] = []
            
            logger.debug("Hashtag configuration validated successfully")
            
        except Exception as e:
            logger.error(f"Error validating hashtag configuration: {e}")
            # Use safe defaults
            self.config = {
                'enable_hashtags': True,
                'max_hashtags': self.DEFAULT_MAX_HASHTAGS,
                'custom_hashtag_rules': {},
                'hashtag_blacklist': []
            }
    
    def generate_hashtags(self, blog_post, max_count=None):
        """
        Generate hashtags for a blog post using all available sources with comprehensive error handling.
        
        Args:
            blog_post: Blog Post model instance
            max_count: Maximum number of hashtags to generate (overrides config)
            
        Returns:
            List of formatted hashtags
        """
        start_time = time.time()
        post_id = getattr(blog_post, 'id', 'unknown')
        post_title = getattr(blog_post, 'title', 'Unknown Title')
        
        try:
            # Check if hashtags are enabled
            if not self.config.get('enable_hashtags', True):
                logger.debug(f"Hashtag generation disabled for post {post_id} ('{post_title}')")
                self._log_hashtag_metrics(post_id, 'disabled', 0, 0, start_time)
                return []
            
            # Validate max_count parameter
            max_hashtags = max_count or self.config.get('max_hashtags', self.DEFAULT_MAX_HASHTAGS)
            if not isinstance(max_hashtags, int) or max_hashtags <= 0:
                logger.warning(f"Invalid max_hashtags value: {max_hashtags} for post {post_id}, using default: {self.DEFAULT_MAX_HASHTAGS}")
                max_hashtags = self.DEFAULT_MAX_HASHTAGS
            
            # Validate blog_post parameter
            if not blog_post:
                logger.error("Blog post is None, cannot generate hashtags")
                self._log_hashtag_metrics('none', 'error', 0, 0, start_time)
                return []
            
            logger.debug(f"Starting hashtag generation for post {post_id} ('{post_title}') with max_hashtags={max_hashtags}")
            
            # Collect hashtags from different sources with error handling
            all_hashtags = []
            generation_errors = []
            source_counts = {'custom': 0, 'tags': 0, 'categories': 0, 'content': 0}
            
            # 1. Get hashtags from custom rules (highest priority)
            try:
                custom_hashtags = self._get_custom_hashtags_for_post(blog_post)
                all_hashtags.extend(custom_hashtags)
                source_counts['custom'] = len(custom_hashtags)
                logger.debug(f"Generated {len(custom_hashtags)} custom hashtags for post {post_id}")
            except Exception as e:
                error_msg = f"Error generating custom hashtags: {e}"
                logger.warning(f"Custom hashtag generation failed for post {post_id}: {error_msg}")
                generation_errors.append(error_msg)
            
            # 2. Generate from tags (high priority)
            if len(all_hashtags) < max_hashtags:
                try:
                    tag_hashtags = self.generate_from_tags(blog_post, max_hashtags - len(all_hashtags))
                    all_hashtags.extend(tag_hashtags)
                    source_counts['tags'] = len(tag_hashtags)
                    logger.debug(f"Generated {len(tag_hashtags)} hashtags from tags for post {post_id}")
                except Exception as e:
                    error_msg = f"Error generating hashtags from tags: {e}"
                    logger.warning(f"Tag hashtag generation failed for post {post_id}: {error_msg}")
                    generation_errors.append(error_msg)
            
            # 3. Generate from categories (medium priority)
            if len(all_hashtags) < max_hashtags:
                try:
                    category_hashtags = self.generate_from_categories(blog_post, max_hashtags - len(all_hashtags))
                    all_hashtags.extend(category_hashtags)
                    source_counts['categories'] = len(category_hashtags)
                    logger.debug(f"Generated {len(category_hashtags)} hashtags from categories for post {post_id}")
                except Exception as e:
                    error_msg = f"Error generating hashtags from categories: {e}"
                    logger.warning(f"Category hashtag generation failed for post {post_id}: {error_msg}")
                    generation_errors.append(error_msg)
            
            # 4. Generate from content (lower priority)
            if len(all_hashtags) < max_hashtags:
                try:
                    content_hashtags = self.generate_from_content(blog_post, max_hashtags - len(all_hashtags))
                    all_hashtags.extend(content_hashtags)
                    source_counts['content'] = len(content_hashtags)
                    logger.debug(f"Generated {len(content_hashtags)} hashtags from content for post {post_id}")
                except Exception as e:
                    error_msg = f"Error generating hashtags from content: {e}"
                    logger.warning(f"Content hashtag generation failed for post {post_id}: {error_msg}")
                    generation_errors.append(error_msg)
            
            # If no hashtags were generated and there were errors, log a warning
            if not all_hashtags and generation_errors:
                logger.warning(f"No hashtags generated for post {post_id} ('{post_title}') due to errors: {generation_errors}")
                self._log_hashtag_metrics(post_id, 'failed', 0, len(generation_errors), start_time, 
                                        source_counts=source_counts, errors=generation_errors)
                return []
            
            # Remove duplicates while preserving order
            try:
                unique_hashtags = []
                seen = set()
                for hashtag in all_hashtags:
                    if hashtag and isinstance(hashtag, str):
                        hashtag_lower = hashtag.lower()
                        if hashtag_lower not in seen:
                            unique_hashtags.append(hashtag)
                            seen.add(hashtag_lower)
                
                duplicates_removed = len(all_hashtags) - len(unique_hashtags)
                if duplicates_removed > 0:
                    logger.debug(f"Removed {duplicates_removed} duplicate hashtags for post {post_id}: {len(all_hashtags)} -> {len(unique_hashtags)}")
            except Exception as e:
                logger.error(f"Error removing duplicate hashtags for post {post_id}: {e}")
                unique_hashtags = all_hashtags  # Fallback to original list
            
            # Apply blacklist filtering with error handling
            try:
                filtered_hashtags = self.filter_blacklisted_hashtags(unique_hashtags)
                blacklisted_count = len(unique_hashtags) - len(filtered_hashtags)
                if blacklisted_count > 0:
                    logger.debug(f"Applied blacklist filter for post {post_id}: removed {blacklisted_count} hashtags ({len(unique_hashtags)} -> {len(filtered_hashtags)})")
            except Exception as e:
                logger.warning(f"Error applying blacklist filter for post {post_id}: {e}")
                filtered_hashtags = unique_hashtags  # Fallback to unfiltered list
            
            # Apply final validation and formatting with error handling
            valid_hashtags = []
            validation_errors = 0
            
            for hashtag in filtered_hashtags:
                try:
                    formatted = self.format_hashtag(hashtag)
                    if formatted and self.validate_hashtag(formatted):
                        valid_hashtags.append(formatted)
                    else:
                        validation_errors += 1
                except Exception as e:
                    logger.debug(f"Error formatting/validating hashtag '{hashtag}' for post {post_id}: {e}")
                    validation_errors += 1
            
            if validation_errors > 0:
                logger.debug(f"Filtered out {validation_errors} invalid hashtags during validation for post {post_id}")
            
            # Return up to max_hashtags
            final_hashtags = valid_hashtags[:max_hashtags]
            
            # Log successful generation with detailed metrics
            generation_time = time.time() - start_time
            logger.info(f"Generated {len(final_hashtags)} valid hashtags for post {post_id} ('{post_title}') in {generation_time:.3f}s")
            
            # If we have very few hashtags and there were errors, try fallback generation
            fallback_used = False
            if len(final_hashtags) < 2 and generation_errors:
                logger.info(f"Low hashtag count ({len(final_hashtags)}) for post {post_id}, attempting fallback generation")
                fallback_hashtags = self._generate_fallback_hashtags(blog_post, max_hashtags)
                if fallback_hashtags:
                    final_hashtags.extend(fallback_hashtags)
                    final_hashtags = final_hashtags[:max_hashtags]  # Ensure we don't exceed limit
                    fallback_used = True
                    logger.info(f"Added {len(fallback_hashtags)} fallback hashtags for post {post_id}, total: {len(final_hashtags)}")
            
            # Log comprehensive metrics
            self._log_hashtag_metrics(
                post_id, 'success', len(final_hashtags), len(generation_errors), start_time,
                source_counts=source_counts, 
                validation_errors=validation_errors,
                fallback_used=fallback_used,
                final_hashtags=final_hashtags
            )
            
            # Log feature usage metrics
            linkedin_metrics_logger.log_feature_usage(
                'hashtag_generation', 
                str(post_id), 
                True, 
                generation_time,
                {
                    'hashtag_count': len(final_hashtags),
                    'source_counts': source_counts,
                    'fallback_used': fallback_used,
                    'validation_errors': validation_errors
                }
            )
            
            return final_hashtags
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Critical error in hashtag generation for post {post_id} ('{post_title}') after {generation_time:.3f}s: {e}")
            self._log_hashtag_metrics(post_id, 'critical_error', 0, 1, start_time, errors=[str(e)])
            
            # Log feature usage failure
            linkedin_metrics_logger.log_feature_usage(
                'hashtag_generation', 
                str(post_id), 
                False, 
                generation_time,
                {'error': str(e), 'error_type': 'critical_error'}
            )
            
            # Return empty list as ultimate fallback
            return []
    
    def _generate_fallback_hashtags(self, blog_post, max_count):
        """
        Generate basic fallback hashtags when primary generation fails.
        
        Args:
            blog_post: Blog Post model instance
            max_count: Maximum number of hashtags to generate
            
        Returns:
            List of basic hashtags
        """
        fallback_hashtags = []
        
        try:
            # Try to generate very basic hashtags from post title
            if hasattr(blog_post, 'title') and blog_post.title:
                title_words = blog_post.title.lower().split()
                for word in title_words[:3]:  # Take first 3 words
                    if len(word) >= 3 and word.isalpha():
                        formatted = self.format_hashtag(word)
                        if formatted and self.validate_hashtag(formatted):
                            fallback_hashtags.append(formatted)
                            if len(fallback_hashtags) >= max_count:
                                break
            
            # Add generic fallback hashtags if still not enough
            if len(fallback_hashtags) < 2:
                generic_hashtags = ['#blog', '#content', '#article']
                for hashtag in generic_hashtags:
                    if self.validate_hashtag(hashtag):
                        fallback_hashtags.append(hashtag)
                        if len(fallback_hashtags) >= max_count:
                            break
            
            logger.debug(f"Generated {len(fallback_hashtags)} fallback hashtags")
            return fallback_hashtags
            
        except Exception as e:
            logger.error(f"Error generating fallback hashtags: {e}")
            return []
    
    def generate_from_tags(self, blog_post, max_count):
        """
        Generate hashtags from blog post tags with error handling.
        
        Args:
            blog_post: Blog Post model instance
            max_count: Maximum number of hashtags to generate
            
        Returns:
            List of hashtags from post tags
        """
        try:
            # Validate inputs
            if not blog_post:
                logger.warning("Blog post is None in generate_from_tags")
                return []
            
            if not isinstance(max_count, int) or max_count <= 0:
                logger.warning(f"Invalid max_count in generate_from_tags: {max_count}")
                return []
            
            # Check if post has tags attribute and tags exist
            if not hasattr(blog_post, 'tags'):
                logger.debug(f"Post {getattr(blog_post, 'id', 'unknown')} has no tags attribute")
                return []
            
            try:
                if not blog_post.tags.exists():
                    logger.debug(f"Post {getattr(blog_post, 'id', 'unknown')} has no tags")
                    return []
            except Exception as e:
                logger.warning(f"Error checking if tags exist for post {getattr(blog_post, 'id', 'unknown')}: {e}")
                return []
            
            hashtags = []
            
            try:
                # Get tag names with error handling
                tag_names = list(blog_post.tags.values_list('name', flat=True)[:max_count * 2])  # Get more than needed
                logger.debug(f"Retrieved {len(tag_names)} tag names for post {getattr(blog_post, 'id', 'unknown')}")
            except Exception as e:
                logger.error(f"Error retrieving tag names for post {getattr(blog_post, 'id', 'unknown')}: {e}")
                return []
            
            # Process each tag name with individual error handling
            for tag_name in tag_names:
                if len(hashtags) >= max_count:
                    break
                
                try:
                    if not tag_name or not isinstance(tag_name, str):
                        logger.debug(f"Skipping invalid tag name: {tag_name}")
                        continue
                    
                    formatted_hashtag = self.format_hashtag(tag_name)
                    if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                        hashtags.append(formatted_hashtag)
                        logger.debug(f"Added hashtag from tag: {formatted_hashtag}")
                    else:
                        logger.debug(f"Tag '{tag_name}' did not produce valid hashtag")
                        
                except Exception as e:
                    logger.warning(f"Error processing tag '{tag_name}': {e}")
                    continue
            
            logger.debug(f"Generated {len(hashtags)} hashtags from tags for post {getattr(blog_post, 'id', 'unknown')}")
            return hashtags
            
        except Exception as e:
            logger.error(f"Critical error in generate_from_tags for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            return []
    
    def generate_from_categories(self, blog_post, max_count):
        """
        Generate hashtags from blog post categories with error handling.
        
        Args:
            blog_post: Blog Post model instance
            max_count: Maximum number of hashtags to generate
            
        Returns:
            List of hashtags from post categories
        """
        try:
            # Validate inputs
            if not blog_post:
                logger.warning("Blog post is None in generate_from_categories")
                return []
            
            if not isinstance(max_count, int) or max_count <= 0:
                logger.warning(f"Invalid max_count in generate_from_categories: {max_count}")
                return []
            
            # Check if post has categories attribute and categories exist
            if not hasattr(blog_post, 'categories'):
                logger.debug(f"Post {getattr(blog_post, 'id', 'unknown')} has no categories attribute")
                return []
            
            try:
                if not blog_post.categories.exists():
                    logger.debug(f"Post {getattr(blog_post, 'id', 'unknown')} has no categories")
                    return []
            except Exception as e:
                logger.warning(f"Error checking if categories exist for post {getattr(blog_post, 'id', 'unknown')}: {e}")
                return []
            
            hashtags = []
            
            try:
                # Get category names with error handling
                category_names = list(blog_post.categories.values_list('name', flat=True)[:max_count * 2])  # Get more than needed
                logger.debug(f"Retrieved {len(category_names)} category names for post {getattr(blog_post, 'id', 'unknown')}")
            except Exception as e:
                logger.error(f"Error retrieving category names for post {getattr(blog_post, 'id', 'unknown')}: {e}")
                return []
            
            # Process each category name with individual error handling
            for category_name in category_names:
                if len(hashtags) >= max_count:
                    break
                
                try:
                    if not category_name or not isinstance(category_name, str):
                        logger.debug(f"Skipping invalid category name: {category_name}")
                        continue
                    
                    formatted_hashtag = self.format_hashtag(category_name)
                    if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                        hashtags.append(formatted_hashtag)
                        logger.debug(f"Added hashtag from category: {formatted_hashtag}")
                    else:
                        logger.debug(f"Category '{category_name}' did not produce valid hashtag")
                        
                except Exception as e:
                    logger.warning(f"Error processing category '{category_name}': {e}")
                    continue
            
            logger.debug(f"Generated {len(hashtags)} hashtags from categories for post {getattr(blog_post, 'id', 'unknown')}")
            return hashtags
            
        except Exception as e:
            logger.error(f"Critical error in generate_from_categories for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            return []
    
    def generate_from_content(self, blog_post, max_count):
        """
        Generate hashtags from blog post content using keyword extraction with error handling.
        
        Args:
            blog_post: Blog Post model instance
            max_count: Maximum number of hashtags to generate
            
        Returns:
            List of hashtags extracted from content
        """
        try:
            # Validate inputs
            if not blog_post:
                logger.warning("Blog post is None in generate_from_content")
                return []
            
            if not isinstance(max_count, int) or max_count <= 0:
                logger.warning(f"Invalid max_count in generate_from_content: {max_count}")
                return []
            
            # Get content to analyze with error handling
            content_text = ""
            
            try:
                # Try to get title
                if hasattr(blog_post, 'title') and blog_post.title:
                    content_text += str(blog_post.title) + " "
            except Exception as e:
                logger.warning(f"Error accessing post title: {e}")
            
            try:
                # Try to get excerpt
                if hasattr(blog_post, 'excerpt') and blog_post.excerpt:
                    clean_excerpt = strip_tags(str(blog_post.excerpt))
                    content_text += clean_excerpt + " "
                elif hasattr(blog_post, 'content') and blog_post.content:
                    # Use first 500 characters of content if no excerpt
                    clean_content = strip_tags(str(blog_post.content))
                    content_text += clean_content[:500] + " "
            except Exception as e:
                logger.warning(f"Error accessing post content/excerpt: {e}")
            
            # Check if we have any content to work with
            if not content_text.strip():
                logger.debug(f"No content available for hashtag generation for post {getattr(blog_post, 'id', 'unknown')}")
                return []
            
            # Extract potential hashtags using simple keyword extraction
            try:
                hashtags = self._extract_keywords_from_text(content_text, max_count)
                logger.debug(f"Generated {len(hashtags)} hashtags from content for post {getattr(blog_post, 'id', 'unknown')}")
                return hashtags
            except Exception as e:
                logger.error(f"Error extracting keywords from content for post {getattr(blog_post, 'id', 'unknown')}: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Critical error in generate_from_content for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            return []
    
    def _extract_keywords_from_text(self, text, max_count):
        """
        Extract potential hashtags from text content with error handling.
        
        Args:
            text: Text to analyze
            max_count: Maximum number of keywords to extract
            
        Returns:
            List of potential hashtags
        """
        try:
            # Validate inputs
            if not text or not isinstance(text, str):
                logger.warning(f"Invalid text input for keyword extraction: {type(text)}")
                return []
            
            if not isinstance(max_count, int) or max_count <= 0:
                logger.warning(f"Invalid max_count for keyword extraction: {max_count}")
                return []
            
            # Clean and normalize text with error handling
            try:
                clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
                words = clean_text.split()
            except Exception as e:
                logger.error(f"Error cleaning text for keyword extraction: {e}")
                return []
            
            if not words:
                logger.debug("No words found after text cleaning")
                return []
            
            # Filter out common stop words and short words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
                'above', 'below', 'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been',
                'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
            }
            
            # Count word frequency with error handling
            word_freq = {}
            processed_words = 0
            
            for word in words:
                try:
                    if (len(word) >= 3 and 
                        word not in stop_words and 
                        not word.isdigit() and 
                        word.isalpha()):
                        word_freq[word] = word_freq.get(word, 0) + 1
                        processed_words += 1
                except Exception as e:
                    logger.debug(f"Error processing word '{word}': {e}")
                    continue
            
            logger.debug(f"Processed {processed_words} words, found {len(word_freq)} unique keywords")
            
            if not word_freq:
                logger.debug("No valid keywords found after filtering")
                return []
            
            # Sort by frequency and get top candidates
            try:
                sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            except Exception as e:
                logger.error(f"Error sorting word frequencies: {e}")
                return []
            
            # Convert to hashtags with error handling
            hashtags = []
            conversion_errors = 0
            
            for word, freq in sorted_words[:max_count * 2]:  # Get more candidates than needed
                try:
                    formatted_hashtag = self.format_hashtag(word)
                    if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                        hashtags.append(formatted_hashtag)
                        if len(hashtags) >= max_count:
                            break
                    else:
                        conversion_errors += 1
                except Exception as e:
                    logger.debug(f"Error converting word '{word}' to hashtag: {e}")
                    conversion_errors += 1
                    continue
            
            if conversion_errors > 0:
                logger.debug(f"Failed to convert {conversion_errors} words to valid hashtags")
            
            logger.debug(f"Successfully extracted {len(hashtags)} hashtags from text")
            return hashtags
            
        except Exception as e:
            logger.error(f"Critical error in keyword extraction: {e}")
            return []
    
    def _get_custom_hashtags_for_post(self, blog_post):
        """
        Get custom hashtags defined for the post's categories.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            List of custom hashtags
        """
        custom_rules = self.config.get('custom_hashtag_rules', {})
        if not custom_rules or not hasattr(blog_post, 'categories'):
            return []
        
        custom_hashtags = []
        
        # Check each category for custom rules
        for category in blog_post.categories.all():
            category_key = category.slug if hasattr(category, 'slug') else category.name.lower()
            
            if category_key in custom_rules:
                rules = custom_rules[category_key]
                
                # Add required hashtags
                if isinstance(rules, dict) and 'required_hashtags' in rules:
                    required = rules['required_hashtags']
                    if isinstance(required, list):
                        custom_hashtags.extend(required)
                
                # Add suggested hashtags if space allows
                if isinstance(rules, dict) and 'suggested_hashtags' in rules:
                    suggested = rules['suggested_hashtags']
                    if isinstance(suggested, list):
                        custom_hashtags.extend(suggested)
                
                # Handle simple list format
                elif isinstance(rules, list):
                    custom_hashtags.extend(rules)
        
        # Format and validate custom hashtags
        formatted_hashtags = []
        for hashtag in custom_hashtags:
            formatted = self.format_hashtag(hashtag)
            if formatted and self.validate_hashtag(formatted):
                formatted_hashtags.append(formatted)
        
        return formatted_hashtags
    
    def _log_hashtag_metrics(self, post_id, status, hashtag_count, error_count, start_time, 
                           source_counts=None, validation_errors=0, fallback_used=False, 
                           final_hashtags=None, errors=None):
        """
        Log comprehensive hashtag generation metrics for monitoring and analysis.
        
        Args:
            post_id: Blog post ID
            status: Generation status (success, failed, disabled, etc.)
            hashtag_count: Number of hashtags generated
            error_count: Number of errors encountered
            start_time: Generation start time
            source_counts: Dictionary of hashtag counts by source
            validation_errors: Number of validation errors
            fallback_used: Whether fallback generation was used
            final_hashtags: List of final hashtags (for debug logging)
            errors: List of error messages
        """
        try:
            generation_time = time.time() - start_time
            
            # Create metrics entry
            metrics = {
                'post_id': post_id,
                'status': status,
                'hashtag_count': hashtag_count,
                'error_count': error_count,
                'generation_time_ms': round(generation_time * 1000, 2),
                'validation_errors': validation_errors,
                'fallback_used': fallback_used,
                'timestamp': time.time()
            }
            
            if source_counts:
                metrics['source_counts'] = source_counts
                metrics['total_generated'] = sum(source_counts.values())
            
            if final_hashtags:
                metrics['final_hashtags'] = final_hashtags
            
            if errors:
                metrics['errors'] = errors
            
            # Cache metrics for monitoring dashboard
            cache_key = f"linkedin_hashtag_metrics_{post_id}"
            cache.set(cache_key, metrics, timeout=86400)  # 24 hours
            
            # Update aggregate metrics
            self._update_hashtag_aggregate_metrics(status, hashtag_count, generation_time, error_count)
            
            # Log based on status with enhanced detail
            if status == 'success':
                if source_counts:
                    source_summary = ', '.join([f"{k}:{v}" for k, v in source_counts.items() if v > 0])
                    logger.info(f"Hashtag generation successful for post {post_id}: {hashtag_count} hashtags from sources ({source_summary}) in {generation_time:.3f}s")
                    # Debug log with more detail
                    if final_hashtags:
                        logger.debug(f"Generated hashtags for post {post_id}: {final_hashtags}")
                else:
                    logger.info(f"Hashtag generation successful for post {post_id}: {hashtag_count} hashtags in {generation_time:.3f}s")
                
                # Log performance metrics
                if generation_time > 1.0:
                    logger.warning(f"Slow hashtag generation for post {post_id}: {generation_time:.3f}s (threshold: 1.0s)")
                
                # Log validation issues if any
                if validation_errors > 0:
                    logger.debug(f"Hashtag validation filtered {validation_errors} invalid hashtags for post {post_id}")
                
                # Log fallback usage
                if fallback_used:
                    logger.info(f"Fallback hashtag generation used for post {post_id}")
                    
            elif status == 'failed':
                logger.warning(f"Hashtag generation failed for post {post_id}: {error_count} errors in {generation_time:.3f}s")
                if errors:
                    logger.debug(f"Hashtag generation errors for post {post_id}: {errors}")
                    
            elif status == 'critical_error':
                logger.error(f"Critical hashtag generation error for post {post_id} in {generation_time:.3f}s")
                if errors:
                    logger.error(f"Critical hashtag error details for post {post_id}: {errors[0]}")
                    
            elif status == 'disabled':
                logger.debug(f"Hashtag generation disabled for post {post_id}")
                
            # Log configuration issues if detected
            config_issues = self._detect_hashtag_config_issues()
            if config_issues:
                logger.warning(f"Hashtag configuration issues detected: {config_issues}")
            
        except Exception as e:
            logger.error(f"Error logging hashtag metrics for post {post_id}: {e}")
    
    def _detect_hashtag_config_issues(self):
        """
        Detect potential configuration issues with hashtag generation.
        
        Returns:
            list: List of configuration issues detected
        """
        issues = []
        
        try:
            # Check if config is valid
            if not isinstance(self.config, dict):
                issues.append("Invalid config format")
                return issues
            
            # Check max_hashtags setting
            max_hashtags = self.config.get('max_hashtags', self.DEFAULT_MAX_HASHTAGS)
            if not isinstance(max_hashtags, int) or max_hashtags < 0:
                issues.append(f"Invalid max_hashtags value: {max_hashtags}")
            elif max_hashtags > 30:
                issues.append(f"max_hashtags too high: {max_hashtags} (LinkedIn recommends ≤5)")
            elif max_hashtags == 0:
                issues.append("max_hashtags set to 0 - no hashtags will be generated")
            
            # Check custom rules format
            custom_rules = self.config.get('custom_hashtag_rules', {})
            if custom_rules and not isinstance(custom_rules, dict):
                issues.append("custom_hashtag_rules is not a valid dictionary")
            
            # Check blacklist format
            blacklist = self.config.get('hashtag_blacklist', [])
            if blacklist and not isinstance(blacklist, list):
                issues.append("hashtag_blacklist is not a valid list")
            elif isinstance(blacklist, list) and len(blacklist) > 100:
                issues.append(f"hashtag_blacklist very large: {len(blacklist)} items")
            
        except Exception as e:
            issues.append(f"Error checking config: {e}")
        
        return issues
    
    def _update_hashtag_aggregate_metrics(self, status, hashtag_count, generation_time, error_count):
        """
        Update aggregate hashtag generation metrics for monitoring with comprehensive tracking.
        
        Args:
            status: Generation status
            hashtag_count: Number of hashtags generated
            generation_time: Time taken for generation
            error_count: Number of errors
        """
        try:
            cache_key = "linkedin_hashtag_aggregate_metrics"
            current_metrics = cache.get(cache_key, {
                'total_attempts': 0,
                'successful_attempts': 0,
                'failed_attempts': 0,
                'disabled_attempts': 0,
                'total_hashtags_generated': 0,
                'total_errors': 0,
                'avg_generation_time': 0,
                'avg_hashtags_per_post': 0,
                'performance_stats': {
                    'slow_generations': 0,  # > 1 second
                    'very_slow_generations': 0,  # > 2 seconds
                    'fast_generations': 0,  # < 0.1 seconds
                },
                'status_breakdown': {},
                'last_updated': time.time(),
                'last_reset': time.time()
            })
            
            current_metrics['total_attempts'] += 1
            current_metrics['total_errors'] += error_count
            current_metrics['last_updated'] = time.time()
            
            # Track status breakdown
            current_metrics['status_breakdown'][status] = current_metrics['status_breakdown'].get(status, 0) + 1
            
            # Update status-specific counters
            if status == 'success':
                current_metrics['successful_attempts'] += 1
                current_metrics['total_hashtags_generated'] += hashtag_count
            elif status in ['failed', 'critical_error']:
                current_metrics['failed_attempts'] += 1
            elif status == 'disabled':
                current_metrics['disabled_attempts'] += 1
            
            # Track performance metrics
            if generation_time > 2.0:
                current_metrics['performance_stats']['very_slow_generations'] += 1
            elif generation_time > 1.0:
                current_metrics['performance_stats']['slow_generations'] += 1
            elif generation_time < 0.1:
                current_metrics['performance_stats']['fast_generations'] += 1
            
            # Update averages
            if current_metrics['total_attempts'] > 0:
                # Update average generation time
                current_avg = current_metrics['avg_generation_time']
                new_avg = ((current_avg * (current_metrics['total_attempts'] - 1)) + generation_time) / current_metrics['total_attempts']
                current_metrics['avg_generation_time'] = round(new_avg, 3)
                
                # Update average hashtags per successful post
                if current_metrics['successful_attempts'] > 0:
                    current_metrics['avg_hashtags_per_post'] = round(
                        current_metrics['total_hashtags_generated'] / current_metrics['successful_attempts'], 2
                    )
            
            cache.set(cache_key, current_metrics, timeout=86400)  # 24 hours
            
            # Log periodic statistics
            if current_metrics['total_attempts'] % 25 == 0:  # Every 25 attempts
                success_rate = (current_metrics['successful_attempts'] / current_metrics['total_attempts']) * 100
                error_rate = (current_metrics['total_errors'] / current_metrics['total_attempts']) * 100
                
                logger.info(f"Hashtag generation stats: {current_metrics['total_attempts']} attempts, "
                          f"{success_rate:.1f}% success rate, {error_rate:.1f}% error rate, "
                          f"avg {current_metrics['avg_generation_time']:.3f}s generation time, "
                          f"avg {current_metrics['avg_hashtags_per_post']} hashtags/post")
                
                # Log performance warnings
                slow_percentage = (current_metrics['performance_stats']['slow_generations'] / current_metrics['total_attempts']) * 100
                if slow_percentage > 20:  # More than 20% slow
                    logger.warning(f"High percentage of slow hashtag generations: {slow_percentage:.1f}% > 1s")
            
        except Exception as e:
            logger.error(f"Error updating hashtag aggregate metrics: {e}")
    
    def get_hashtag_metrics_summary(self):
        """
        Get a comprehensive summary of hashtag generation metrics for monitoring.
        
        Returns:
            dict: Hashtag metrics summary
        """
        try:
            cache_key = "linkedin_hashtag_aggregate_metrics"
            metrics = cache.get(cache_key, {})
            
            if not metrics:
                return {'status': 'no_data', 'message': 'No hashtag metrics available'}
            
            total_attempts = metrics.get('total_attempts', 0)
            if total_attempts == 0:
                return {'status': 'no_attempts', 'message': 'No hashtag generation attempts recorded'}
            
            successful_attempts = metrics.get('successful_attempts', 0)
            failed_attempts = metrics.get('failed_attempts', 0)
            disabled_attempts = metrics.get('disabled_attempts', 0)
            
            success_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            failure_rate = (failed_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            
            performance_stats = metrics.get('performance_stats', {})
            slow_percentage = (performance_stats.get('slow_generations', 0) / total_attempts) * 100 if total_attempts > 0 else 0
            
            summary = {
                'status': 'active',
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'failed_attempts': failed_attempts,
                'disabled_attempts': disabled_attempts,
                'success_rate_percent': round(success_rate, 1),
                'failure_rate_percent': round(failure_rate, 1),
                'total_hashtags_generated': metrics.get('total_hashtags_generated', 0),
                'avg_hashtags_per_post': metrics.get('avg_hashtags_per_post', 0),
                'avg_generation_time_seconds': metrics.get('avg_generation_time', 0),
                'performance_metrics': {
                    'slow_generations_percent': round(slow_percentage, 1),
                    'very_slow_generations': performance_stats.get('very_slow_generations', 0),
                    'fast_generations': performance_stats.get('fast_generations', 0)
                },
                'status_breakdown': metrics.get('status_breakdown', {}),
                'last_updated': metrics.get('last_updated'),
                'health_status': self._assess_hashtag_health(metrics)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting hashtag metrics summary: {e}")
            return {'status': 'error', 'message': f'Error retrieving metrics: {e}'}
    
    def _assess_hashtag_health(self, metrics):
        """
        Assess the health of hashtag generation based on metrics.
        
        Args:
            metrics: Hashtag metrics dictionary
            
        Returns:
            str: Health status (healthy, warning, critical)
        """
        try:
            total_attempts = metrics.get('total_attempts', 0)
            if total_attempts < 5:
                return 'insufficient_data'
            
            successful_attempts = metrics.get('successful_attempts', 0)
            failed_attempts = metrics.get('failed_attempts', 0)
            
            success_rate = (successful_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            failure_rate = (failed_attempts / total_attempts) * 100 if total_attempts > 0 else 0
            
            performance_stats = metrics.get('performance_stats', {})
            slow_percentage = (performance_stats.get('slow_generations', 0) / total_attempts) * 100 if total_attempts > 0 else 0
            
            # Assess health based on multiple factors
            if failure_rate > 50:
                return 'critical'
            elif failure_rate > 25 or slow_percentage > 40:
                return 'warning'
            elif success_rate > 80 and slow_percentage < 20:
                return 'healthy'
            else:
                return 'warning'
                
        except Exception as e:
            logger.error(f"Error assessing hashtag health: {e}")
            return 'unknown'
    
    def apply_custom_rules(self, hashtags, category_rules):
        """
        Apply custom hashtag rules to a list of hashtags.
        
        Args:
            hashtags: List of hashtags to process
            category_rules: Dictionary of category-specific rules
            
        Returns:
            List of hashtags with custom rules applied
        """
        if not category_rules or not isinstance(category_rules, dict):
            return hashtags
        
        processed_hashtags = []
        
        for hashtag in hashtags:
            # Apply any transformation rules
            processed_hashtag = hashtag
            
            # Check for replacement rules
            for category, rules in category_rules.items():
                if isinstance(rules, dict) and 'replacements' in rules:
                    replacements = rules['replacements']
                    if isinstance(replacements, dict):
                        hashtag_clean = hashtag.lstrip('#').lower()
                        if hashtag_clean in replacements:
                            processed_hashtag = self.format_hashtag(replacements[hashtag_clean])
                            break
            
            if processed_hashtag and self.validate_hashtag(processed_hashtag):
                processed_hashtags.append(processed_hashtag)
        
        return processed_hashtags
    
    def filter_blacklisted_hashtags(self, hashtags):
        """
        Remove blacklisted terms from hashtags with error handling.
        
        Args:
            hashtags: List of hashtags to filter
            
        Returns:
            List of hashtags with blacklisted terms removed
        """
        try:
            # Validate input
            if not hashtags or not isinstance(hashtags, list):
                logger.warning(f"Invalid hashtags input for blacklist filtering: {type(hashtags)}")
                return []
            
            # Get blacklist with error handling
            try:
                blacklist = self.config.get('hashtag_blacklist', [])
                if not isinstance(blacklist, list):
                    logger.warning(f"Invalid blacklist format: {type(blacklist)}, using empty list")
                    blacklist = []
            except Exception as e:
                logger.warning(f"Error accessing hashtag blacklist: {e}")
                blacklist = []
            
            # If no blacklist, return original hashtags
            if not blacklist:
                logger.debug("No blacklist configured, returning all hashtags")
                return hashtags
            
            # Convert blacklist to lowercase for case-insensitive matching with error handling
            blacklist_lower = []
            for term in blacklist:
                try:
                    if isinstance(term, str) and term.strip():
                        blacklist_lower.append(term.lower().strip())
                except Exception as e:
                    logger.debug(f"Error processing blacklist term '{term}': {e}")
                    continue
            
            if not blacklist_lower:
                logger.debug("No valid blacklist terms found, returning all hashtags")
                return hashtags
            
            logger.debug(f"Applying blacklist filter with {len(blacklist_lower)} terms to {len(hashtags)} hashtags")
            
            # Filter hashtags with individual error handling
            filtered_hashtags = []
            filtered_count = 0
            
            for hashtag in hashtags:
                try:
                    if not hashtag or not isinstance(hashtag, str):
                        logger.debug(f"Skipping invalid hashtag: {hashtag}")
                        continue
                    
                    hashtag_clean = hashtag.lstrip('#').lower()
                    
                    # Check if hashtag contains any blacklisted terms
                    is_blacklisted = False
                    for blacklisted_term in blacklist_lower:
                        try:
                            if blacklisted_term in hashtag_clean:
                                is_blacklisted = True
                                logger.debug(f"Filtered out blacklisted hashtag: {hashtag} (contains '{blacklisted_term}')")
                                filtered_count += 1
                                break
                        except Exception as e:
                            logger.debug(f"Error checking blacklist term '{blacklisted_term}' against hashtag '{hashtag}': {e}")
                            continue
                    
                    if not is_blacklisted:
                        filtered_hashtags.append(hashtag)
                        
                except Exception as e:
                    logger.warning(f"Error processing hashtag '{hashtag}' for blacklist filtering: {e}")
                    continue
            
            logger.debug(f"Blacklist filtering complete: {len(hashtags)} -> {len(filtered_hashtags)} hashtags ({filtered_count} filtered)")
            return filtered_hashtags
            
        except Exception as e:
            logger.error(f"Critical error in blacklist filtering: {e}")
            # Return original hashtags as fallback
            return hashtags if isinstance(hashtags, list) else []
    
    def validate_hashtag(self, hashtag):
        """
        Validate if a hashtag meets LinkedIn requirements.
        
        Args:
            hashtag: Hashtag to validate (with or without #)
            
        Returns:
            bool: True if hashtag is valid, False otherwise
        """
        if not hashtag or not isinstance(hashtag, str):
            return False
        
        # Remove # for validation
        clean_hashtag = hashtag.lstrip('#')
        
        # Check length
        if len(clean_hashtag) < self.MIN_HASHTAG_LENGTH or len(clean_hashtag) > self.MAX_HASHTAG_LENGTH:
            return False
        
        # Check for valid characters (alphanumeric and some special chars)
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_hashtag):
            return False
        
        # Must not be all numbers
        if clean_hashtag.isdigit():
            return False
        
        # Must start with a letter
        if not clean_hashtag[0].isalpha():
            return False
        
        return True
    
    def format_hashtag(self, tag_name):
        """
        Format a tag name as a LinkedIn hashtag.
        
        Args:
            tag_name: Original tag name or text
            
        Returns:
            Formatted hashtag with # prefix, or empty string if invalid
        """
        if not tag_name or not isinstance(tag_name, str):
            return ""
        
        # If already formatted as hashtag, clean and reformat
        if tag_name.startswith('#'):
            tag_name = tag_name[1:]
        
        # Remove special characters and extra spaces
        clean_tag = re.sub(r'[^a-zA-Z0-9\s]', '', tag_name.strip())
        
        if not clean_tag:
            return ""
        
        # Convert to camelCase for multi-word tags
        words = clean_tag.split()
        if not words:
            return ""
        
        # First word lowercase, subsequent words capitalized
        formatted_words = [words[0].lower()]
        for word in words[1:]:
            if word:
                formatted_words.append(word.capitalize())
        
        hashtag = ''.join(formatted_words)
        
        # Final validation
        if self.validate_hashtag(hashtag):
            return f"#{hashtag}"
        
        return ""
    
    def prioritize_hashtags(self, hashtags, priority_rules=None):
        """
        Sort hashtags by priority based on rules.
        
        Args:
            hashtags: List of hashtags to prioritize
            priority_rules: Dictionary of priority rules (optional)
            
        Returns:
            List of hashtags sorted by priority
        """
        if not hashtags:
            return []
        
        if not priority_rules:
            # Default prioritization: shorter hashtags first, then alphabetical
            return sorted(hashtags, key=lambda x: (len(x), x.lower()))
        
        # Apply custom priority rules
        def get_priority(hashtag):
            hashtag_clean = hashtag.lstrip('#').lower()
            
            # Check for explicit priority in rules
            if isinstance(priority_rules, dict):
                if hashtag_clean in priority_rules:
                    return priority_rules[hashtag_clean]
                
                # Check for pattern-based priorities
                for pattern, priority in priority_rules.items():
                    if pattern in hashtag_clean:
                        return priority
            
            # Default priority
            return 100
        
        return sorted(hashtags, key=lambda x: (get_priority(x), len(x), x.lower()))


class LinkedInContentFormatter:
    """
    Utility class for formatting blog post content for LinkedIn.
    
    Handles:
    - Character limit enforcement with intelligent truncation
    - Hashtag generation from blog post tags
    - Featured image URL extraction
    - Content formatting for LinkedIn posts
    """
    
    # LinkedIn content limits
    MAX_POST_LENGTH = 3000
    MAX_TITLE_LENGTH = 200
    MAX_EXCERPT_LENGTH = 300
    MAX_HASHTAGS = 5
    
    # Content formatting templates
    POST_TEMPLATE = "{title}\n\n{content}\n\n{url}{hashtags}"
    SIMPLE_TEMPLATE = "{title}\n\n{url}{hashtags}"
    
    def __init__(self, base_url: str = None):
        """
        Initialize the content formatter.
        
        Args:
            base_url: Base URL for the website (used for image URLs)
        """
        self.base_url = base_url or self._get_base_url()
    
    def _get_base_url(self) -> str:
        """Get the base URL from Django settings or sites framework."""
        try:
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            return f"https://{current_site.domain}"
        except ImportError:
            # Fallback if sites framework is not installed
            from django.conf import settings
            domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0]
            if domain == '*':
                domain = 'localhost'
            return f"https://{domain}"
        except Exception:
            return "https://localhost"
    
    def format_post_with_config(self, blog_post, config, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
        """
        Format a blog post for LinkedIn posting with configuration-aware formatting and comprehensive error handling.
        
        This method provides explicit configuration-aware formatting, implementing
        image posting decision logic based on the provided LinkedInConfig settings.
        
        Args:
            blog_post: Blog Post model instance
            config: LinkedInConfig instance with hashtag and image posting settings
            include_excerpt: Whether to include the excerpt in the post
            optimize_for_images: Whether to optimize content length for image posts
            
        Returns:
            Formatted LinkedIn post content
        """
        try:
            # Validate inputs
            if not blog_post:
                logger.error("Blog post is None in format_post_with_config")
                return ""
            
            post_id = getattr(blog_post, 'id', 'unknown')
            
            # Handle missing configuration with fallback
            if not config:
                logger.warning(f"No configuration provided for post {post_id}, using default formatting")
                try:
                    return self.format_post_content(blog_post, include_excerpt, optimize_for_images)
                except Exception as e:
                    logger.error(f"Fallback formatting failed for post {post_id}: {e}")
                    return self._create_emergency_fallback_content(blog_post)
            
            logger.debug(f"Formatting post {post_id} with explicit configuration: "
                        f"hashtags={getattr(config, 'enable_hashtags', 'unknown')}, "
                        f"images={getattr(config, 'enable_image_posting', 'unknown')}, "
                        f"strategy={getattr(config, 'image_posting_strategy', 'unknown')}")
            
            # Get the blog post URL with error handling
            try:
                post_url = self._get_post_url(blog_post)
            except Exception as e:
                logger.error(f"Error getting post URL for post {post_id}: {e}")
                post_url = "https://localhost/"  # Fallback URL
            
            # Format title with length limit and error handling
            try:
                title = self._format_title(getattr(blog_post, 'title', 'Untitled Post'))
            except Exception as e:
                logger.error(f"Error formatting title for post {post_id}: {e}")
                title = "Blog Post"  # Fallback title
            
            # Implement image posting decision logic based on configuration
            should_include_images = False
            try:
                should_include_images = self._should_include_images_for_post(blog_post, config, optimize_for_images)
            except Exception as e:
                logger.warning(f"Error determining image posting strategy for post {post_id}: {e}")
                should_include_images = False  # Fallback to text-only
            
            # Check if we have images available for this post (only if we should include them)
            has_images = False
            available_images_count = 0
            if should_include_images:
                try:
                    available_images = self.get_post_images(blog_post)
                    available_images_count = len(available_images)
                    has_images = available_images_count > 0
                    logger.debug(f"Post {post_id} has {available_images_count} images available")
                except Exception as e:
                    logger.warning(f"Could not check images for post {post_id}: {e}")
                    has_images = False
                    should_include_images = False  # Fallback to text-only if image check fails
            else:
                logger.debug(f"Image posting disabled by configuration for post {post_id} "
                            f"(strategy: {getattr(config, 'image_posting_strategy', 'unknown')})")
            
            # Format content/excerpt with image considerations and error handling
            content = ""
            try:
                if include_excerpt and hasattr(blog_post, 'excerpt') and blog_post.excerpt:
                    content = self._format_excerpt(blog_post.excerpt)
                elif include_excerpt and hasattr(blog_post, 'content') and blog_post.content:
                    # Extract excerpt from content if no explicit excerpt
                    content = self._extract_excerpt_from_content(blog_post.content)
            except Exception as e:
                logger.warning(f"Error formatting content/excerpt for post {post_id}: {e}")
                content = ""  # Continue with title-only post
            
            # If we have images and should include them, optimize text content for visual balance
            if has_images and content and optimize_for_images and should_include_images:
                try:
                    # Reduce excerpt length slightly for image posts to balance visual elements
                    image_optimized_length = int(self.MAX_EXCERPT_LENGTH * 0.85)  # 15% shorter
                    if len(content) > image_optimized_length:
                        truncator = Truncator(content)
                        content = truncator.chars(image_optimized_length - 3, truncate='...')
                        logger.debug(f"Shortened excerpt for image post {post_id} "
                                   f"(from {len(getattr(blog_post, 'excerpt', '') or '')} to {len(content)} chars)")
                except Exception as e:
                    logger.warning(f"Error optimizing content for images for post {post_id}: {e}")
                    # Continue with original content
            
            # Generate hashtags using configuration with error handling
            hashtags = ""
            hashtag_string = ""
            try:
                hashtags = self._generate_hashtags(blog_post, config)
                hashtag_string = f"\n\n{hashtags}" if hashtags else ""
            except Exception as e:
                logger.warning(f"Error generating hashtags for post {post_id}: {e}")
                hashtags = ""
                hashtag_string = ""
            
            # Choose template based on content availability and format post
            try:
                if content:
                    formatted_post = self.POST_TEMPLATE.format(
                        title=title,
                        content=content,
                        url=post_url,
                        hashtags=hashtag_string
                    )
                else:
                    formatted_post = self.SIMPLE_TEMPLATE.format(
                        title=title,
                        url=post_url,
                        hashtags=hashtag_string
                    )
            except Exception as e:
                logger.error(f"Error formatting post template for post {post_id}: {e}")
                # Emergency fallback formatting
                formatted_post = f"{title}\n\n{post_url}"
            
            # Apply character limit with intelligent truncation
            try:
                final_content = self._apply_character_limit(formatted_post, post_url, hashtag_string)
            except Exception as e:
                logger.error(f"Error applying character limit for post {post_id}: {e}")
                # Fallback to simple truncation
                final_content = formatted_post[:self.MAX_POST_LENGTH]
            
            # Log comprehensive formatting result
            try:
                posting_type = "image post" if (should_include_images and has_images) else "text-only post"
                hashtag_count = len(hashtags.split()) if hashtags else 0
                logger.info(f"Formatted post {post_id} for LinkedIn as {posting_type}: "
                           f"{len(final_content)} characters, {hashtag_count} hashtags")
                
                if should_include_images and not has_images:
                    logger.warning(f"Post {post_id} configured for images but no images available - posting as text-only")
            except Exception as e:
                logger.debug(f"Error logging formatting result for post {post_id}: {e}")
            
            return final_content
            
        except Exception as e:
            logger.error(f"Critical error in format_post_with_config for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            # Emergency fallback
            return self._create_emergency_fallback_content(blog_post)
    
    def _create_emergency_fallback_content(self, blog_post):
        """
        Create emergency fallback content when all other formatting fails.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Basic formatted content string
        """
        try:
            title = getattr(blog_post, 'title', 'Blog Post')
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Try to get a basic URL
            try:
                post_url = self._get_post_url(blog_post)
            except:
                post_url = "https://localhost/"
            
            return f"{title}\n\n{post_url}"
            
        except Exception as e:
            logger.critical(f"Emergency fallback content creation failed: {e}")
            return "New blog post available"
    
    def _should_include_images_for_post(self, blog_post, config, optimize_for_images):
        """
        Implement image posting decision logic based on configuration with comprehensive logging.
        
        Args:
            blog_post: Blog Post model instance
            config: LinkedInConfig instance
            optimize_for_images: Whether image optimization is enabled
            
        Returns:
            bool: True if images should be included for this post
        """
        start_time = time.time()
        post_id = getattr(blog_post, 'id', 'unknown')
        post_title = getattr(blog_post, 'title', 'Unknown Title')
        
        try:
            # Log the decision process start
            logger.debug(f"Starting image posting decision for post {post_id} ('{post_title}')")
            
            # Check basic prerequisites
            if not config:
                decision_time = time.time() - start_time
                logger.warning(f"No LinkedIn config provided for image posting decision on post {post_id}")
                self._log_image_posting_metrics(post_id, 'no_config', False, decision_time, 'config_missing')
                return False
            
            if not optimize_for_images:
                decision_time = time.time() - start_time
                logger.info(f"Image optimization disabled for post {post_id} - posting as text-only")
                self._log_image_posting_metrics(post_id, 'optimization_disabled', False, decision_time, 'parameter_setting')
                return False
            
            # Check global image posting setting
            if not config.enable_image_posting:
                decision_time = time.time() - start_time
                logger.info(f"Image posting globally disabled for post {post_id} ('{post_title}')")
                self._log_image_posting_metrics(post_id, 'globally_disabled', False, decision_time, 'global_setting')
                return False
            
            # Apply strategy-based logic
            strategy = getattr(config, 'image_posting_strategy', 'always')
            logger.debug(f"Applying image posting strategy '{strategy}' for post {post_id}")
            
            if strategy == 'never':
                decision_time = time.time() - start_time
                logger.info(f"Image posting strategy 'never' for post {post_id} ('{post_title}') - posting as text-only")
                self._log_image_posting_metrics(post_id, 'strategy_never', False, decision_time, 'strategy_setting')
                
                # Log feature usage
                linkedin_metrics_logger.log_feature_usage(
                    'image_posting_decision', 
                    str(post_id), 
                    True, 
                    decision_time,
                    {'decision_type': 'strategy_never', 'include_images': False, 'strategy': strategy}
                )
                
                return False
                
            elif strategy == 'always':
                decision_time = time.time() - start_time
                logger.info(f"Image posting strategy 'always' for post {post_id} ('{post_title}') - including images")
                self._log_image_posting_metrics(post_id, 'strategy_always', True, decision_time, 'strategy_setting')
                
                # Log feature usage
                linkedin_metrics_logger.log_feature_usage(
                    'image_posting_decision', 
                    str(post_id), 
                    True, 
                    decision_time,
                    {'decision_type': 'strategy_always', 'include_images': True, 'strategy': strategy}
                )
                
                return True
                
            elif strategy == 'category_based':
                logger.debug(f"Using category-based image posting logic for post {post_id}")
                result = self._should_include_images_category_based(blog_post, config)
                decision_time = time.time() - start_time
                
                logger.info(f"Category-based image posting decision for post {post_id} ('{post_title}'): {result}")
                self._log_image_posting_metrics(post_id, 'category_based_success', result, decision_time, 'category_rules')
                return result
                
            else:
                # Unknown strategy, default to enabled with warning
                decision_time = time.time() - start_time
                logger.warning(f"Unknown image posting strategy '{strategy}' for post {post_id} ('{post_title}'), defaulting to enabled")
                self._log_image_posting_metrics(post_id, 'unknown_strategy', True, decision_time, 'fallback', 
                                              error=f"Unknown strategy: {strategy}")
                return True
                
        except Exception as e:
            decision_time = time.time() - start_time
            logger.error(f"Error in image posting decision for post {post_id}: {e}")
            self._log_image_posting_metrics(post_id, 'decision_error', True, decision_time, 'fallback', error=str(e))
            # Safe fallback - default to image posting enabled
            return True
    
    def _should_include_images_category_based(self, blog_post, config):
        """
        Implement category-based image posting logic with comprehensive logging.
        
        Args:
            blog_post: Blog Post model instance
            config: LinkedInConfig instance
            
        Returns:
            bool: True if images should be included based on category rules
        """
        post_id = getattr(blog_post, 'id', 'unknown')
        
        try:
            # Check if post has categories
            if not hasattr(blog_post, 'categories'):
                logger.debug(f"Post {post_id} has no categories attribute, defaulting to image posting enabled")
                return True
            
            try:
                if not blog_post.categories.exists():
                    logger.debug(f"Post {post_id} has no categories, defaulting to image posting enabled")
                    return True
            except Exception as e:
                logger.warning(f"Error checking categories for post {post_id}: {e}, defaulting to enabled")
                return True
            
            # Get category-specific rules
            try:
                # Check both custom hashtag rules and category image overrides
                custom_rules = getattr(config, 'custom_hashtag_rules', {}) or {}
                category_overrides = getattr(config, 'category_image_overrides', {}) or {}
                
                logger.debug(f"Checking category-based image rules for post {post_id}")
                
                # Get post categories
                categories = list(blog_post.categories.all())
                category_names = [getattr(cat, 'name', 'Unknown') for cat in categories]
                logger.debug(f"Post {post_id} categories: {category_names}")
                
                # Check each category for image posting preferences
                for category in categories:
                    try:
                        category_key = getattr(category, 'slug', None) or getattr(category, 'name', '').lower()
                        
                        # First check category_image_overrides (more specific)
                        if category_key in category_overrides:
                            override_value = category_overrides[category_key]
                            
                            if isinstance(override_value, bool):
                                logger.info(f"Category '{category_key}' has explicit image override: {override_value} for post {post_id}")
                                return override_value
                            elif isinstance(override_value, dict):
                                enable_images = override_value.get('enable_images', True)
                                logger.info(f"Category '{category_key}' has dict image override: {enable_images} for post {post_id}")
                                return enable_images
                            else:
                                logger.warning(f"Invalid category image override format for '{category_key}': {type(override_value)}")
                        
                        # Then check custom hashtag rules for image settings
                        if category_key in custom_rules:
                            rules = custom_rules[category_key]
                            
                            # Check for image posting preference in category rules
                            if isinstance(rules, dict) and 'enable_images' in rules:
                                enable_images = rules['enable_images']
                                logger.info(f"Category '{category_key}' has image setting in custom rules: {enable_images} for post {post_id}")
                                return bool(enable_images)
                                
                    except Exception as e:
                        logger.warning(f"Error processing category rules for post {post_id}, category {category}: {e}")
                        continue
                
                # If no specific category rules found, default to enabled
                logger.debug(f"No specific image posting rules found for categories of post {post_id}, defaulting to enabled")
                return True
                
            except Exception as e:
                logger.error(f"Error accessing category rules for post {post_id}: {e}")
                return True
                
        except Exception as e:
            logger.error(f"Critical error in category-based image decision for post {post_id}: {e}")
            return True  # Safe fallback

    def format_post_content(self, blog_post, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
        """
        Format a blog post for LinkedIn posting with image considerations and configuration awareness.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include the excerpt in the post
            optimize_for_images: Whether to optimize content length for image posts
            
        Returns:
            Formatted LinkedIn post content
        """
        # Try to get active LinkedIn configuration for image posting decisions
        config = None
        try:
            from ..linkedin_models import LinkedInConfig
            config = LinkedInConfig.get_active_config()
            if config:
                logger.debug(f"Using active LinkedIn config for content formatting for post {blog_post.id}")
        except ImportError:
            logger.debug("LinkedInConfig not available, using default settings")
        
        # Get the blog post URL
        post_url = self._get_post_url(blog_post)
        
        # Format title with length limit
        title = self._format_title(blog_post.title)
        
        # Check if we should include images based on configuration
        should_include_images = True  # Default behavior
        if config and optimize_for_images:
            should_include_images = config.should_include_images(blog_post)
            logger.debug(f"Image posting decision for post {blog_post.id}: {should_include_images} "
                        f"(strategy: {config.image_posting_strategy})")
        
        # Check if we have images available for this post (only if we should include them)
        has_images = False
        if should_include_images and optimize_for_images:
            try:
                available_images = self.get_post_images(blog_post)
                has_images = len(available_images) > 0
                logger.debug(f"Post {blog_post.id} has {len(available_images)} images available")
            except Exception as e:
                logger.warning(f"Could not check images for post {blog_post.id}: {e}")
        elif not should_include_images:
            logger.debug(f"Image posting disabled by configuration for post {blog_post.id}")
        
        # Format content/excerpt with image considerations
        content = ""
        if include_excerpt and blog_post.excerpt:
            content = self._format_excerpt(blog_post.excerpt)
        elif include_excerpt and not blog_post.excerpt:
            # Extract excerpt from content if no explicit excerpt
            content = self._extract_excerpt_from_content(blog_post.content)
        
        # If we have images and should include them, we might want to shorten text content slightly
        # to leave more visual focus on the image
        if has_images and content and optimize_for_images and should_include_images:
            # Reduce excerpt length slightly for image posts to balance visual elements
            image_optimized_length = int(self.MAX_EXCERPT_LENGTH * 0.85)  # 15% shorter
            if len(content) > image_optimized_length:
                truncator = Truncator(content)
                content = truncator.chars(image_optimized_length - 3, truncate='...')
                logger.debug(f"Shortened excerpt for image post {blog_post.id}")
        
        # Generate hashtags using configuration
        hashtags = self._generate_hashtags(blog_post, config)
        hashtag_string = f"\n\n{hashtags}" if hashtags else ""
        
        # Choose template based on content availability
        if content:
            formatted_post = self.POST_TEMPLATE.format(
                title=title,
                content=content,
                url=post_url,
                hashtags=hashtag_string
            )
        else:
            formatted_post = self.SIMPLE_TEMPLATE.format(
                title=title,
                url=post_url,
                hashtags=hashtag_string
            )
        
        # Apply character limit with intelligent truncation
        final_content = self._apply_character_limit(formatted_post, post_url, hashtag_string)
        
        # Log formatting result with configuration context
        if should_include_images and has_images:
            logger.debug(f"Formatted post {blog_post.id} for LinkedIn with image optimization: "
                        f"{len(final_content)} characters")
        elif not should_include_images:
            logger.debug(f"Formatted post {blog_post.id} for LinkedIn as text-only (per configuration): "
                        f"{len(final_content)} characters")
        else:
            logger.debug(f"Formatted post {blog_post.id} for LinkedIn as text-only (no images available): "
                        f"{len(final_content)} characters")
        
        return final_content
    
    def _format_title(self, title: str) -> str:
        """
        Format and truncate title for LinkedIn.
        
        Args:
            title: Original blog post title
            
        Returns:
            Formatted title
        """
        if not title:
            return ""
        
        # Clean up title
        clean_title = title.strip()
        
        # Apply length limit with intelligent truncation
        if len(clean_title) > self.MAX_TITLE_LENGTH:
            truncator = Truncator(clean_title)
            clean_title = truncator.chars(self.MAX_TITLE_LENGTH - 3, truncate='...')
        
        return clean_title
    
    def _format_excerpt(self, excerpt: str) -> str:
        """
        Format and truncate excerpt for LinkedIn.
        
        Args:
            excerpt: Blog post excerpt
            
        Returns:
            Formatted excerpt
        """
        if not excerpt:
            return ""
        
        # Strip HTML tags and clean up
        clean_excerpt = strip_tags(excerpt).strip()
        
        # Remove extra whitespace
        clean_excerpt = re.sub(r'\s+', ' ', clean_excerpt)
        
        # Apply length limit
        if len(clean_excerpt) > self.MAX_EXCERPT_LENGTH:
            truncator = Truncator(clean_excerpt)
            clean_excerpt = truncator.chars(self.MAX_EXCERPT_LENGTH - 3, truncate='...')
        
        return clean_excerpt
    
    def _extract_excerpt_from_content(self, content: str) -> str:
        """
        Extract an excerpt from blog post content.
        
        Args:
            content: Full blog post content
            
        Returns:
            Extracted excerpt
        """
        if not content:
            return ""
        
        # Strip HTML tags
        clean_content = strip_tags(content).strip()
        
        # Remove extra whitespace
        clean_content = re.sub(r'\s+', ' ', clean_content)
        
        # Extract first paragraph or sentence
        paragraphs = clean_content.split('\n\n')
        first_paragraph = paragraphs[0] if paragraphs else clean_content
        
        # If first paragraph is too long, try to get first few sentences
        if len(first_paragraph) > self.MAX_EXCERPT_LENGTH:
            sentences = re.split(r'[.!?]+', first_paragraph)
            excerpt = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if adding this sentence would exceed limit
                test_excerpt = f"{excerpt} {sentence}".strip() if excerpt else sentence
                if len(test_excerpt) > self.MAX_EXCERPT_LENGTH - 3:
                    break
                
                excerpt = test_excerpt
            
            if not excerpt:  # Fallback if no complete sentences fit
                truncator = Truncator(first_paragraph)
                excerpt = truncator.chars(self.MAX_EXCERPT_LENGTH - 3, truncate='...')
        else:
            excerpt = first_paragraph
        
        return excerpt
    
    def _generate_hashtags(self, blog_post, config=None) -> str:
        """
        Generate hashtags from blog post using the HashtagGenerator with LinkedInConfig settings and comprehensive error handling.
        
        Args:
            blog_post: Blog Post model instance
            config: Optional LinkedInConfig instance or hashtag configuration dict
            
        Returns:
            Formatted hashtags string
        """
        try:
            # Validate blog_post input
            if not blog_post:
                logger.warning("Blog post is None in _generate_hashtags")
                return ""
            
            post_id = getattr(blog_post, 'id', 'unknown')
            logger.debug(f"Starting hashtag generation for post {post_id}")
            
            # If no config provided, try to get active LinkedIn configuration with error handling
            if config is None:
                try:
                    from ..linkedin_models import LinkedInConfig
                    config = LinkedInConfig.get_active_config()
                    if config:
                        logger.debug(f"Using active LinkedIn config for hashtag generation for post {post_id}")
                    else:
                        logger.debug(f"No active LinkedIn config found, using default hashtag settings for post {post_id}")
                except ImportError:
                    logger.warning("LinkedInConfig not available, using default hashtag settings")
                    config = None
                except Exception as e:
                    logger.warning(f"Error accessing LinkedInConfig: {e}")
                    config = None
            
            # Use HashtagGenerator for intelligent hashtag generation with error handling
            try:
                generator = HashtagGenerator(config)
                hashtags = generator.generate_hashtags(blog_post)
            except Exception as e:
                logger.error(f"Error with HashtagGenerator for post {post_id}: {e}")
                # Fallback to simple tag-based generation
                logger.info(f"Falling back to simple hashtag generation for post {post_id}")
                return self._generate_hashtags_fallback(blog_post)
            
            # Validate hashtags result
            if not hashtags:
                logger.debug(f"No hashtags generated for post {post_id}, trying fallback")
                return self._generate_hashtags_fallback(blog_post)
            
            if not isinstance(hashtags, list):
                logger.warning(f"Invalid hashtags format for post {post_id}: {type(hashtags)}")
                return self._generate_hashtags_fallback(blog_post)
            
            # Filter out invalid hashtags
            valid_hashtags = []
            for hashtag in hashtags:
                try:
                    if hashtag and isinstance(hashtag, str) and hashtag.strip():
                        valid_hashtags.append(hashtag.strip())
                except Exception as e:
                    logger.debug(f"Error processing hashtag '{hashtag}' for post {post_id}: {e}")
                    continue
            
            if not valid_hashtags:
                logger.debug(f"No valid hashtags after filtering for post {post_id}, trying fallback")
                return self._generate_hashtags_fallback(blog_post)
            
            hashtag_count = len(valid_hashtags)
            logger.debug(f"Generated {hashtag_count} valid hashtags for post {post_id}: {valid_hashtags}")
            
            # Join hashtags with error handling
            try:
                hashtag_string = " ".join(valid_hashtags)
                return hashtag_string
            except Exception as e:
                logger.error(f"Error joining hashtags for post {post_id}: {e}")
                return self._generate_hashtags_fallback(blog_post)
            
        except Exception as e:
            logger.error(f"Critical error generating hashtags for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            # Ultimate fallback to simple tag-based generation
            try:
                return self._generate_hashtags_fallback(blog_post)
            except Exception as fallback_error:
                logger.error(f"Fallback hashtag generation also failed: {fallback_error}")
                return ""
    
    def _generate_hashtags_fallback(self, blog_post) -> str:
        """
        Fallback hashtag generation using simple tag-based approach with error handling.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Formatted hashtags string
        """
        try:
            # Validate blog_post input
            if not blog_post:
                logger.warning("Blog post is None in _generate_hashtags_fallback")
                return ""
            
            post_id = getattr(blog_post, 'id', 'unknown')
            logger.debug(f"Starting fallback hashtag generation for post {post_id}")
            
            # Check if post has tags attribute and tags exist
            if not hasattr(blog_post, 'tags'):
                logger.debug(f"Post {post_id} has no tags attribute, trying title-based fallback")
                return self._generate_title_based_hashtags(blog_post)
            
            try:
                if not blog_post.tags.exists():
                    logger.debug(f"Post {post_id} has no tags, trying title-based fallback")
                    return self._generate_title_based_hashtags(blog_post)
            except Exception as e:
                logger.warning(f"Error checking tags existence for post {post_id}: {e}")
                return self._generate_title_based_hashtags(blog_post)
            
            # Get tag names and format as hashtags with error handling
            try:
                tag_names = list(blog_post.tags.values_list('name', flat=True)[:self.MAX_HASHTAGS])
                logger.debug(f"Retrieved {len(tag_names)} tag names for fallback hashtag generation for post {post_id}")
            except Exception as e:
                logger.error(f"Error retrieving tag names for post {post_id}: {e}")
                return self._generate_title_based_hashtags(blog_post)
            
            if not tag_names:
                logger.debug(f"No tag names found for post {post_id}, trying title-based fallback")
                return self._generate_title_based_hashtags(blog_post)
            
            hashtags = []
            for tag_name in tag_names:
                try:
                    if not tag_name or not isinstance(tag_name, str):
                        logger.debug(f"Skipping invalid tag name: {tag_name}")
                        continue
                    
                    # Clean tag name for hashtag format
                    hashtag = self._format_hashtag(tag_name)
                    if hashtag:
                        hashtags.append(hashtag)
                        logger.debug(f"Added fallback hashtag: {hashtag}")
                except Exception as e:
                    logger.warning(f"Error processing tag '{tag_name}' for post {post_id}: {e}")
                    continue
            
            if not hashtags:
                logger.debug(f"No valid hashtags generated from tags for post {post_id}, trying title-based fallback")
                return self._generate_title_based_hashtags(blog_post)
            
            hashtag_string = " ".join(hashtags)
            logger.debug(f"Generated {len(hashtags)} fallback hashtags for post {post_id}: {hashtag_string}")
            return hashtag_string
            
        except Exception as e:
            logger.error(f"Critical error in fallback hashtag generation for post {getattr(blog_post, 'id', 'unknown')}: {e}")
            # Ultimate fallback
            try:
                return self._generate_title_based_hashtags(blog_post)
            except Exception as title_error:
                logger.error(f"Title-based hashtag fallback also failed: {title_error}")
                return ""
    
    def _generate_title_based_hashtags(self, blog_post) -> str:
        """
        Generate basic hashtags from post title as ultimate fallback.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Basic hashtags string
        """
        try:
            if not blog_post or not hasattr(blog_post, 'title') or not blog_post.title:
                logger.debug("No title available for title-based hashtag generation")
                return "#blog"  # Ultimate fallback
            
            title = str(blog_post.title)
            words = title.lower().split()[:2]  # Take first 2 words
            hashtags = []
            
            for word in words:
                if len(word) >= 3 and word.isalpha():
                    hashtag = f"#{word.capitalize()}"
                    hashtags.append(hashtag)
            
            # Add generic hashtag if we don't have any
            if not hashtags:
                hashtags = ["#blog"]
            
            hashtag_string = " ".join(hashtags)
            logger.debug(f"Generated title-based hashtags: {hashtag_string}")
            return hashtag_string
            
        except Exception as e:
            logger.error(f"Error in title-based hashtag generation: {e}")
            return "#blog"  # Ultimate fallback
    
    def _format_hashtag(self, tag_name: str) -> str:
        """
        Format a tag name as a LinkedIn hashtag.
        
        Args:
            tag_name: Original tag name
            
        Returns:
            Formatted hashtag or empty string if invalid
        """
        if not tag_name:
            return ""
        
        # Remove special characters and spaces, keep alphanumeric
        clean_tag = re.sub(r'[^a-zA-Z0-9\s]', '', tag_name)
        
        # Convert to camelCase for multi-word tags
        words = clean_tag.split()
        if not words:
            return ""
        
        # First word lowercase, subsequent words capitalized
        formatted_words = [words[0].lower()]
        for word in words[1:]:
            if word:
                formatted_words.append(word.capitalize())
        
        hashtag = ''.join(formatted_words)
        
        # Ensure hashtag is valid (at least 1 character, not just numbers)
        if len(hashtag) > 0 and not hashtag.isdigit():
            return f"#{hashtag}"
        
        return ""
    
    def _get_post_url(self, blog_post) -> str:
        """
        Get the full URL for a blog post.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Full URL to the blog post
        """
        try:
            # Try to get absolute URL from the model
            relative_url = blog_post.get_absolute_url()
            return urljoin(self.base_url, relative_url)
        except Exception as e:
            logger.warning(f"Could not get absolute URL for post {blog_post.id}: {e}")
            # Fallback URL construction
            return f"{self.base_url}/blog/{blog_post.slug}/"
    
    def _apply_character_limit(self, content: str, post_url: str, hashtags: str) -> str:
        """
        Apply LinkedIn character limit with intelligent truncation.
        
        Args:
            content: Full formatted content
            post_url: Blog post URL (must be preserved)
            hashtags: Hashtags string (lower priority)
            
        Returns:
            Truncated content that fits LinkedIn limits
        """
        if len(content) <= self.MAX_POST_LENGTH:
            return content
        
        # Calculate space needed for URL and hashtags
        hashtag_space = len(hashtags)
        
        # If even without hashtags we're over limit, remove hashtags
        if len(content) - hashtag_space > self.MAX_POST_LENGTH:
            content_without_hashtags = content.replace(hashtags, "").rstrip()
            
            # If still over limit, truncate content intelligently
            if len(content_without_hashtags) > self.MAX_POST_LENGTH:
                # Split content to preserve structure
                parts = content_without_hashtags.split('\n\n')
                if len(parts) >= 3:  # title, content, url
                    title = parts[0]
                    excerpt = parts[1]
                    url_part = parts[2]
                    
                    # Calculate space for title and URL (must be preserved)
                    title_and_url_space = len(title) + len(url_part) + 4  # + newlines
                    
                    if title_and_url_space < self.MAX_POST_LENGTH:
                        # Calculate remaining space for excerpt
                        excerpt_space = self.MAX_POST_LENGTH - title_and_url_space
                        
                        if excerpt_space > 10:  # Minimum meaningful excerpt length
                            truncator = Truncator(excerpt)
                            truncated_excerpt = truncator.chars(excerpt_space - 3, truncate='...')
                            final_content = f"{title}\n\n{truncated_excerpt}\n\n{url_part}"
                        else:
                            # Just title and URL
                            final_content = f"{title}\n\n{url_part}"
                    else:
                        # Even title and URL are too long, truncate everything
                        truncator = Truncator(content_without_hashtags)
                        final_content = truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
                else:
                    # Fallback: truncate entire content
                    truncator = Truncator(content_without_hashtags)
                    final_content = truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
                
                return final_content
            else:
                return content_without_hashtags
        else:
            # Remove some hashtags to fit
            truncator = Truncator(content)
            return truncator.chars(self.MAX_POST_LENGTH - 3, truncate='...')
    
    def get_post_images(self, blog_post) -> List[str]:
        """
        Extract multiple images from blog posts for LinkedIn posting.
        
        Returns all available images from the blog post in priority order,
        including featured image, social image, and media items.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            List of absolute URLs to available images
        """
        try:
            # Use the LinkedIn image service to get all fallback images
            return LinkedInImageService.get_fallback_images(blog_post)
        except Exception as e:
            logger.error(f"Error getting post images for {blog_post.id}: {e}")
            return []
    
    def select_best_image_for_linkedin(self, blog_post) -> Optional[str]:
        """
        Select the optimal image for LinkedIn posting from available images.
        
        This method uses the LinkedIn image service to find the best image
        that meets LinkedIn's requirements for dimensions, format, and file size.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            URL of the best LinkedIn-compatible image, or None if no suitable image found
        """
        try:
            # Use the LinkedIn image service to select the best compatible image
            return LinkedInImageService.select_best_compatible_image(blog_post)
        except Exception as e:
            logger.error(f"Error selecting best image for LinkedIn for post {blog_post.id}: {e}")
            return None
    
    def validate_image_compatibility(self, image_url: str) -> bool:
        """
        Validate if an image meets LinkedIn's requirements.
        
        Checks the image against LinkedIn's specifications for:
        - Supported formats (JPEG, PNG, GIF)
        - Dimension requirements (200x200 to 7680x4320 pixels)
        - File size limits (max 20MB)
        - Aspect ratio constraints
        
        Args:
            image_url: URL of the image to validate
            
        Returns:
            True if image is compatible with LinkedIn, False otherwise
        """
        try:
            is_valid, issues = LinkedInImageService.validate_image_for_linkedin(image_url)
            if not is_valid and issues:
                logger.debug(f"Image {image_url} validation issues: {issues}")
            return is_valid
        except Exception as e:
            logger.error(f"Error validating image compatibility for {image_url}: {e}")
            return False

    def get_featured_image_url(self, blog_post) -> Optional[str]:
        """
        Extract featured image URL for LinkedIn media.
        
        This method is maintained for backward compatibility but now uses
        the LinkedIn image service for consistent image selection logic.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Full URL to featured image or None
        """
        try:
            # Use the LinkedIn image service for consistent image selection
            return LinkedInImageService.get_post_image(blog_post)
        except Exception as e:
            logger.error(f"Error getting featured image URL for post {blog_post.id}: {e}")
            return None
    
    def get_image_info_for_linkedin(self, blog_post) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive image information for LinkedIn posting.
        
        This method provides all the image information needed for LinkedIn posting,
        including the best image, metadata, and compatibility information.
        
        Args:
            blog_post: Blog Post model instance
            
        Returns:
            Dictionary with comprehensive image information, or None if no suitable image
        """
        try:
            # Get comprehensive image information from the LinkedIn image service
            return LinkedInImageService.get_image_for_linkedin_post(blog_post, validate=True)
        except Exception as e:
            logger.error(f"Error getting image info for LinkedIn post {blog_post.id}: {e}")
            return None
    
    def format_post_with_image_info(self, blog_post, include_excerpt: bool = True) -> Dict[str, Any]:
        """
        Format a blog post for LinkedIn with comprehensive image information.
        
        This method combines content formatting with image analysis to provide
        everything needed for LinkedIn posting with images.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include excerpt in the post
            
        Returns:
            Dictionary with formatted content and image information
        """
        try:
            # Format the text content
            formatted_content = self.format_post_content(blog_post, include_excerpt, optimize_for_images=True)
            
            # Get image information
            image_info = self.get_image_info_for_linkedin(blog_post)
            
            # Validate content with image considerations
            validation_result = self.validate_content(formatted_content, blog_post, include_image_validation=True)
            
            # Prepare comprehensive result
            result = {
                # Content information
                'content': formatted_content,
                'character_count': len(formatted_content),
                'is_valid': validation_result[0],
                'validation_errors': validation_result[1],
                
                # Post metadata
                'post_id': blog_post.id,
                'post_title': blog_post.title,
                'post_url': self._get_post_url(blog_post),
                
                # Image information
                'has_image': image_info is not None,
                'image_info': image_info,
                
                # Posting strategy
                'posting_strategy': 'image_post' if image_info else 'text_only_post',
                'ready_for_posting': validation_result[0] and (image_info is not None or True)  # Text-only is also valid
            }
            
            # Add image-specific details if available
            if image_info:
                result.update({
                    'image_url': image_info.get('url'),
                    'image_compatible': image_info.get('linkedin_compatible', False),
                    'image_issues': image_info.get('compatibility_issues', []),
                    'fallback_images_count': image_info.get('fallback_images_available', 0)
                })
            
            logger.debug(f"Formatted post {blog_post.id} with image info: "
                        f"strategy={result['posting_strategy']}, "
                        f"has_image={result['has_image']}, "
                        f"ready={result['ready_for_posting']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting post with image info for {blog_post.id}: {e}")
            # Return basic fallback result
            return {
                'content': self.format_post_content(blog_post, include_excerpt),
                'has_image': False,
                'image_info': None,
                'posting_strategy': 'text_only_post',
                'ready_for_posting': False,
                'error': str(e)
            }
    
    def validate_content(self, content: str, blog_post=None, include_image_validation: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate formatted content for LinkedIn posting, including image considerations.
        
        Args:
            content: Formatted LinkedIn post content
            blog_post: Optional blog post instance for image validation
            include_image_validation: Whether to validate associated images
            
        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # Check length
        if len(content) > self.MAX_POST_LENGTH:
            errors.append(f"Content exceeds LinkedIn limit of {self.MAX_POST_LENGTH} characters")
        
        # Check if content is empty
        if not content.strip():
            errors.append("Content cannot be empty")
        
        # Check for required URL
        if "http" not in content:
            errors.append("Content should include a URL to the blog post")
        
        # Check for excessive hashtags
        hashtag_count = len(re.findall(r'#\w+', content))
        if hashtag_count > self.MAX_HASHTAGS:
            errors.append(f"Too many hashtags ({hashtag_count}). Maximum is {self.MAX_HASHTAGS}")
        
        # Image validation if blog post is provided
        if blog_post and include_image_validation:
            try:
                # Check if there are images available
                available_images = self.get_post_images(blog_post)
                if available_images:
                    # Check if at least one image is LinkedIn compatible
                    compatible_image = self.select_best_image_for_linkedin(blog_post)
                    if not compatible_image:
                        # This is a warning, not an error - post can still be text-only
                        logger.warning(f"No LinkedIn-compatible images found for post {blog_post.id}")
                        # Could add this as a warning rather than error:
                        # errors.append("No LinkedIn-compatible images available (post will be text-only)")
                else:
                    logger.debug(f"No images available for post {blog_post.id}")
            except Exception as e:
                logger.error(f"Error during image validation for post {blog_post.id if blog_post else 'unknown'}: {e}")
                # Don't fail validation due to image validation errors
        
        return len(errors) == 0, errors
    
    def format_for_preview(self, blog_post, include_excerpt: bool = True, include_image_analysis: bool = True) -> Dict[str, str]:
        """
        Format content for preview purposes (admin interface, etc.) with enhanced image information.
        
        Args:
            blog_post: Blog Post model instance
            include_excerpt: Whether to include excerpt
            include_image_analysis: Whether to include detailed image analysis
            
        Returns:
            Dictionary with formatted content components and image information
        """
        formatted_content = self.format_post_content(blog_post, include_excerpt)
        validation_result = self.validate_content(formatted_content, blog_post, include_image_validation=True)
        
        result = {
            'full_content': formatted_content,
            'title': self._format_title(blog_post.title),
            'excerpt': self._format_excerpt(blog_post.excerpt) if blog_post.excerpt else self._extract_excerpt_from_content(blog_post.content),
            'url': self._get_post_url(blog_post),
            'hashtags': self._generate_hashtags(blog_post),
            'featured_image_url': self.get_featured_image_url(blog_post),
            'character_count': len(formatted_content),
            'is_valid': validation_result[0],
            'validation_errors': validation_result[1]
        }
        
        # Add enhanced image information if requested
        if include_image_analysis:
            try:
                # Get all available images
                available_images = self.get_post_images(blog_post)
                result['available_images'] = available_images
                result['total_images_count'] = len(available_images)
                
                # Get the best LinkedIn-compatible image
                best_image = self.select_best_image_for_linkedin(blog_post)
                result['best_linkedin_image'] = best_image
                result['has_linkedin_compatible_image'] = best_image is not None
                
                # Image compatibility analysis
                if available_images:
                    compatible_count = 0
                    image_analysis = []
                    
                    for img_url in available_images[:5]:  # Limit analysis to first 5 images
                        is_compatible = self.validate_image_compatibility(img_url)
                        if is_compatible:
                            compatible_count += 1
                        
                        image_analysis.append({
                            'url': img_url,
                            'linkedin_compatible': is_compatible
                        })
                    
                    result['image_analysis'] = image_analysis
                    result['compatible_images_count'] = compatible_count
                    result['image_compatibility_rate'] = (
                        compatible_count / len(available_images) * 100 
                        if available_images else 0
                    )
                else:
                    result['image_analysis'] = []
                    result['compatible_images_count'] = 0
                    result['image_compatibility_rate'] = 0
                
            except Exception as e:
                logger.error(f"Error during image analysis for preview of post {blog_post.id}: {e}")
                # Set default values on error
                result.update({
                    'available_images': [],
                    'total_images_count': 0,
                    'best_linkedin_image': None,
                    'has_linkedin_compatible_image': False,
                    'image_analysis': [],
                    'compatible_images_count': 0,
                    'image_compatibility_rate': 0
                })
        
        return result
    
    def _log_image_posting_metrics(self, post_id, decision_type, include_images, decision_time, 
                                 decision_source, error=None, categories=None):
        """
        Log comprehensive image posting decision metrics for monitoring and analysis.
        
        Args:
            post_id: Blog post ID
            decision_type: Type of decision made (strategy_always, category_based_success, etc.)
            include_images: Whether images will be included
            decision_time: Time taken to make decision
            decision_source: Source of the decision (strategy_setting, category_rules, fallback)
            error: Error message if applicable
            categories: List of post categories if applicable
        """
        try:
            # Create metrics entry
            metrics = {
                'post_id': post_id,
                'decision_type': decision_type,
                'include_images': include_images,
                'decision_time_ms': round(decision_time * 1000, 2),
                'decision_source': decision_source,
                'timestamp': time.time()
            }
            
            if error:
                metrics['error'] = error
            
            if categories:
                metrics['categories'] = categories
            
            # Log appropriate level based on decision type and errors
            if decision_type in ['strategy_always', 'strategy_never']:
                logger.info(f"Image posting decision for post {post_id}: {decision_type} -> {include_images}")
            elif decision_type == 'category_based_success':
                logger.info(f"Category-based image posting decision for post {post_id}: {include_images}")
            elif decision_type in ['globally_disabled', 'optimization_disabled']:
                logger.debug(f"Image posting disabled for post {post_id}: {decision_type}")
            elif 'error' in decision_type or error:
                logger.warning(f"Image posting decision error for post {post_id}: {decision_type} (fallback: {include_images})")
            else:
                logger.debug(f"Image posting decision for post {post_id}: {decision_type} -> {include_images}")
            
            # Cache metrics for monitoring dashboard
            cache_key = f"linkedin_image_posting_metrics_{post_id}"
            cache.set(cache_key, metrics, timeout=86400)  # 24 hours
            
            # Update aggregate metrics
            self._update_image_posting_aggregate_metrics(decision_type, include_images, decision_time, bool(error))
            
        except Exception as e:
            logger.error(f"Error logging image posting metrics for post {post_id}: {e}")
    
    def _update_image_posting_aggregate_metrics(self, decision_type, include_images, decision_time, has_error):
        """
        Update aggregate image posting decision metrics for monitoring.
        
        Args:
            decision_type: Type of decision made
            include_images: Whether images will be included
            decision_time: Time taken for decision
            has_error: Whether an error occurred
        """
        try:
            cache_key = "linkedin_image_posting_aggregate_metrics"
            current_metrics = cache.get(cache_key, {
                'total_decisions': 0,
                'images_included_count': 0,
                'images_excluded_count': 0,
                'error_count': 0,
                'avg_decision_time': 0,
                'decision_types': {},
                'decision_sources': {},
                'performance_stats': {
                    'slow_decisions': 0,  # > 0.1 seconds
                    'very_slow_decisions': 0,  # > 0.5 seconds
                },
                'last_updated': time.time()
            })
            
            current_metrics['total_decisions'] += 1
            current_metrics['last_updated'] = time.time()
            
            if include_images:
                current_metrics['images_included_count'] += 1
            else:
                current_metrics['images_excluded_count'] += 1
            
            if has_error:
                current_metrics['error_count'] += 1
            
            # Track decision types
            current_metrics['decision_types'][decision_type] = current_metrics['decision_types'].get(decision_type, 0) + 1
            
            # Track performance
            if decision_time > 0.5:
                current_metrics['performance_stats']['very_slow_decisions'] += 1
            elif decision_time > 0.1:
                current_metrics['performance_stats']['slow_decisions'] += 1
            
            # Update average decision time
            if current_metrics['total_decisions'] > 0:
                current_avg = current_metrics['avg_decision_time']
                new_avg = ((current_avg * (current_metrics['total_decisions'] - 1)) + decision_time) / current_metrics['total_decisions']
                current_metrics['avg_decision_time'] = round(new_avg, 3)
            
            cache.set(cache_key, current_metrics, timeout=86400)  # 24 hours
            
            # Log periodic statistics
            if current_metrics['total_decisions'] % 20 == 0:  # Every 20 decisions
                inclusion_rate = (current_metrics['images_included_count'] / current_metrics['total_decisions']) * 100
                error_rate = (current_metrics['error_count'] / current_metrics['total_decisions']) * 100
                
                logger.info(f"Image posting decision stats: {current_metrics['total_decisions']} decisions, "
                          f"{inclusion_rate:.1f}% include images, {error_rate:.1f}% error rate, "
                          f"avg {current_metrics['avg_decision_time']:.3f}s decision time")
                
                # Log performance warnings
                slow_percentage = (current_metrics['performance_stats']['slow_decisions'] / current_metrics['total_decisions']) * 100
                if slow_percentage > 10:  # More than 10% slow
                    logger.warning(f"High percentage of slow image posting decisions: {slow_percentage:.1f}% > 0.1s")
            
        except Exception as e:
            logger.error(f"Error updating image posting aggregate metrics: {e}")
    
    def get_image_posting_metrics_summary(self):
        """
        Get a comprehensive summary of image posting decision metrics for monitoring.
        
        Returns:
            dict: Image posting metrics summary
        """
        try:
            cache_key = "linkedin_image_posting_aggregate_metrics"
            metrics = cache.get(cache_key, {})
            
            if not metrics:
                return {'status': 'no_data', 'message': 'No image posting metrics available'}
            
            total_decisions = metrics.get('total_decisions', 0)
            if total_decisions == 0:
                return {'status': 'no_decisions', 'message': 'No image posting decisions recorded'}
            
            images_included = metrics.get('images_included_count', 0)
            images_excluded = metrics.get('images_excluded_count', 0)
            error_count = metrics.get('error_count', 0)
            
            inclusion_rate = (images_included / total_decisions) * 100 if total_decisions > 0 else 0
            error_rate = (error_count / total_decisions) * 100 if total_decisions > 0 else 0
            
            performance_stats = metrics.get('performance_stats', {})
            slow_percentage = (performance_stats.get('slow_decisions', 0) / total_decisions) * 100 if total_decisions > 0 else 0
            
            summary = {
                'status': 'active',
                'total_decisions': total_decisions,
                'images_included_count': images_included,
                'images_excluded_count': images_excluded,
                'inclusion_rate_percent': round(inclusion_rate, 1),
                'exclusion_rate_percent': round(100 - inclusion_rate, 1),
                'error_count': error_count,
                'error_rate_percent': round(error_rate, 1),
                'avg_decision_time_seconds': metrics.get('avg_decision_time', 0),
                'performance_metrics': {
                    'slow_decisions_percent': round(slow_percentage, 1),
                    'very_slow_decisions': performance_stats.get('very_slow_decisions', 0),
                },
                'decision_types': metrics.get('decision_types', {}),
                'last_updated': metrics.get('last_updated'),
                'health_status': self._assess_image_posting_health(metrics)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting image posting metrics summary: {e}")
            return {'status': 'error', 'message': f'Error retrieving metrics: {e}'}
    
    def _assess_image_posting_health(self, metrics):
        """
        Assess the health of image posting decisions based on metrics.
        
        Args:
            metrics: Image posting metrics dictionary
            
        Returns:
            str: Health status (healthy, warning, critical)
        """
        try:
            total_decisions = metrics.get('total_decisions', 0)
            if total_decisions < 5:
                return 'insufficient_data'
            
            error_count = metrics.get('error_count', 0)
            error_rate = (error_count / total_decisions) * 100 if total_decisions > 0 else 0
            
            performance_stats = metrics.get('performance_stats', {})
            slow_percentage = (performance_stats.get('slow_decisions', 0) / total_decisions) * 100 if total_decisions > 0 else 0
            
            # Assess health based on error rate and performance
            if error_rate > 25:
                return 'critical'
            elif error_rate > 10 or slow_percentage > 30:
                return 'warning'
            elif error_rate < 5 and slow_percentage < 10:
                return 'healthy'
            else:
                return 'warning'
                
        except Exception as e:
            logger.error(f"Error assessing image posting health: {e}")
            return 'unknown'


# Convenience functions for easy usage
def format_blog_post_for_linkedin(blog_post, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
    """
    Convenience function to format a blog post for LinkedIn with image optimization.
    
    Args:
        blog_post: Blog Post model instance
        include_excerpt: Whether to include excerpt in the post
        optimize_for_images: Whether to optimize content for image posts
        
    Returns:
        Formatted LinkedIn post content
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_content(blog_post, include_excerpt, optimize_for_images)


def get_blog_post_hashtags(blog_post) -> str:
    """
    Convenience function to get hashtags for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        Formatted hashtags string
    """
    formatter = LinkedInContentFormatter()
    return formatter._generate_hashtags(blog_post)


def get_blog_post_featured_image(blog_post) -> Optional[str]:
    """
    Convenience function to get featured image URL for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        Full URL to featured image or None
    """
    formatter = LinkedInContentFormatter()
    return formatter.get_featured_image_url(blog_post)


def get_blog_post_images(blog_post) -> List[str]:
    """
    Convenience function to get all available images from a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        List of absolute URLs to available images
    """
    formatter = LinkedInContentFormatter()
    return formatter.get_post_images(blog_post)


def get_best_linkedin_image(blog_post) -> Optional[str]:
    """
    Convenience function to get the best LinkedIn-compatible image for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        
    Returns:
        URL of the best LinkedIn-compatible image, or None if no suitable image found
    """
    formatter = LinkedInContentFormatter()
    return formatter.select_best_image_for_linkedin(blog_post)


def generate_hashtags_for_post(blog_post, config=None) -> List[str]:
    """
    Convenience function to generate hashtags for a blog post.
    
    Args:
        blog_post: Blog Post model instance
        config: Optional LinkedInConfig instance or hashtag configuration dict
        
    Returns:
        List of formatted hashtags
    """
    generator = HashtagGenerator(config)
    return generator.generate_hashtags(blog_post)


def format_blog_post_with_config(blog_post, config, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
    """
    Convenience function to format a blog post for LinkedIn with explicit configuration.
    
    Args:
        blog_post: Blog Post model instance
        config: LinkedInConfig instance with hashtag and image posting settings
        include_excerpt: Whether to include excerpt in the post
        optimize_for_images: Whether to optimize content for image posts
        
    Returns:
        Formatted LinkedIn post content
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_with_config(blog_post, config, include_excerpt, optimize_for_images)


def format_blog_post_with_linkedin_config(blog_post, config, include_excerpt: bool = True, optimize_for_images: bool = True) -> str:
    """
    Convenience function to format a blog post for LinkedIn with configuration.
    
    Args:
        blog_post: Blog Post model instance
        config: LinkedInConfig instance with hashtag and image posting settings
        include_excerpt: Whether to include excerpt in the post
        optimize_for_images: Whether to optimize content for image posts
        
    Returns:
        Formatted LinkedIn post content
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_with_config(blog_post, config, include_excerpt, optimize_for_images)


def validate_image_for_linkedin(image_url: str) -> bool:
    """
    Convenience function to validate if an image is LinkedIn-compatible.
    
    Args:
        image_url: URL of the image to validate
        
    Returns:
        True if image is compatible with LinkedIn, False otherwise
    """
    formatter = LinkedInContentFormatter()
    return formatter.validate_image_compatibility(image_url)


def get_linkedin_post_with_images(blog_post, include_excerpt: bool = True) -> Dict[str, Any]:
    """
    Convenience function to get comprehensive LinkedIn post information with images.
    
    Args:
        blog_post: Blog Post model instance
        include_excerpt: Whether to include excerpt in the post
        
    Returns:
        Dictionary with formatted content and image information
    """
    formatter = LinkedInContentFormatter()
    return formatter.format_post_with_image_info(blog_post, include_excerpt)



def validate_linkedin_content(content: str, blog_post=None, include_image_validation: bool = True) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate LinkedIn content with image considerations.
    
    Args:
        content: Formatted LinkedIn post content
        blog_post: Optional blog post instance for image validation
        include_image_validation: Whether to validate associated images
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    formatter = LinkedInContentFormatter()
    return formatter.validate_content(content, blog_post, include_image_validation)