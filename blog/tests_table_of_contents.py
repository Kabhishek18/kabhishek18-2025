"""
Tests for Table of Contents Service

This module contains tests for the table of contents functionality
including heading extraction, anchor generation, and TOC HTML generation.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Post, Category
from .services.table_of_contents_service import TableOfContentsService


class TableOfContentsServiceTest(TestCase):
    """Test cases for TableOfContentsService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Sample HTML content with headings
        self.sample_content = """
        <h1>Introduction</h1>
        <p>This is the introduction paragraph.</p>
        
        <h2>Main Section</h2>
        <p>This is the main section content.</p>
        
        <h3>Subsection A</h3>
        <p>Content for subsection A.</p>
        
        <h3>Subsection B</h3>
        <p>Content for subsection B.</p>
        
        <h2>Another Section</h2>
        <p>Another section content.</p>
        
        <h4>Deep Subsection</h4>
        <p>Deep subsection content.</p>
        """
        
        self.post = Post.objects.create(
            title='Test Post with TOC',
            slug='test-post-toc',
            author=self.user,
            content=self.sample_content,
            status='published',
            table_of_contents=True
        )
        self.post.categories.add(self.category)
    
    def test_extract_headings(self):
        """Test heading extraction from HTML content"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(self.sample_content, 'html.parser')
        headings = TableOfContentsService.extract_headings(soup)
        
        # Should extract 6 headings
        self.assertEqual(len(headings), 6)
        
        # Check heading texts
        expected_texts = [
            'Introduction',
            'Main Section', 
            'Subsection A',
            'Subsection B',
            'Another Section',
            'Deep Subsection'
        ]
        
        for i, heading in enumerate(headings):
            self.assertEqual(heading['text'], expected_texts[i])
        
        # Check heading levels
        expected_levels = [1, 2, 3, 3, 2, 4]
        for i, heading in enumerate(headings):
            self.assertEqual(heading['level'], expected_levels[i])
    
    def test_generate_unique_anchor(self):
        """Test unique anchor generation"""
        used_anchors = set()
        
        # Test basic anchor generation
        anchor1 = TableOfContentsService.generate_unique_anchor('Introduction', used_anchors)
        self.assertEqual(anchor1, 'introduction')
        used_anchors.add(anchor1)
        
        # Test duplicate handling
        anchor2 = TableOfContentsService.generate_unique_anchor('Introduction', used_anchors)
        self.assertEqual(anchor2, 'introduction-1')
        used_anchors.add(anchor2)
        
        # Test another duplicate
        anchor3 = TableOfContentsService.generate_unique_anchor('Introduction', used_anchors)
        self.assertEqual(anchor3, 'introduction-2')
        
        # Test special characters
        anchor4 = TableOfContentsService.generate_unique_anchor('Section with Special Characters!', used_anchors)
        self.assertEqual(anchor4, 'section-with-special-characters')
    
    def test_should_show_toc(self):
        """Test TOC visibility logic"""
        # Content with enough headings should show TOC
        self.assertTrue(TableOfContentsService.should_show_toc(self.sample_content))
        
        # Content with few headings should not show TOC
        short_content = "<h1>Only One Heading</h1><p>Some content</p>"
        self.assertFalse(TableOfContentsService.should_show_toc(short_content))
        
        # Empty content should not show TOC
        self.assertFalse(TableOfContentsService.should_show_toc(""))
        self.assertFalse(TableOfContentsService.should_show_toc(None))
    
    def test_generate_toc(self):
        """Test complete TOC generation"""
        toc_data = TableOfContentsService.generate_toc(self.sample_content)
        
        # Should show TOC for content with multiple headings
        self.assertTrue(toc_data['show_toc'])
        
        # Should have extracted headings
        self.assertEqual(len(toc_data['headings']), 6)
        
        # Content should be modified with anchor links
        self.assertIn('id="introduction"', toc_data['content'])
        self.assertIn('id="main-section"', toc_data['content'])
        
        # Should contain anchor links
        self.assertIn('class="heading-anchor"', toc_data['content'])
    
    def test_build_toc_html(self):
        """Test TOC HTML generation"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(self.sample_content, 'html.parser')
        headings = TableOfContentsService.extract_headings(soup)
        
        toc_html = TableOfContentsService.build_toc_html(headings)
        
        # Should contain TOC structure
        self.assertIn('class="table-of-contents"', toc_html)
        self.assertIn('class="toc-title"', toc_html)
        self.assertIn('class="toc-list"', toc_html)
        self.assertIn('class="toc-link"', toc_html)
        
        # Should contain all heading links
        self.assertIn('href="#introduction"', toc_html)
        self.assertIn('href="#main-section"', toc_html)
        self.assertIn('href="#subsection-a"', toc_html)
        
        # Should have proper heading levels
        self.assertIn('toc-level-1', toc_html)
        self.assertIn('toc-level-2', toc_html)
        self.assertIn('toc-level-3', toc_html)
    
    def test_generate_toc_data_for_template(self):
        """Test template data generation"""
        # Test with TOC enabled
        toc_data = TableOfContentsService.generate_toc_data_for_template(self.post)
        
        self.assertTrue(toc_data['show_toc'])
        self.assertIsNotNone(toc_data['toc_html'])
        self.assertEqual(len(toc_data['headings']), 6)
        self.assertIn('id="introduction"', toc_data['content'])
        
        # Test with TOC disabled
        self.post.table_of_contents = False
        self.post.save()
        
        toc_data_disabled = TableOfContentsService.generate_toc_data_for_template(self.post)
        
        self.assertFalse(toc_data_disabled['show_toc'])
        self.assertEqual(toc_data_disabled['toc_html'], '')
        self.assertEqual(len(toc_data_disabled['headings']), 0)
        self.assertEqual(toc_data_disabled['content'], self.post.content)
    
    def test_get_reading_time_by_sections(self):
        """Test section reading time calculation"""
        from bs4 import BeautifulSoup
        
        # Create content with more text for reading time calculation
        content_with_text = """
        <h1>Introduction</h1>
        <p>This is a longer introduction paragraph with more words to test reading time calculation. 
        It contains multiple sentences and should take some time to read. The reading time calculation 
        is based on average reading speed of 200 words per minute.</p>
        
        <h2>Main Section</h2>
        <p>This main section also contains substantial content for testing purposes. It has detailed 
        explanations and examples that would require more reading time. The algorithm should calculate 
        different reading times for different sections based on their content length.</p>
        """
        
        soup = BeautifulSoup(content_with_text, 'html.parser')
        headings = TableOfContentsService.extract_headings(soup)
        
        section_times = TableOfContentsService.get_reading_time_by_sections(content_with_text, headings)
        
        # Should return reading times for each section
        self.assertIn('introduction', section_times)
        self.assertIn('main-section', section_times)
        
        # Reading times should be positive integers
        for anchor, time in section_times.items():
            self.assertIsInstance(time, int)
            self.assertGreater(time, 0)
    
    def test_empty_content_handling(self):
        """Test handling of empty or invalid content"""
        # Empty content
        toc_data = TableOfContentsService.generate_toc("")
        self.assertFalse(toc_data['show_toc'])
        self.assertEqual(len(toc_data['headings']), 0)
        
        # None content
        toc_data = TableOfContentsService.generate_toc(None)
        self.assertFalse(toc_data['show_toc'])
        self.assertEqual(len(toc_data['headings']), 0)
        
        # Content without headings
        no_headings = "<p>Just a paragraph without any headings.</p>"
        toc_data = TableOfContentsService.generate_toc(no_headings)
        self.assertFalse(toc_data['show_toc'])
        self.assertEqual(len(toc_data['headings']), 0)
    
    def test_complex_heading_content(self):
        """Test handling of complex heading content"""
        complex_content = """
        <h1>Heading with <strong>Bold</strong> and <em>Italic</em> Text</h1>
        <h2>Heading with <a href="#">Link</a></h2>
        <h3>Heading with Special Characters: @#$%^&*()</h3>
        <h4>Very Long Heading That Contains Many Words And Should Still Work Properly</h4>
        """
        
        toc_data = TableOfContentsService.generate_toc(complex_content)
        
        # Should extract text content from complex headings
        headings = toc_data['headings']
        self.assertEqual(len(headings), 4)
        
        # Should strip HTML tags from heading text
        self.assertEqual(headings[0]['text'], 'Heading with Bold and Italic Text')
        self.assertEqual(headings[1]['text'], 'Heading with Link')
        
        # Should handle special characters in anchors
        self.assertIn('special-characters', headings[2]['anchor'])
        
        # Should handle long headings
        self.assertIn('very-long-heading', headings[3]['anchor'])


