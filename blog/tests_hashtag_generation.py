"""
Comprehensive unit tests for HashtagGenerator class.

Tests hashtag generation from tags, categories, and content with various input scenarios,
custom hashtag rules application, blacklist filtering, and hashtag validation/formatting edge cases.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth.models import User

from blog.models import Post, Tag, Category
from blog.services.linkedin_content_formatter import HashtagGenerator


class HashtagGeneratorTest(TestCase):
    """Test cases for HashtagGenerator class methods with various input scenarios."""
    
    def setUp(self):
        """Set up test data for hashtag generation tests."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test tags
        self.tag_python = Tag.objects.create(name='Python', slug='python')
        self.tag_django = Tag.objects.create(name='Django Framework', slug='django-framework')
        self.tag_web_dev = Tag.objects.create(name='Web Development', slug='web-development')
        self.tag_api = Tag.objects.create(name='API Design', slug='api-design')
        self.tag_testing = Tag.objects.create(name='Testing', slug='testing')
        self.tag_devops = Tag.objects.create(name='DevOps', slug='devops')
        self.tag_machine_learning = Tag.objects.create(name='Machine Learning', slug='machine-learning')
        
        # Create test categories
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        self.category_news = Category.objects.create(name='News', slug='news')
        
        # Create test posts
        self.post_with_tags = Post.objects.create(
            title='Python Django Tutorial for Beginners',
            slug='python-django-tutorial',
            author=self.user,
            content='<p>This is a comprehensive tutorial about Python and Django development. Learn how to build web applications with Django framework.</p>',
            excerpt='Learn Python Django development',
            status='published'
        )
        self.post_with_tags.tags.add(self.tag_python, self.tag_django, self.tag_web_dev)
        self.post_with_tags.categories.add(self.category_tech, self.category_tutorial)
        
        self.post_no_tags = Post.objects.create(
            title='General Blog Post',
            slug='general-blog-post',
            author=self.user,
            content='<p>This is a general blog post without specific tags.</p>',
            excerpt='General content',
            status='published'
        )
        self.post_no_tags.categories.add(self.category_news)
        
        self.post_many_tags = Post.objects.create(
            title='Comprehensive Development Guide',
            slug='comprehensive-dev-guide',
            author=self.user,
            content='<p>This post covers Python, Django, API design, testing, DevOps, and machine learning.</p>',
            excerpt='Complete development guide',
            status='published'
        )
        self.post_many_tags.tags.add(
            self.tag_python, self.tag_django, self.tag_web_dev, 
            self.tag_api, self.tag_testing, self.tag_devops, self.tag_machine_learning
        )
        self.post_many_tags.categories.add(self.category_tech, self.category_tutorial)
    
    def test_hashtag_generator_initialization_with_dict_config(self):
        """Test HashtagGenerator initialization with dictionary configuration."""
        config = {
            'enable_hashtags': True,
            'max_hashtags': 3,
            'custom_hashtag_rules': {'tech': ['#TechTips']},
            'hashtag_blacklist': ['spam', 'clickbait']
        }
        
        generator = HashtagGenerator(config)
        
        self.assertEqual(generator.config['enable_hashtags'], True)
        self.assertEqual(generator.config['max_hashtags'], 3)
        self.assertEqual(generator.config['custom_hashtag_rules'], {'tech': ['#TechTips']})
        self.assertEqual(generator.config['hashtag_blacklist'], ['spam', 'clickbait'])
    
    def test_hashtag_generator_initialization_with_mock_linkedin_config(self):
        """Test HashtagGenerator initialization with mock LinkedInConfig instance."""
        mock_config = Mock()
        mock_config.get_hashtag_config.return_value = {
            'enable_hashtags': False,
            'max_hashtags': 7,
            'custom_hashtag_rules': {},
            'hashtag_blacklist': []
        }
        
        generator = HashtagGenerator(mock_config)
        
        self.assertEqual(generator.config['enable_hashtags'], False)
        self.assertEqual(generator.config['max_hashtags'], 7)
    
    def test_hashtag_generator_initialization_with_none_config(self):
        """Test HashtagGenerator initialization with None configuration (uses defaults)."""
        generator = HashtagGenerator(None)
        
        self.assertEqual(generator.config['enable_hashtags'], True)
        self.assertEqual(generator.config['max_hashtags'], HashtagGenerator.DEFAULT_MAX_HASHTAGS)
        self.assertEqual(generator.config['custom_hashtag_rules'], {})
        self.assertEqual(generator.config['hashtag_blacklist'], [])
    
    def test_generate_hashtags_disabled(self):
        """Test hashtag generation when hashtags are disabled in configuration."""
        config = {'enable_hashtags': False}
        generator = HashtagGenerator(config)
        
        hashtags = generator.generate_hashtags(self.post_with_tags)
        
        self.assertEqual(hashtags, [])
    
    def test_generate_hashtags_zero_max_count(self):
        """Test hashtag generation with zero max count."""
        config = {'enable_hashtags': True, 'max_hashtags': 0}
        generator = HashtagGenerator(config)
        
        hashtags = generator.generate_hashtags(self.post_with_tags)
        
        self.assertEqual(hashtags, [])
    
    def test_generate_hashtags_from_tags_normal_case(self):
        """Test hashtag generation from blog post tags - normal case."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_tags(self.post_with_tags, 5)
        
        self.assertIn('#python', hashtags)
        self.assertIn('#djangoFramework', hashtags)
        self.assertIn('#webDevelopment', hashtags)
        self.assertEqual(len(hashtags), 3)  # Post has 3 tags
    
    def test_generate_hashtags_from_tags_with_max_count_limit(self):
        """Test hashtag generation from tags with max count limit."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_tags(self.post_many_tags, 3)
        
        self.assertEqual(len(hashtags), 3)  # Should be limited to 3
        # Should contain valid hashtags
        for hashtag in hashtags:
            self.assertTrue(hashtag.startswith('#'))
            self.assertTrue(generator.validate_hashtag(hashtag))
    
    def test_generate_hashtags_from_tags_no_tags(self):
        """Test hashtag generation from post with no tags."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_tags(self.post_no_tags, 5)
        
        self.assertEqual(hashtags, [])
    
    def test_generate_hashtags_from_tags_zero_max_count(self):
        """Test hashtag generation from tags with zero max count."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_tags(self.post_with_tags, 0)
        
        self.assertEqual(hashtags, [])
    
    def test_generate_hashtags_from_categories_normal_case(self):
        """Test hashtag generation from blog post categories - normal case."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_categories(self.post_with_tags, 5)
        
        self.assertIn('#technology', hashtags)
        self.assertIn('#tutorial', hashtags)
        self.assertEqual(len(hashtags), 2)  # Post has 2 categories
    
    def test_generate_hashtags_from_categories_with_max_count_limit(self):
        """Test hashtag generation from categories with max count limit."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_categories(self.post_with_tags, 1)
        
        self.assertEqual(len(hashtags), 1)  # Should be limited to 1
        self.assertTrue(hashtags[0] in ['#technology', '#tutorial'])
    
    def test_generate_hashtags_from_categories_no_categories(self):
        """Test hashtag generation from post with no categories."""
        post_no_categories = Post.objects.create(
            title='Post Without Categories',
            slug='post-no-categories',
            author=self.user,
            content='Content without categories',
            status='published'
        )
        
        generator = HashtagGenerator()
        hashtags = generator.generate_from_categories(post_no_categories, 5)
        
        self.assertEqual(hashtags, [])
    
    def test_generate_hashtags_from_content_with_title_and_excerpt(self):
        """Test hashtag generation from post content including title and excerpt."""
        generator = HashtagGenerator()
        
        hashtags = generator.generate_from_content(self.post_with_tags, 5)
        
        # Should extract keywords from title and excerpt
        self.assertTrue(len(hashtags) > 0)
        # Should contain relevant keywords as hashtags
        hashtag_text = ' '.join(hashtags).lower()
        self.assertTrue(any(keyword in hashtag_text for keyword in ['python', 'django', 'tutorial', 'development']))
    
    def test_generate_hashtags_from_content_no_excerpt_uses_content(self):
        """Test hashtag generation from content when no excerpt is available."""
        post_no_excerpt = Post.objects.create(
            title='Machine Learning Algorithms',
            slug='ml-algorithms',
            author=self.user,
            content='<p>Machine learning algorithms are powerful tools for data analysis and prediction. Python provides excellent libraries for implementing these algorithms.</p>',
            excerpt='',  # No excerpt
            status='published'
        )
        
        generator = HashtagGenerator()
        hashtags = generator.generate_from_content(post_no_excerpt, 5)
        
        # Should extract from content
        self.assertTrue(len(hashtags) > 0)
        hashtag_text = ' '.join(hashtags).lower()
        self.assertTrue(any(keyword in hashtag_text for keyword in ['machine', 'learning', 'algorithms', 'python']))
    
    def test_generate_hashtags_from_content_empty_content(self):
        """Test hashtag generation from empty content."""
        post_empty = Post.objects.create(
            title='',
            slug='empty-post',
            author=self.user,
            content='',
            excerpt='',
            status='published'
        )
        
        generator = HashtagGenerator()
        hashtags = generator.generate_from_content(post_empty, 5)
        
        self.assertEqual(hashtags, [])
    
    def test_extract_keywords_from_text_normal_case(self):
        """Test keyword extraction from text content."""
        generator = HashtagGenerator()
        text = "Python programming is great for web development and machine learning applications"
        
        hashtags = generator._extract_keywords_from_text(text, 3)
        
        self.assertTrue(len(hashtags) <= 3)
        # Should filter out stop words and extract meaningful keywords
        hashtag_text = ' '.join(hashtags).lower()
        self.assertFalse(any(stop_word in hashtag_text for stop_word in ['is', 'for', 'and']))
        self.assertTrue(any(keyword in hashtag_text for keyword in ['python', 'programming', 'development']))
    
    def test_extract_keywords_from_text_with_stop_words(self):
        """Test keyword extraction filters out stop words."""
        generator = HashtagGenerator()
        text = "The quick brown fox jumps over the lazy dog and runs through the forest"
        
        hashtags = generator._extract_keywords_from_text(text, 5)
        
        # Should not contain stop words
        hashtag_text = ' '.join(hashtags).lower()
        stop_words = ['the', 'and', 'over', 'through']
        for stop_word in stop_words:
            self.assertNotIn(f'#{stop_word}', hashtag_text)
    
    def test_extract_keywords_from_text_with_numbers_and_special_chars(self):
        """Test keyword extraction handles numbers and special characters."""
        generator = HashtagGenerator()
        text = "Python 3.9 is great! API-design and web-development are important skills."
        
        hashtags = generator._extract_keywords_from_text(text, 5)
        
        # Should extract meaningful words, not pure numbers
        for hashtag in hashtags:
            clean_hashtag = hashtag.lstrip('#')
            self.assertFalse(clean_hashtag.isdigit())
            self.assertTrue(clean_hashtag.isalpha())
    
    def test_get_custom_hashtags_for_post_with_required_hashtags(self):
        """Test custom hashtag retrieval with required hashtags configuration."""
        config = {
            'custom_hashtag_rules': {
                'technology': {
                    'required_hashtags': ['#TechTips', '#Innovation'],
                    'suggested_hashtags': ['#Programming', '#Development']
                }
            }
        }
        generator = HashtagGenerator(config)
        
        custom_hashtags = generator._get_custom_hashtags_for_post(self.post_with_tags)
        
        self.assertIn('#TechTips', custom_hashtags)
        self.assertIn('#Innovation', custom_hashtags)
        self.assertIn('#Programming', custom_hashtags)
        self.assertIn('#Development', custom_hashtags)
    
    def test_get_custom_hashtags_for_post_with_simple_list_format(self):
        """Test custom hashtag retrieval with simple list format."""
        config = {
            'custom_hashtag_rules': {
                'tutorial': ['#HowTo', '#Learning', '#Education']
            }
        }
        generator = HashtagGenerator(config)
        
        custom_hashtags = generator._get_custom_hashtags_for_post(self.post_with_tags)
        
        self.assertIn('#HowTo', custom_hashtags)
        self.assertIn('#Learning', custom_hashtags)
        self.assertIn('#Education', custom_hashtags)
    
    def test_get_custom_hashtags_for_post_no_matching_categories(self):
        """Test custom hashtag retrieval when no categories match rules."""
        config = {
            'custom_hashtag_rules': {
                'nonexistent': ['#Test']
            }
        }
        generator = HashtagGenerator(config)
        
        custom_hashtags = generator._get_custom_hashtags_for_post(self.post_with_tags)
        
        self.assertEqual(custom_hashtags, [])
    
    def test_get_custom_hashtags_for_post_no_categories(self):
        """Test custom hashtag retrieval for post with no categories."""
        post_no_categories = Post.objects.create(
            title='Post Without Categories',
            slug='post-no-categories',
            author=self.user,
            content='Content',
            status='published'
        )
        
        config = {
            'custom_hashtag_rules': {
                'technology': ['#TechTips']
            }
        }
        generator = HashtagGenerator(config)
        
        custom_hashtags = generator._get_custom_hashtags_for_post(post_no_categories)
        
        self.assertEqual(custom_hashtags, [])
    
    def test_apply_custom_rules_with_replacements(self):
        """Test custom rules application with hashtag replacements."""
        hashtags = ['#python', '#webdev', '#coding']
        category_rules = {
            'technology': {
                'replacements': {
                    'python': 'PythonProgramming',
                    'webdev': 'WebDevelopment'
                }
            }
        }
        generator = HashtagGenerator()
        
        processed_hashtags = generator.apply_custom_rules(hashtags, category_rules)
        
        self.assertIn('#PythonProgramming', processed_hashtags)
        self.assertIn('#WebDevelopment', processed_hashtags)
        self.assertIn('#coding', processed_hashtags)  # Unchanged
    
    def test_apply_custom_rules_no_rules(self):
        """Test custom rules application with no rules provided."""
        hashtags = ['#python', '#django', '#webdev']
        generator = HashtagGenerator()
        
        processed_hashtags = generator.apply_custom_rules(hashtags, None)
        
        self.assertEqual(processed_hashtags, hashtags)  # Should be unchanged
    
    def test_apply_custom_rules_invalid_rules_format(self):
        """Test custom rules application with invalid rules format."""
        hashtags = ['#python', '#django']
        invalid_rules = "not a dictionary"
        generator = HashtagGenerator()
        
        processed_hashtags = generator.apply_custom_rules(hashtags, invalid_rules)
        
        self.assertEqual(processed_hashtags, hashtags)  # Should be unchanged
    
    def test_filter_blacklisted_hashtags_normal_case(self):
        """Test blacklist filtering removes blacklisted terms."""
        hashtags = ['#python', '#spam', '#django', '#clickbait', '#webdev']
        config = {
            'hashtag_blacklist': ['spam', 'clickbait', 'urgent']
        }
        generator = HashtagGenerator(config)
        
        filtered_hashtags = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertIn('#python', filtered_hashtags)
        self.assertIn('#django', filtered_hashtags)
        self.assertIn('#webdev', filtered_hashtags)
        self.assertNotIn('#spam', filtered_hashtags)
        self.assertNotIn('#clickbait', filtered_hashtags)
    
    def test_filter_blacklisted_hashtags_case_insensitive(self):
        """Test blacklist filtering is case insensitive."""
        hashtags = ['#Python', '#SPAM', '#Django', '#ClickBait']
        config = {
            'hashtag_blacklist': ['spam', 'clickbait']
        }
        generator = HashtagGenerator(config)
        
        filtered_hashtags = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertIn('#Python', filtered_hashtags)
        self.assertIn('#Django', filtered_hashtags)
        self.assertNotIn('#SPAM', filtered_hashtags)
        self.assertNotIn('#ClickBait', filtered_hashtags)
    
    def test_filter_blacklisted_hashtags_partial_match(self):
        """Test blacklist filtering with partial term matching."""
        hashtags = ['#pythonspam', '#spamfilter', '#django']
        config = {
            'hashtag_blacklist': ['spam']
        }
        generator = HashtagGenerator(config)
        
        filtered_hashtags = generator.filter_blacklisted_hashtags(hashtags)
        
        # Should filter out hashtags containing blacklisted terms
        self.assertNotIn('#pythonspam', filtered_hashtags)
        self.assertNotIn('#spamfilter', filtered_hashtags)
        self.assertIn('#django', filtered_hashtags)
    
    def test_filter_blacklisted_hashtags_empty_blacklist(self):
        """Test blacklist filtering with empty blacklist."""
        hashtags = ['#python', '#django', '#webdev']
        config = {
            'hashtag_blacklist': []
        }
        generator = HashtagGenerator(config)
        
        filtered_hashtags = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertEqual(filtered_hashtags, hashtags)  # Should be unchanged
    
    def test_filter_blacklisted_hashtags_no_blacklist_config(self):
        """Test blacklist filtering when no blacklist is configured."""
        hashtags = ['#python', '#django', '#webdev']
        generator = HashtagGenerator()  # No blacklist in default config
        
        filtered_hashtags = generator.filter_blacklisted_hashtags(hashtags)
        
        self.assertEqual(filtered_hashtags, hashtags)  # Should be unchanged


