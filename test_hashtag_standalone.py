#!/usr/bin/env python3
"""
Standalone unit tests for HashtagGenerator functionality.

This file tests the hashtag generation logic without requiring Django models or database.
"""

import unittest
from unittest.mock import Mock
import re


class MockHashtagGenerator:
    """Mock implementation of HashtagGenerator for testing."""
    
    DEFAULT_MAX_HASHTAGS = 5
    MIN_HASHTAG_LENGTH = 2
    MAX_HASHTAG_LENGTH = 100
    
    def __init__(self, config=None):
        if hasattr(config, 'get_hashtag_config'):
            self.config = config.get_hashtag_config()
        elif isinstance(config, dict):
            self.config = config
        else:
            self.config = {
                'enable_hashtags': True,
                'max_hashtags': self.DEFAULT_MAX_HASHTAGS,
                'custom_hashtag_rules': {},
                'hashtag_blacklist': []
            }
    
    def validate_hashtag(self, hashtag):
        """Validate hashtag format."""
        if not hashtag or not isinstance(hashtag, str):
            return False
        
        clean_hashtag = hashtag.lstrip('#')
        
        if len(clean_hashtag) < self.MIN_HASHTAG_LENGTH or len(clean_hashtag) > self.MAX_HASHTAG_LENGTH:
            return False
        
        if not re.match(r'^[a-zA-Z0-9_]+$', clean_hashtag):
            return False
        
        if clean_hashtag.isdigit():
            return False
        
        if not clean_hashtag[0].isalpha():
            return False
        
        return True
    
    def format_hashtag(self, tag_name):
        """Format a tag name as a hashtag."""
        if not tag_name or not isinstance(tag_name, str):
            return ""
        
        if tag_name.startswith('#'):
            tag_name = tag_name[1:]
        
        clean_tag = re.sub(r'[^a-zA-Z0-9\s]', '', tag_name.strip())
        
        if not clean_tag:
            return ""
        
        words = clean_tag.split()
        if not words:
            return ""
        
        formatted_words = [words[0].lower()]
        for word in words[1:]:
            if word:
                formatted_words.append(word.capitalize())
        
        hashtag = ''.join(formatted_words)
        
        if self.validate_hashtag(hashtag):
            return f"#{hashtag}"
        
        return ""
    
    def generate_from_tags(self, blog_post, max_count):
        """Generate hashtags from blog post tags."""
        if not hasattr(blog_post, 'tags') or max_count <= 0:
            return []
        
        try:
            if not blog_post.tags.exists():
                return []
        except:
            return []
        
        hashtags = []
        try:
            tag_names = list(blog_post.tags.values_list('name', flat=True)[:max_count])
            
            for tag_name in tag_names:
                if len(hashtags) >= max_count:
                    break
                
                formatted_hashtag = self.format_hashtag(tag_name)
                if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                    hashtags.append(formatted_hashtag)
        except:
            return []
        
        return hashtags
    
    def generate_from_categories(self, blog_post, max_count):
        """Generate hashtags from blog post categories."""
        if not hasattr(blog_post, 'categories') or max_count <= 0:
            return []
        
        try:
            if not blog_post.categories.exists():
                return []
        except:
            return []
        
        hashtags = []
        try:
            category_names = list(blog_post.categories.values_list('name', flat=True)[:max_count])
            
            for category_name in category_names:
                if len(hashtags) >= max_count:
                    break
                
                formatted_hashtag = self.format_hashtag(category_name)
                if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                    hashtags.append(formatted_hashtag)
        except:
            return []
        
        return hashtags
    
    def generate_from_content(self, blog_post, max_count):
        """Generate hashtags from blog post content."""
        if max_count <= 0:
            return []
        
        content_text = ""
        try:
            if hasattr(blog_post, 'title') and blog_post.title:
                content_text += blog_post.title + " "
            if hasattr(blog_post, 'excerpt') and blog_post.excerpt:
                # Simple HTML tag removal
                clean_excerpt = re.sub(r'<[^>]+>', '', blog_post.excerpt)
                content_text += clean_excerpt + " "
            elif hasattr(blog_post, 'content') and blog_post.content:
                # Simple HTML tag removal
                clean_content = re.sub(r'<[^>]+>', '', blog_post.content)
                content_text += clean_content[:500] + " "
        except:
            return []
        
        if not content_text.strip():
            return []
        
        return self._extract_keywords_from_text(content_text, max_count)
    
    def _extract_keywords_from_text(self, text, max_count):
        """Extract keywords from text."""
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        word_freq = {}
        for word in words:
            if (len(word) >= 3 and 
                word not in stop_words and 
                not word.isdigit() and 
                word.isalpha()):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        hashtags = []
        for word, freq in sorted_words[:max_count * 2]:
            formatted_hashtag = self.format_hashtag(word)
            if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                hashtags.append(formatted_hashtag)
                if len(hashtags) >= max_count:
                    break
        
        return hashtags
    
    def filter_blacklisted_hashtags(self, hashtags):
        """Filter out blacklisted hashtags."""
        blacklist = self.config.get('hashtag_blacklist', [])
        if not blacklist:
            return hashtags
        
        blacklist_lower = [term.lower() for term in blacklist if isinstance(term, str)]
        
        filtered_hashtags = []
        for hashtag in hashtags:
            hashtag_clean = hashtag.lstrip('#').lower()
            
            is_blacklisted = False
            for blacklisted_term in blacklist_lower:
                if blacklisted_term in hashtag_clean:
                    is_blacklisted = True
                    break
            
            if not is_blacklisted:
                filtered_hashtags.append(hashtag)
        
        return filtered_hashtags
    
    def apply_custom_rules(self, hashtags, category_rules):
        """Apply custom hashtag rules."""
        if not category_rules or not isinstance(category_rules, dict):
            return hashtags
        
        processed_hashtags = []
        
        for hashtag in hashtags:
            processed_hashtag = hashtag
            
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
    
    def generate_hashtags(self, blog_post, max_count=None):
        """Generate hashtags using all sources."""
        if not self.config.get('enable_hashtags', True):
            return []
        
        max_hashtags = max_count or self.config.get('max_hashtags', self.DEFAULT_MAX_HASHTAGS)
        if max_hashtags <= 0:
            return []
        
        all_hashtags = []
        
        # Get custom hashtags first
        custom_hashtags = self._get_custom_hashtags_for_post(blog_post)
        all_hashtags.extend(custom_hashtags)
        
        # Generate from tags
        if len(all_hashtags) < max_hashtags:
            tag_hashtags = self.generate_from_tags(blog_post, max_hashtags - len(all_hashtags))
            all_hashtags.extend(tag_hashtags)
        
        # Generate from categories
        if len(all_hashtags) < max_hashtags:
            category_hashtags = self.generate_from_categories(blog_post, max_hashtags - len(all_hashtags))
            all_hashtags.extend(category_hashtags)
        
        # Generate from content
        if len(all_hashtags) < max_hashtags:
            content_hashtags = self.generate_from_content(blog_post, max_hashtags - len(all_hashtags))
            all_hashtags.extend(content_hashtags)
        
        # Remove duplicates
        unique_hashtags = []
        seen = set()
        for hashtag in all_hashtags:
            hashtag_lower = hashtag.lower()
            if hashtag_lower not in seen:
                unique_hashtags.append(hashtag)
                seen.add(hashtag_lower)
        
        # Apply blacklist filtering
        filtered_hashtags = self.filter_blacklisted_hashtags(unique_hashtags)
        
        # Apply final validation
        valid_hashtags = []
        for hashtag in filtered_hashtags:
            if self.validate_hashtag(hashtag):
                valid_hashtags.append(hashtag)
        
        return valid_hashtags[:max_hashtags]
    
    def _get_custom_hashtags_for_post(self, blog_post):
        """Get custom hashtags for post categories."""
        custom_rules = self.config.get('custom_hashtag_rules', {})
        if not custom_rules or not hasattr(blog_post, 'categories'):
            return []
        
        custom_hashtags = []
        
        try:
            for category in blog_post.categories.all():
                category_key = getattr(category, 'slug', category.name.lower())
                
                if category_key in custom_rules:
                    rules = custom_rules[category_key]
                    
                    if isinstance(rules, dict) and 'required_hashtags' in rules:
                        required = rules['required_hashtags']
                        if isinstance(required, list):
                            custom_hashtags.extend(required)
                    
                    if isinstance(rules, dict) and 'suggested_hashtags' in rules:
                        suggested = rules['suggested_hashtags']
                        if isinstance(suggested, list):
                            custom_hashtags.extend(suggested)
                    
                    elif isinstance(rules, list):
                        custom_hashtags.extend(rules)
        except:
            return []
        
        # Format and validate
        formatted_hashtags = []
        for hashtag in custom_hashtags:
            formatted = self.format_hashtag(hashtag)
            if formatted and self.validate_hashtag(formatted):
                formatted_hashtags.append(formatted)
        
        return formatted_hashtags


