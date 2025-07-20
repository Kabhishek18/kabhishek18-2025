"""
Tests for the URLInfo class in the URL Discovery Service.
"""
from datetime import datetime
import unittest
from site_files.services.url_discovery import URLInfo


class URLInfoTestCase(unittest.TestCase):
    """Test case for the URLInfo class."""

    def setUp(self):
        """Set up test data."""
        self.site_url = "https://example.com"
        self.url_info = URLInfo(
            url="blog/post-1",
            lastmod=datetime(2023, 1, 1),
            changefreq="weekly",
            priority=0.8,
            title="Test Post",
            type="blog"
        )
        self.url_info_absolute = URLInfo(
            url="https://example.com/about",
            lastmod=datetime(2023, 1, 2),
            changefreq="monthly",
            priority=0.6,
            title="About Us",
            type="page"
        )

    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        # Test with relative URL
        self.assertEqual(
            self.url_info.get_absolute_url(self.site_url),
            "https://example.com/blog/post-1"
        )
        
        # Test with absolute URL
        self.assertEqual(
            self.url_info_absolute.get_absolute_url(self.site_url),
            "https://example.com/about"
        )
        
        # Test with trailing slash in site_url
        self.assertEqual(
            self.url_info.get_absolute_url(self.site_url + "/"),
            "https://example.com/blog/post-1"
        )
        
        # Test with leading slash in url
        url_info_with_slash = URLInfo(url="/blog/post-2")
        self.assertEqual(
            url_info_with_slash.get_absolute_url(self.site_url),
            "https://example.com/blog/post-2"
        )

    def test_to_dict(self):
        """Test the to_dict method."""
        expected_dict = {
            'url': 'blog/post-1',
            'lastmod': '2023-01-01T00:00:00',
            'changefreq': 'weekly',
            'priority': 0.8,
            'title': 'Test Post',
            'type': 'blog'
        }
        self.assertEqual(self.url_info.to_dict(), expected_dict)
        
        # Test without optional fields
        url_info_minimal = URLInfo(url="contact")
        expected_minimal_dict = {
            'url': 'contact',
            'changefreq': 'monthly',
            'priority': 0.5,
            'type': 'page'
        }
        self.assertEqual(url_info_minimal.to_dict(), expected_minimal_dict)

    def test_to_sitemap_element(self):
        """Test the to_sitemap_element method."""
        expected_xml = (
            '  <url>\n'
            '    <loc>https://example.com/blog/post-1</loc>\n'
            '    <lastmod>2023-01-01</lastmod>\n'
            '    <changefreq>weekly</changefreq>\n'
            '    <priority>0.8</priority>\n'
            '  </url>'
        )
        self.assertEqual(self.url_info.to_sitemap_element(self.site_url), expected_xml)
        
        # Test XML escaping
        url_info_with_special_chars = URLInfo(
            url="search?q=test&category=blog",
            lastmod=datetime(2023, 1, 3)
        )
        xml = url_info_with_special_chars.to_sitemap_element(self.site_url)
        self.assertIn("search?q=test&amp;category=blog", xml)

    def test_equality(self):
        """Test the equality comparison."""
        # Same URL should be equal
        url_info_same = URLInfo(
            url="blog/post-1",
            changefreq="daily",  # Different changefreq
            priority=0.9,  # Different priority
        )
        self.assertEqual(self.url_info, url_info_same)
        
        # Different URL should not be equal
        url_info_different = URLInfo(url="blog/post-2")
        self.assertNotEqual(self.url_info, url_info_different)
        
        # Non-URLInfo object should not be equal
        self.assertNotEqual(self.url_info, "blog/post-1")

    def test_hash(self):
        """Test the hash function."""
        # Same URL should have the same hash
        url_info_same = URLInfo(url="blog/post-1")
        self.assertEqual(hash(self.url_info), hash(url_info_same))
        
        # Different URL should have different hash
        url_info_different = URLInfo(url="blog/post-2")
        self.assertNotEqual(hash(self.url_info), hash(url_info_different))
        
        # Test in a set
        url_set = {self.url_info, url_info_same, url_info_different}
        self.assertEqual(len(url_set), 2)  # Only 2 unique URLs


if __name__ == '__main__':
    unittest.main()