class HashtagValidationTest(TestCase):
    """Test cases for hashtag validation and formatting edge cases."""
    
    def setUp(self):
        """Set up test data for validation tests."""
        self.generator = HashtagGenerator()
    
    def test_validate_hashtag_valid_cases(self):
        """Test hashtag validation with valid hashtags."""
        valid_hashtags = [
            'python',
            '#python',
            'webDevelopment',
            '#webDevelopment',
            'api2',
            '#api2',
            'test123',
            'a' * 50,  # Medium length
        ]
        
        for hashtag in valid_hashtags:
            with self.subTest(hashtag=hashtag):
                self.assertTrue(self.generator.validate_hashtag(hashtag))
    
    def test_validate_hashtag_invalid_cases(self):
        """Test hashtag validation with invalid hashtags."""
        invalid_hashtags = [
            '',  # Empty
            None,  # None
            123,  # Not a string
            '123',  # All numbers
            '#123',  # All numbers with #
            'a',  # Too short
            'a' * 101,  # Too long
            '#a' * 101,  # Too long with #
            'test-hashtag',  # Contains hyphen
            'test hashtag',  # Contains space
            'test@hashtag',  # Contains special character
            '1python',  # Starts with number
            '#1python',  # Starts with number with #
        ]
        
        for hashtag in invalid_hashtags:
            with self.subTest(hashtag=hashtag):
                self.assertFalse(self.generator.validate_hashtag(hashtag))
    
    def test_validate_hashtag_boundary_lengths(self):
        """Test hashtag validation at boundary lengths."""
        # Minimum valid length
        min_valid = 'a' * HashtagGenerator.MIN_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(min_valid))
        
        # Just below minimum
        too_short = 'a' * (HashtagGenerator.MIN_HASHTAG_LENGTH - 1)
        self.assertFalse(self.generator.validate_hashtag(too_short))
        
        # Maximum valid length
        max_valid = 'a' * HashtagGenerator.MAX_HASHTAG_LENGTH
        self.assertTrue(self.generator.validate_hashtag(max_valid))
        
        # Just above maximum
        too_long = 'a' * (HashtagGenerator.MAX_HASHTAG_LENGTH + 1)
        self.assertFalse(self.generator.validate_hashtag(too_long))
    
    def test_format_hashtag_normal_cases(self):
        """Test hashtag formatting with normal input cases."""
        test_cases = [
            ('Python', '#python'),
            ('Web Development', '#webDevelopment'),
            ('API Design', '#apiDesign'),
            ('machine learning', '#machineLearning'),
            ('DJANGO FRAMEWORK', '#djangoFramework'),
            ('Test123', '#test123'),
        ]
        
        for input_tag, expected_output in test_cases:
            with self.subTest(input_tag=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_format_hashtag_with_existing_hash(self):
        """Test hashtag formatting when input already has # prefix."""
        test_cases = [
            ('#Python', '#python'),
            ('#Web Development', '#webDevelopment'),
            ('#API-Design', '#apiDesign'),
        ]
        
        for input_tag, expected_output in test_cases:
            with self.subTest(input_tag=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_format_hashtag_with_special_characters(self):
        """Test hashtag formatting removes special characters."""
        test_cases = [
            ('Python!', '#python'),
            ('Web-Development', '#webDevelopment'),
            ('API@Design', '#apiDesign'),
            ('Test & Debug', '#testDebug'),
            ('C++', '#c'),
            ('Node.js', '#nodejs'),
        ]
        
        for input_tag, expected_output in test_cases:
            with self.subTest(input_tag=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_format_hashtag_edge_cases(self):
        """Test hashtag formatting with edge cases."""
        edge_cases = [
            ('', ''),  # Empty string
            (None, ''),  # None input
            ('   ', ''),  # Only whitespace
            ('123', ''),  # Only numbers
            ('!@#$%', ''),  # Only special characters
            ('   Python   ', '#python'),  # Extra whitespace
            ('Multiple   Spaces   Between', '#multipleSpacesBetween'),  # Multiple spaces
        ]
        
        for input_tag, expected_output in edge_cases:
            with self.subTest(input_tag=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_format_hashtag_camel_case_conversion(self):
        """Test hashtag formatting converts to proper camelCase."""
        test_cases = [
            ('single', '#single'),
            ('Two Words', '#twoWords'),
            ('three word phrase', '#threeWordPhrase'),
            ('FOUR WORD UPPER CASE', '#fourWordUpperCase'),
            ('mixed Case INPUT', '#mixedCaseInput'),
        ]
        
        for input_tag, expected_output in test_cases:
            with self.subTest(input_tag=input_tag):
                result = self.generator.format_hashtag(input_tag)
                self.assertEqual(result, expected_output)
    
    def test_prioritize_hashtags_default_sorting(self):
        """Test hashtag prioritization with default sorting (length then alphabetical)."""
        hashtags = ['#webDevelopment', '#api', '#python', '#machineLearning', '#test']
        
        prioritized = self.generator.prioritize_hashtags(hashtags)
        
        # Should be sorted by length first, then alphabetically
        expected_order = ['#api', '#test', '#python', '#machineLearning', '#webDevelopment']
        self.assertEqual(prioritized, expected_order)
    
    def test_prioritize_hashtags_with_custom_rules(self):
        """Test hashtag prioritization with custom priority rules."""
        hashtags = ['#python', '#django', '#webdev', '#api']
        priority_rules = {
            'python': 1,  # Highest priority
            'api': 2,
            'django': 3,
            'webdev': 4   # Lowest priority
        }
        
        prioritized = self.generator.prioritize_hashtags(hashtags, priority_rules)
        
        expected_order = ['#python', '#api', '#django', '#webdev']
        self.assertEqual(prioritized, expected_order)
    
    def test_prioritize_hashtags_with_pattern_based_rules(self):
        """Test hashtag prioritization with pattern-based priority rules."""
        hashtags = ['#pythonTips', '#webDevelopment', '#apiDesign', '#testing']
        priority_rules = {
            'python': 1,  # Should match #pythonTips
            'api': 2,     # Should match #apiDesign
        }
        
        prioritized = self.generator.prioritize_hashtags(hashtags, priority_rules)
        
        # Items with patterns should come first
        self.assertEqual(prioritized[0], '#pythonTips')  # Contains 'python'
        self.assertEqual(prioritized[1], '#apiDesign')   # Contains 'api'
    
    def test_prioritize_hashtags_empty_list(self):
        """Test hashtag prioritization with empty hashtag list."""
        prioritized = self.generator.prioritize_hashtags([])
        
        self.assertEqual(prioritized, [])
    
    def test_prioritize_hashtags_single_hashtag(self):
        """Test hashtag prioritization with single hashtag."""
        hashtags = ['#python']
        
        prioritized = self.generator.prioritize_hashtags(hashtags)
        
        self.assertEqual(prioritized, ['#python'])


class HashtagGenerationIntegrationTest(TestCase):
    """Integration tests for complete hashtag generation workflow."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create comprehensive test data
        self.tag_python = Tag.objects.create(name='Python', slug='python')
        self.tag_django = Tag.objects.create(name='Django', slug='django')
        self.tag_spam = Tag.objects.create(name='Spam Content', slug='spam-content')
        
        self.category_tech = Category.objects.create(name='Technology', slug='technology')
        self.category_tutorial = Category.objects.create(name='Tutorial', slug='tutorial')
        
        self.post = Post.objects.create(
            title='Advanced Python Django Development Tutorial',
            slug='python-django-tutorial',
            author=self.user,
            content='<p>Learn advanced Python programming techniques and Django framework development. This comprehensive tutorial covers web development, API design, and best practices.</p>',
            excerpt='Master Python Django development with this comprehensive tutorial',
            status='published'
        )
        self.post.tags.add(self.tag_python, self.tag_django, self.tag_spam)
        self.post.categories.add(self.category_tech, self.category_tutorial)
    
    def test_complete_hashtag_generation_workflow(self):
        """Test complete hashtag generation workflow with all sources."""
        config = {
            'enable_hashtags': True,
            'max_hashtags': 5,
            'custom_hashtag_rules': {
                'technology': {
                    'required_hashtags': ['#TechTips'],
                    'suggested_hashtags': ['#Innovation']
                }
            },
            'hashtag_blacklist': ['spam']
        }
        generator = HashtagGenerator(config)
        
        hashtags = generator.generate_hashtags(self.post)
        
        # Should include custom hashtags
        self.assertIn('#TechTips', hashtags)
        
        # Should include hashtags from tags (but not blacklisted ones)
        self.assertIn('#python', hashtags)
        self.assertIn('#django', hashtags)
        self.assertNotIn('#spamContent', hashtags)  # Should be filtered out
        
        # Should not exceed max count
        self.assertLessEqual(len(hashtags), 5)
        
        # All hashtags should be valid
        for hashtag in hashtags:
            self.assertTrue(generator.validate_hashtag(hashtag))
    
    def test_hashtag_generation_priority_order(self):
        """Test that hashtag generation follows correct priority order."""
        config = {
            'enable_hashtags': True,
            'max_hashtags': 3,  # Limited to test priority
            'custom_hashtag_rules': {
                'technology': ['#TechTips', '#Innovation']  # Highest priority
            },
            'hashtag_blacklist': []
        }
        generator = HashtagGenerator(config)
        
        hashtags = generator.generate_hashtags(self.post)
        
        # Should prioritize custom hashtags first
        self.assertIn('#TechTips', hashtags)
        self.assertIn('#Innovation', hashtags)
        
        # Should have exactly max_hashtags
        self.assertEqual(len(hashtags), 3)
    
    def test_hashtag_generation_fallback_behavior(self):
        """Test hashtag generation fallback when primary sources are unavailable."""
        # Create post with no tags or categories
        post_minimal = Post.objects.create(
            title='Machine Learning Algorithms and Data Science',
            slug='ml-algorithms',
            author=self.user,
            content='<p>Explore machine learning algorithms, data science techniques, and artificial intelligence applications in modern software development.</p>',
            excerpt='',
            status='published'
        )
        
        generator = HashtagGenerator()
        hashtags = generator.generate_hashtags(post_minimal)
        
        # Should generate hashtags from content
        self.assertTrue(len(hashtags) > 0)
        
        # Should contain relevant keywords from title/content
        hashtag_text = ' '.join(hashtags).lower()
        self.assertTrue(any(keyword in hashtag_text for keyword in ['machine', 'learning', 'data', 'science']))
    
    def test_hashtag_generation_with_duplicate_removal(self):
        """Test that hashtag generation removes duplicates while preserving order."""
        config = {
            'enable_hashtags': True,
            'max_hashtags': 10,
            'custom_hashtag_rules': {
                'technology': ['#Python', '#Development'],  # Duplicates with tags
                'tutorial': ['#Learning']
            },
            'hashtag_blacklist': []
        }
        generator = HashtagGenerator(config)
        
        hashtags = generator.generate_hashtags(self.post)
        
        # Should not have duplicates
        self.assertEqual(len(hashtags), len(set(h.lower() for h in hashtags)))
        
        # Should contain Python only once (case-insensitive)
        python_count = sum(1 for h in hashtags if 'python' in h.lower())
        self.assertEqual(python_count, 1)
    
    def test_hashtag_generation_error_handling(self):
        """Test hashtag generation handles errors gracefully."""
        # Test with mock post that might cause errors
        mock_post = Mock()
        mock_post.tags.exists.side_effect = Exception("Database error")
        mock_post.categories.exists.side_effect = Exception("Database error")
        mock_post.title = "Test Title"
        mock_post.content = "Test content"
        mock_post.excerpt = "Test excerpt"
        
        generator = HashtagGenerator()
        
        # Should not raise exception, should return empty list or fallback
        try:
            hashtags = generator.generate_hashtags(mock_post)
            # Should either return empty list or hashtags from content
            self.assertIsInstance(hashtags, list)
        except Exception:
            self.fail("Hashtag generation should handle errors gracefully")


if __name__ == '__main__':
    unittest.main()