class TestHashtagGeneratorComprehensive(unittest.TestCase):
    """Comprehensive unit tests for HashtagGenerator functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.generator = MockHashtagGenerator()
    
    def test_hashtag_validation_comprehensive(self):
        """Test hashtag validation with various input scenarios."""
        # Valid cases
        valid_cases = [
            "python", "#python", "webDevelopment", "#webDevelopment",
            "api2", "#api2", "test123", "#test123",
            "a" * MockHashtagGenerator.MIN_HASHTAG_LENGTH,
            "a" * MockHashtagGenerator.MAX_HASHTAG_LENGTH,
            "Python_API", "#Python_API"
        ]
        
        for case in valid_cases:
            with self.subTest(case=case):
                self.assertTrue(self.generator.validate_hashtag(case))
        
        # Invalid cases
        invalid_cases = [
            None, "", "   ", 123, [], {}, "a", "123", "#123", "1abc",
            "test-tag", "test tag", "test@tag", "test.tag",
            "a" * (MockHashtagGenerator.MAX_HASHTAG_LENGTH + 1)
        ]
        
        for case in invalid_cases:
            with self.subTest(case=case):
                self.assertFalse(self.generator.validate_hashtag(case))
    
    def test_hashtag_formatting_comprehensive(self):
        """Test hashtag formatting with various input scenarios."""
        test_cases = [
            ("Python", "#python"),
            ("Web Development", "#webDevelopment"),
            ("API Design", "#apiDesign"),
            ("machine learning", "#machineLearning"),
            ("DJANGO FRAMEWORK", "#djangoFramework"),
            ("   Python   ", "#python"),
            ("Python!@#", "#python"),
            ("Web-Development", "#webdevelopment"),
            ("#Python", "#python"),
            ("", ""),
            (None, ""),
            ("123", ""),
            ("!@#$%", "")
        ]
        
        for input_tag, expected in test_cases:
            with self.subTest(input=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected)
    
    def test_generate_from_tags_various_scenarios(self):
        """Test hashtag generation from tags with various scenarios."""
        # Mock post with tags
        mock_post = Mock()
        mock_post.tags.exists.return_value = True
        mock_post.tags.values_list.return_value = ['Python', 'Django', 'Web Development']
        
        hashtags = self.generator.generate_from_tags(mock_post, 5)
        
        self.assertIn('#python', hashtags)
        self.assertIn('#django', hashtags)
        self.assertIn('#webDevelopment', hashtags)
        
        # Test with no tags
        mock_post_no_tags = Mock()
        mock_post_no_tags.tags.exists.return_value = False
        
        hashtags_empty = self.generator.generate_from_tags(mock_post_no_tags, 5)
        self.assertEqual(hashtags_empty, [])
        
        # Test with zero max_count
        hashtags_zero = self.generator.generate_from_tags(mock_post, 0)
        self.assertEqual(hashtags_zero, [])
        
        # Test error handling
        mock_post_error = Mock()
        mock_post_error.tags.exists.side_effect = Exception("Database error")
        
        hashtags_error = self.generator.generate_from_tags(mock_post_error, 5)
        self.assertEqual(hashtags_error, [])
    
    def test_generate_from_categories_various_scenarios(self):
        """Test hashtag generation from categories with various scenarios."""
        # Mock post with categories
        mock_post = Mock()
        mock_post.categories.exists.return_value = True
        mock_post.categories.values_list.return_value = ['Technology', 'Tutorial']
        
        hashtags = self.generator.generate_from_categories(mock_post, 5)
        
        self.assertIn('#technology', hashtags)
        self.assertIn('#tutorial', hashtags)
        
        # Test with no categories
        mock_post_no_cats = Mock()
        mock_post_no_cats.categories.exists.return_value = False
        
        hashtags_empty = self.generator.generate_from_categories(mock_post_no_cats, 5)
        self.assertEqual(hashtags_empty, [])
        
        # Test error handling
        mock_post_error = Mock()
        mock_post_error.categories.exists.side_effect = Exception("Database error")
        
        hashtags_error = self.generator.generate_from_categories(mock_post_error, 5)
        self.assertEqual(hashtags_error, [])
    
    def test_generate_from_content_various_scenarios(self):
        """Test hashtag generation from content with various scenarios."""
        # Mock post with content
        mock_post = Mock()
        mock_post.title = "Python Machine Learning Tutorial"
        mock_post.excerpt = "Learn Python machine learning with practical examples"
        mock_post.content = "<p>Python programming for machine learning applications</p>"
        
        hashtags = self.generator.generate_from_content(mock_post, 5)
        
        self.assertTrue(len(hashtags) > 0)
        hashtag_text = ' '.join(hashtags).lower()
        self.assertTrue(any(keyword in hashtag_text for keyword in ['python', 'machine', 'learning']))
        
        # Test with empty content
        mock_post_empty = Mock()
        mock_post_empty.title = ""
        mock_post_empty.excerpt = ""
        mock_post_empty.content = ""
        
        hashtags_empty = self.generator.generate_from_content(mock_post_empty, 5)
        self.assertEqual(hashtags_empty, [])
        
        # Test with zero max_count
        hashtags_zero = self.generator.generate_from_content(mock_post, 0)
        self.assertEqual(hashtags_zero, [])
    
    def test_custom_hashtag_rules_application(self):
        """Test custom hashtag rules application and blacklist filtering."""
        # Test blacklist filtering
        hashtags = ['#python', '#spam', '#django', '#clickbait', '#webdev']
        config = {
            'hashtag_blacklist': ['spam', 'clickbait']
        }
        generator = MockHashtagGenerator(config)
        
        filtered = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertIn('#python', filtered)
        self.assertIn('#django', filtered)
        self.assertIn('#webdev', filtered)
        self.assertNotIn('#spam', filtered)
        self.assertNotIn('#clickbait', filtered)
        
        # Test custom rules
        hashtags_for_rules = ['#python', '#webdev', '#coding']
        category_rules = {
            'technology': {
                'replacements': {
                    'python': 'PythonProgramming',
                    'webdev': 'WebDevelopment'
                }
            }
        }
        
        processed = generator.apply_custom_rules(hashtags_for_rules, category_rules)
        
        self.assertIn('#pythonprogramming', processed)
        self.assertIn('#webdevelopment', processed)
        self.assertIn('#coding', processed)
    
    def test_hashtag_generation_edge_cases(self):
        """Test hashtag generation edge cases and error handling."""
        # Test with disabled hashtags
        config_disabled = {'enable_hashtags': False}
        generator_disabled = MockHashtagGenerator(config_disabled)
        
        mock_post = Mock()
        mock_post.tags.exists.return_value = True
        mock_post.tags.values_list.return_value = ['Python']
        
        hashtags_disabled = generator_disabled.generate_hashtags(mock_post)
        self.assertEqual(hashtags_disabled, [])
        
        # Test with zero max_hashtags
        config_zero = {'enable_hashtags': True, 'max_hashtags': 0}
        generator_zero = MockHashtagGenerator(config_zero)
        
        hashtags_zero = generator_zero.generate_hashtags(mock_post)
        self.assertEqual(hashtags_zero, [])
        
        # Test duplicate removal
        mock_post_duplicates = Mock()
        mock_post_duplicates.tags.exists.return_value = True
        mock_post_duplicates.tags.values_list.return_value = ['Python', 'python', 'PYTHON']
        mock_post_duplicates.categories.exists.return_value = False
        mock_post_duplicates.title = ""
        mock_post_duplicates.excerpt = ""
        mock_post_duplicates.content = ""
        
        hashtags_unique = self.generator.generate_hashtags(mock_post_duplicates)
        
        # Should only have one Python hashtag
        python_count = sum(1 for h in hashtags_unique if 'python' in h.lower())
        self.assertEqual(python_count, 1)
    
    def test_error_handling_and_resilience(self):
        """Test error handling and resilience in various failure scenarios."""
        # Mock post that raises exceptions
        mock_post_error = Mock()
        mock_post_error.tags.exists.side_effect = Exception("Database error")
        mock_post_error.categories.exists.side_effect = Exception("Database error")
        mock_post_error.title = "Test Title"
        mock_post_error.content = "Test content with python and django"
        mock_post_error.excerpt = "Test excerpt"
        
        # Should not raise exceptions
        try:
            hashtags = self.generator.generate_hashtags(mock_post_error)
            self.assertIsInstance(hashtags, list)
        except Exception as e:
            self.fail(f"generate_hashtags should handle exceptions gracefully: {e}")
        
        # Test with missing attributes
        mock_post_minimal = Mock()
        # Remove attributes that might not exist
        if hasattr(mock_post_minimal, 'tags'):
            del mock_post_minimal.tags
        if hasattr(mock_post_minimal, 'categories'):
            del mock_post_minimal.categories
        
        try:
            hashtags_minimal = self.generator.generate_hashtags(mock_post_minimal)
            self.assertIsInstance(hashtags_minimal, list)
        except Exception as e:
            self.fail(f"generate_hashtags should handle missing attributes gracefully: {e}")
    
    def test_boundary_conditions(self):
        """Test boundary conditions and limits."""
        # Test exactly at boundaries
        min_length_tag = "a" * MockHashtagGenerator.MIN_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(min_length_tag))
        
        max_length_tag = "a" * MockHashtagGenerator.MAX_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(max_length_tag))
        
        # Test just outside boundaries
        under_min_tag = "a" * (MockHashtagGenerator.MIN_HASHTAG_LENGTH - 1)
        self.assertFalse(self.generator.validate_hashtag(under_min_tag))
        
        over_max_tag = "a" * (MockHashtagGenerator.MAX_HASHTAG_LENGTH + 1)
        self.assertFalse(self.generator.validate_hashtag(over_max_tag))


if __name__ == '__main__':
    print("Running comprehensive HashtagGenerator unit tests...")
    unittest.main(verbosity=2)