class TableOfContentsIntegrationTest(TestCase):
    """Integration tests for TOC with Django views"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Read test content from file
        try:
            with open('test_toc_content.html', 'r') as f:
                test_content = f.read()
        except FileNotFoundError:
            # Fallback content if file doesn't exist
            test_content = """
            <h1>Test Heading 1</h1>
            <p>Content 1</p>
            <h2>Test Heading 2</h2>
            <p>Content 2</p>
            <h3>Test Heading 3</h3>
            <p>Content 3</p>
            """
        
        self.post = Post.objects.create(
            title='Integration Test Post',
            slug='integration-test-post',
            author=self.user,
            content=test_content,
            status='published',
            table_of_contents=True
        )
    
    def test_blog_detail_view_with_toc(self):
        """Test that blog detail view includes TOC data"""
        from django.test import Client
        from django.urls import reverse
        
        client = Client()
        url = reverse('blog:detail', kwargs={'slug': self.post.slug})
        response = client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that TOC data is in context
        self.assertIn('toc_data', response.context)
        
        toc_data = response.context['toc_data']
        
        # Should show TOC for post with multiple headings
        self.assertTrue(toc_data['show_toc'])
        self.assertGreater(len(toc_data['headings']), 0)
        
        # Response should contain TOC HTML
        self.assertContains(response, 'table-of-contents')
        self.assertContains(response, 'toc-title')
        self.assertContains(response, 'toc-link')
    
    def test_blog_detail_view_without_toc(self):
        """Test blog detail view when TOC is disabled"""
        from django.test import Client
        from django.urls import reverse
        
        # Disable TOC for this post
        self.post.table_of_contents = False
        self.post.save()
        
        client = Client()
        url = reverse('blog:detail', kwargs={'slug': self.post.slug})
        response = client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that TOC data indicates no TOC
        toc_data = response.context['toc_data']
        self.assertFalse(toc_data['show_toc'])
        
        # Response should not contain TOC HTML
        self.assertNotContains(response, 'table-of-contents')
        self.assertNotContains(response, 'toc-title')