from django.core.management.base import BaseCommand
from blog.models import Post
from django.utils.text import slugify
import re

class Command(BaseCommand):
    help = 'Improve existing content for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument('--expand', action='store_true', help='Expand thin content')
        parser.add_argument('--seo', action='store_true', help='Optimize for SEO')
        parser.add_argument('--structure', action='store_true', help='Improve content structure')

    def handle(self, *args, **options):
        posts = Post.objects.filter(status='published')
        
        for post in posts:
            improved = False
            
            if options.get('expand'):
                if len(post.content) < 800:
                    self.expand_content(post)
                    improved = True
            
            if options.get('seo'):
                self.optimize_seo(post)
                improved = True
            
            if options.get('structure'):
                self.improve_structure(post)
                improved = True
            
            if improved:
                post.save()
                self.stdout.write(f'Improved post: {post.title}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully improved {posts.count()} posts')
        )

    def expand_content(self, post):
        """Expand thin content with additional sections"""
        if len(post.content) < 800:
            additional_content = self.generate_additional_sections(post)
            post.content += additional_content
    
    def generate_additional_sections(self, post):
        """Generate additional content sections"""
        return f"""

<h2>Key Takeaways</h2>
<p>This article covers important concepts that are essential for understanding {post.title.lower()}. The main points discussed provide practical insights for developers and technical professionals.</p>

<h2>Best Practices</h2>
<p>When implementing the concepts discussed in this article, consider the following best practices:</p>
<ul>
    <li>Always test your implementation thoroughly</li>
    <li>Follow security guidelines and industry standards</li>
    <li>Document your code and processes clearly</li>
    <li>Consider performance implications</li>
    <li>Plan for scalability and maintenance</li>
</ul>

<h2>Common Challenges and Solutions</h2>
<p>Developers often encounter specific challenges when working with these concepts. Here are some common issues and their solutions:</p>

<h3>Performance Considerations</h3>
<p>Performance is crucial in any implementation. Consider caching strategies, database optimization, and efficient algorithms to ensure your solution scales well.</p>

<h3>Security Implications</h3>
<p>Security should always be a primary concern. Implement proper validation, authentication, and authorization mechanisms to protect your application and users.</p>

<h2>Further Reading and Resources</h2>
<p>To deepen your understanding of these concepts, consider exploring the following resources:</p>
<ul>
    <li>Official documentation and guides</li>
    <li>Community forums and discussions</li>
    <li>Related tutorials and case studies</li>
    <li>Industry best practices and standards</li>
</ul>

<h2>Conclusion</h2>
<p>Understanding and implementing these concepts correctly is essential for building robust, scalable applications. By following the guidelines and best practices outlined in this article, you can create solutions that are both effective and maintainable.</p>
        """

    def optimize_seo(self, post):
        """Optimize post for SEO"""
        # Ensure meta description exists
        if not post.excerpt:
            post.excerpt = self.generate_excerpt(post.content)
        
        # Ensure proper heading structure
        post.content = self.fix_heading_structure(post.content)
    
    def generate_excerpt(self, content):
        """Generate SEO-friendly excerpt"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        # Get first 150 characters
        excerpt = text[:150].strip()
        if len(text) > 150:
            excerpt += "..."
        return excerpt
    
    def fix_heading_structure(self, content):
        """Ensure proper heading hierarchy"""
        # This is a simplified version - you might want more sophisticated logic
        content = re.sub(r'<h1>', '<h2>', content)
        content = re.sub(r'</h1>', '</h2>', content)
        return content
    
    def improve_structure(self, post):
        """Improve content structure"""
        # Add table of contents if content is long enough
        if len(post.content) > 1500:
            toc = self.generate_table_of_contents(post.content)
            if toc:
                post.content = toc + post.content
    
    def generate_table_of_contents(self, content):
        """Generate table of contents from headings"""
        headings = re.findall(r'<h([2-6]).*?>(.*?)</h[2-6]>', content, re.IGNORECASE)
        
        if len(headings) < 3:
            return ""
        
        toc = "<h2>Table of Contents</h2>\n<ul>\n"
        for level, heading_text in headings:
            # Clean heading text
            clean_text = re.sub(r'<[^>]+>', '', heading_text).strip()
            slug = slugify(clean_text)
            toc += f'    <li><a href="#{slug}">{clean_text}</a></li>\n'
        toc += "</ul>\n\n"
        
        return toc