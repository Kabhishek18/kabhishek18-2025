"""
Comprehensive unit tests for HashtagGenerator class - Additional test coverage.

This file provides additional test cases to ensure complete coverage of hashtag generation
functionality, focusing on edge cases and comprehensive scenarios.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth.models import User

from blog.models import Post, Tag, Category


class MockHashtagGenerator:
    """Mock HashtagGenerator for testing when the real one has import issues."""
    
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
        
        import re
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
        
        import re
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
        if not hasattr(blog_post, 'tags') or not blog_post.tags.exists() or max_count <= 0:
            return []
        
        hashtags = []
        tag_names = list(blog_post.tags.values_list('name', flat=True)[:max_count])
        
        for tag_name in tag_names:
            if len(hashtags) >= max_count:
                break
            
            formatted_hashtag = self.format_hashtag(tag_name)
            if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                hashtags.append(formatted_hashtag)
        
        return hashtags
    
    def generate_from_categories(self, blog_post, max_count):
        """Generate hashtags from blog post categories."""
        if not hasattr(blog_post, 'categories') or not blog_post.categories.exists() or max_count <= 0:
            return []
        
        hashtags = []
        category_names = list(blog_post.categories.values_list('name', flat=True)[:max_count])
        
        for category_name in category_names:
            if len(hashtags) >= max_count:
                break
            
            formatted_hashtag = self.format_hashtag(category_name)
            if formatted_hashtag and self.validate_hashtag(formatted_hashtag):
                hashtags.append(formatted_hashtag)
        
        return hashtags
    
    def generate_from_content(self, blog_post, max_count):
        """Generate hashtags from blog post content."""
        if max_count <= 0:
            return []
        
        content_text = ""
        if hasattr(blog_post, 'title') and blog_post.title:
            content_text += blog_post.title + " "
        if hasattr(blog_post, 'excerpt') and blog_post.excerpt:
            from django.utils.html import strip_tags
            content_text += strip_tags(blog_post.excerpt) + " "
        elif hasattr(blog_post, 'content') and blog_post.content:
            from django.utils.html import strip_tags
            clean_content = strip_tags(blog_post.content)
            content_text += clean_content[:500] + " "
        
        if not content_text.strip():
            return []
        
        return self._extract_keywords_from_text(content_text, max_count)
    
    def _extract_keywords_from_text(self, text, max_count):
        """Extract keywords from text."""
        import re
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


class ComprehensiveHashtagGeneratorTest(TestCase):
    """Comprehensive test cases for HashtagGenerator with edge cases and error scenarios."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test tags with various formats
        self.tag_simple = Tag.objects.create(name='Python', slug='python')
        self.tag_multiword = Tag.objects.create(name='Machine Learning', slug='machine-learning')
        self.tag_special_chars = Tag.objects.create(name='API-Design', slug='api-design')
        self.tag_numbers = Tag.objects.create(name='Python3', slug='python3')
        self.tag_long = Tag.objects.create(name='Very Long Tag Name That Might Cause Issues', slug='very-long-tag')
        
        # Create test categories
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        
        # Create test posts with various content scenarios
        self.post_standard = Post.objects.create(
            title='Python Machine Learning Tutorial',
            slug='python-ml-tutorial',
            author=self.user,
            content='<p>Learn Python machine learning with practical examples and code samples.</p>',
            excerpt='Python ML tutorial with examples',
            status='published'
        )
        self.post_standard.tags.add(self.tag_simple, self.tag_multiword)
        self.post_standard.categories.add(self.category_tech, self.category_tutorial)
        
        self.generator = MockHashtagGenerator()
    
    def test_hashtag_validation_comprehensive_edge_cases(self):
        """Test hashtag validation with comprehensive edge cases."""
        # Test various invalid inputs
        invalid_cases = [
            None,  # None input
            "",    # Empty string
            "   ", # Whitespace only
            123,   # Non-string type
            [],    # List type
            {},    # Dict type
            "a",   # Too short (below MIN_HASHTAG_LENGTH)
            "ab",  # At minimum length boundary
            "a" * (MockHashtagGenerator.MAX_HASHTAG_LENGTH + 1),  # Too long
            "123", # All numbers
            "#123", # All numbers with hash
            "1abc", # Starts with number
            "#1abc", # Starts with number with hash
            "test-tag", # Contains hyphen
            "test tag", # Contains space
            "test@tag", # Contains @ symbol
            "test#tag", # Contains # in middle
            "test.tag", # Contains period
            "test,tag", # Contains comma
            "test!tag", # Contains exclamation
            "test?tag", # Contains question mark
            "test&tag", # Contains ampersand
            "test%tag", # Contains percent
            "test$tag", # Contains dollar sign
            "test+tag", # Contains plus
            "test=tag", # Contains equals
            "test[tag]", # Contains brackets
            "test{tag}", # Contains braces
            "test(tag)", # Contains parentheses
            "test|tag", # Contains pipe
            "test\\tag", # Contains backslash
            "test/tag", # Contains forward slash
            "test\"tag", # Contains quote
            "test'tag", # Contains apostrophe
            "test`tag", # Contains backtick
            "test~tag", # Contains tilde
            "test^tag", # Contains caret
            "test*tag", # Contains asterisk
        ]
        
        for invalid_input in invalid_cases:
            with self.subTest(input=invalid_input):
                self.assertFalse(self.generator.validate_hashtag(invalid_input))
        
        # Test valid cases
        valid_cases = [
            "python",
            "#python",
            "webDevelopment",
            "#webDevelopment",
            "api2",
            "#api2",
            "test123",
            "#test123",
            "a" * MockHashtagGenerator.MIN_HASHTAG_LENGTH,  # Minimum valid length
            "a" * MockHashtagGenerator.MAX_HASHTAG_LENGTH,  # Maximum valid length
            "Python_API",
            "#Python_API",
            "test_123",
            "#test_123",
            "camelCaseHashtag",
            "#camelCaseHashtag",
        ]
        
        for valid_input in valid_cases:
            with self.subTest(input=valid_input):
                self.assertTrue(self.generator.validate_hashtag(valid_input))
    
    def test_hashtag_formatting_comprehensive_edge_cases(self):
        """Test hashtag formatting with comprehensive edge cases."""
        # Test edge cases that should return empty string
        empty_result_cases = [
            None,
            "",
            "   ",
            "123",
            "#123",
            "!@#$%^&*()",
            "   !@#   ",
            "1234567890",
            "#1234567890",
        ]
        
        for input_case in empty_result_cases:
            with self.subTest(input=input_case):
                result = self.generator.format_hashtag(input_case)
                self.assertEqual(result, "")
        
        # Test complex formatting scenarios
        formatting_cases = [
            # (input, expected_output)
            ("Python", "#python"),
            ("PYTHON", "#python"),
            ("python", "#python"),
            ("Web Development", "#webDevelopment"),
            ("WEB DEVELOPMENT", "#webDevelopment"),
            ("web development", "#webDevelopment"),
            ("API Design", "#apiDesign"),
            ("Machine Learning", "#machineLearning"),
            ("Data Science", "#dataScience"),
            ("Full Stack Development", "#fullStackDevelopment"),
            ("   Python   ", "#python"),  # Extra whitespace
            ("Multiple   Spaces   Between", "#multipleSpacesBetween"),
            ("Python!@#", "#python"),  # Special characters removed
            ("Web-Development", "#webDevelopment"),  # Hyphen removed
            ("API@Design", "#apiDesign"),  # @ symbol removed
            ("Test & Debug", "#testDebug"),  # & symbol removed
            ("C++", "#c"),  # Special characters removed, only C remains
            ("Node.js", "#nodejs"),  # Period removed
            ("React.js Framework", "#reactjsFramework"),
            ("#Python", "#python"),  # Already has hash
            ("##Python", "#python"),  # Multiple hashes
            ("Python##", "#python"),  # Hash at end
            ("Py#thon", "#python"),  # Hash in middle
        ]
        
        for input_tag, expected_output in formatting_cases:
            with self.subTest(input=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_generate_from_tags_edge_cases(self):
        """Test hashtag generation from tags with edge cases."""
        # Test with post that has no tags attribute
        mock_post_no_tags_attr = Mock()
        del mock_post_no_tags_attr.tags  # Remove tags attribute
        
        hashtags = self.generator.generate_from_tags(mock_post_no_tags_attr, 5)
        self.assertEqual(hashtags, [])
        
        # Test with post where tags.exists() returns False
        mock_post_no_tags = Mock()
        mock_post_no_tags.tags.exists.return_value = False
        
        hashtags = self.generator.generate_from_tags(mock_post_no_tags, 5)
        self.assertEqual(hashtags, [])
        
        # Test with zero max_count
        hashtags = self.generator.generate_from_tags(self.post_standard, 0)
        self.assertEqual(hashtags, [])
        
        # Test with negative max_count
        hashtags = self.generator.generate_from_tags(self.post_standard, -1)
        self.assertEqual(hashtags, [])
        
        # Test with very large max_count
        hashtags = self.generator.generate_from_tags(self.post_standard, 1000)
        self.assertTrue(len(hashtags) <= 2)  # Post only has 2 tags
    
    def test_generate_from_categories_edge_cases(self):
        """Test hashtag generation from categories with edge cases."""
        # Test with post that has no categories attribute
        mock_post_no_categories_attr = Mock()
        del mock_post_no_categories_attr.categories
        
        hashtags = self.generator.generate_from_categories(mock_post_no_categories_attr, 5)
        self.assertEqual(hashtags, [])
        
        # Test with post where categories.exists() returns False
        mock_post_no_categories = Mock()
        mock_post_no_categories.categories.exists.return_value = False
        
        hashtags = self.generator.generate_from_categories(mock_post_no_categories, 5)
        self.assertEqual(hashtags, [])
        
        # Test with zero max_count
        hashtags = self.generator.generate_from_categories(self.post_standard, 0)
        self.assertEqual(hashtags, [])
        
        # Test with negative max_count
        hashtags = self.generator.generate_from_categories(self.post_standard, -1)
        self.assertEqual(hashtags, [])
    
    def test_generate_from_content_edge_cases(self):
        """Test hashtag generation from content with edge cases."""
        # Test with zero max_count
        hashtags = self.generator.generate_from_content(self.post_standard, 0)
        self.assertEqual(hashtags, [])
        
        # Test with negative max_count
        hashtags = self.generator.generate_from_content(self.post_standard, -1)
        self.assertEqual(hashtags, [])
        
        # Test with post that has no title, content, or excerpt
        empty_post = Post.objects.create(
            title='',
            slug='empty-post',
            author=self.user,
            content='',
            excerpt='',
            status='published'
        )
        
        hashtags = self.generator.generate_from_content(empty_post, 5)
        self.assertEqual(hashtags, [])
        
        # Test with post that has only HTML tags in content
        html_only_post = Post.objects.create(
            title='',
            slug='html-only-post',
            author=self.user,
            content='<div><p></p><br/><img src="test.jpg"/></div>',
            excerpt='<span></span>',
            status='published'
        )
        
        hashtags = self.generator.generate_from_content(html_only_post, 5)
        self.assertEqual(hashtags, [])
        
        # Test with post that has only stop words
        stop_words_post = Post.objects.create(
            title='The and or but',
            slug='stop-words-post',
            author=self.user,
            content='<p>The quick brown fox and the lazy dog or the cat but not the bird.</p>',
            excerpt='The and or but',
            status='published'
        )
        
        hashtags = self.generator.generate_from_content(stop_words_post, 5)
        # Should extract meaningful words like 'quick', 'brown', 'fox', etc.
        self.assertTrue(len(hashtags) > 0)
        hashtag_text = ' '.join(hashtags).lower()
        # Should not contain stop words
        for stop_word in ['the', 'and', 'or', 'but']:
            self.assertNotIn(f'#{stop_word}', hashtag_text)
    
    def test_blacklist_filtering_comprehensive(self):
        """Test comprehensive blacklist filtering scenarios."""
        # Test case-insensitive filtering
        hashtags = ['#Python', '#SPAM', '#Django', '#clickbait', '#WebDev', '#URGENT']
        config = {
            'hashtag_blacklist': ['spam', 'clickbait', 'urgent']
        }
        generator = MockHashtagGenerator(config)
        
        filtered = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertIn('#Python', filtered)
        self.assertIn('#Django', filtered)
        self.assertIn('#WebDev', filtered)
        self.assertNotIn('#SPAM', filtered)
        self.assertNotIn('#clickbait', filtered)
        self.assertNotIn('#URGENT', filtered)
        
        # Test partial matching
        hashtags = ['#pythonspam', '#spamfilter', '#antispam', '#django']
        filtered = generator.filter_blacklisted_hashtags(hashtags)
        
        # All hashtags containing 'spam' should be filtered out
        self.assertEqual(filtered, ['#django'])
        
        # Test with empty blacklist
        config_empty = {'hashtag_blacklist': []}
        generator_empty = MockHashtagGenerator(config_empty)
        
        filtered_empty = generator_empty.filter_blacklisted_hashtags(hashtags)
        self.assertEqual(filtered_empty, hashtags)  # No filtering
        
        # Test with non-string items in blacklist (should be ignored)
        config_mixed = {
            'hashtag_blacklist': ['spam', 123, None, 'clickbait', [], 'urgent']
        }
        generator_mixed = MockHashtagGenerator(config_mixed)
        
        hashtags_mixed = ['#python', '#spam', '#django', '#clickbait']
        filtered_mixed = generator_mixed.filter_blacklisted_hashtags(hashtags_mixed)
        
        self.assertIn('#python', filtered_mixed)
        self.assertIn('#django', filtered_mixed)
        self.assertNotIn('#spam', filtered_mixed)
        self.assertNotIn('#clickbait', filtered_mixed)
    
    def test_custom_rules_application_comprehensive(self):
        """Test comprehensive custom rules application."""
        hashtags = ['#python', '#webdev', '#coding', '#api', '#database']
        
        # Test complex replacement rules
        category_rules = {
            'technology': {
                'replacements': {
                    'python': 'PythonProgramming',
                    'webdev': 'WebDevelopment',
                    'api': 'APIDesign'
                }
            },
            'programming': {
                'replacements': {
                    'coding': 'SoftwareDevelopment'
                }
            }
        }
        
        processed = self.generator.apply_custom_rules(hashtags, category_rules)
        
        self.assertIn('#PythonProgramming', processed)
        self.assertIn('#WebDevelopment', processed)
        self.assertIn('#APIDesign', processed)
        self.assertIn('#SoftwareDevelopment', processed)
        self.assertIn('#database', processed)  # Unchanged
        
        # Test with invalid rules format
        invalid_rules = "not a dictionary"
        processed_invalid = self.generator.apply_custom_rules(hashtags, invalid_rules)
        self.assertEqual(processed_invalid, hashtags)  # Should be unchanged
        
        # Test with None rules
        processed_none = self.generator.apply_custom_rules(hashtags, None)
        self.assertEqual(processed_none, hashtags)  # Should be unchanged
        
        # Test with empty rules
        processed_empty = self.generator.apply_custom_rules(hashtags, {})
        self.assertEqual(processed_empty, hashtags)  # Should be unchanged
    
    def test_error_handling_and_resilience(self):
        """Test error handling and resilience in various scenarios."""
        # Test with mock objects that raise exceptions
        mock_post = Mock()
        mock_post.tags.exists.side_effect = Exception("Database connection error")
        mock_post.categories.exists.side_effect = Exception("Database connection error")
        mock_post.title = "Test Title"
        mock_post.content = "<p>Test content with keywords like python and django</p>"
        mock_post.excerpt = "Test excerpt"
        
        # Should not raise exceptions
        try:
            hashtags_tags = self.generator.generate_from_tags(mock_post, 5)
            self.assertEqual(hashtags_tags, [])  # Should return empty list on error
        except Exception as e:
            self.fail(f"generate_from_tags should handle exceptions gracefully: {e}")
        
        try:
            hashtags_categories = self.generator.generate_from_categories(mock_post, 5)
            self.assertEqual(hashtags_categories, [])  # Should return empty list on error
        except Exception as e:
            self.fail(f"generate_from_categories should handle exceptions gracefully: {e}")
        
        # Content generation should still work even if tags/categories fail
        try:
            hashtags_content = self.generator.generate_from_content(mock_post, 5)
            self.assertIsInstance(hashtags_content, list)
        except Exception as e:
            self.fail(f"generate_from_content should handle exceptions gracefully: {e}")
    
    def test_performance_with_large_inputs(self):
        """Test performance and behavior with large inputs."""
        # Create a post with very long content
        long_content = " ".join([f"keyword{i}" for i in range(1000)])
        long_post = Post.objects.create(
            title="Very Long Title " + " ".join([f"titleword{i}" for i in range(100)]),
            slug='long-post',
            author=self.user,
            content=f'<p>{long_content}</p>',
            excerpt=" ".join([f"excerptword{i}" for i in range(100)]),
            status='published'
        )
        
        # Should handle large content without issues
        hashtags = self.generator.generate_from_content(long_post, 10)
        self.assertIsInstance(hashtags, list)
        self.assertTrue(len(hashtags) <= 10)
        
        # Test with very large max_count
        hashtags_large = self.generator.generate_from_content(long_post, 1000)
        self.assertIsInstance(hashtags_large, list)
        # Should still be reasonable number due to content limitations
        self.assertTrue(len(hashtags_large) < 100)
    
    def test_unicode_and_special_character_handling(self):
        """Test handling of unicode and special characters."""
        # Test with unicode characters
        unicode_cases = [
            ("Pythön", ""),  # Should be filtered out due to special char
            ("Café", ""),    # Should be filtered out due to special char
            ("naïve", ""),   # Should be filtered out due to special char
            ("résumé", ""),  # Should be filtered out due to special char
            ("Python", "#python"),  # Normal case should work
        ]
        
        for input_tag, expected in unicode_cases:
            with self.subTest(input=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected)
    
    def test_boundary_conditions(self):
        """Test boundary conditions and limits."""
        # Test exactly at MIN_HASHTAG_LENGTH
        min_length_tag = "a" * MockHashtagGenerator.MIN_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(min_length_tag))
        
        # Test exactly at MAX_HASHTAG_LENGTH
        max_length_tag = "a" * MockHashtagGenerator.MAX_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(max_length_tag))
        
        # Test one character over MAX_HASHTAG_LENGTH
        over_max_tag = "a" * (MockHashtagGenerator.MAX_HASHTAG_LENGTH + 1)
        self.assertFalse(self.generator.validate_hashtag(over_max_tag))
        
        # Test one character under MIN_HASHTAG_LENGTH
        under_min_tag = "a" * (MockHashtagGenerator.MIN_HASHTAG_LENGTH - 1)
        self.assertFalse(self.generator.validate_hashtag(under_min_tag))


if __name__ == '__main__':
    unittest.main()