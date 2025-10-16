from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Post, Category, Tag
from django.utils.text import slugify
import datetime

class Command(BaseCommand):
    help = 'Create high-quality content for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument('--type', type=str, help='Content type: tutorial, guide, case-study')
        parser.add_argument('--count', type=int, default=1, help='Number of posts to create')

    def handle(self, *args, **options):
        content_type = options.get('type', 'tutorial')
        count = options.get('count', 1)
        
        # Get or create author
        author, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True}
        )
        
        # Create categories
        tech_category, _ = Category.objects.get_or_create(
            name='Technology',
            defaults={'slug': 'technology'}
        )
        
        tutorial_category, _ = Category.objects.get_or_create(
            name='Tutorials',
            defaults={'slug': 'tutorials'}
        )
        
        # Create tags
        django_tag, _ = Tag.objects.get_or_create(
            name='Django',
            defaults={'slug': 'django', 'color': '#092e20'}
        )
        
        python_tag, _ = Tag.objects.get_or_create(
            name='Python',
            defaults={'slug': 'python', 'color': '#3776ab'}
        )
        
        if content_type == 'tutorial':
            self.create_tutorial_content(author, tutorial_category, [django_tag, python_tag], count)
        elif content_type == 'guide':
            self.create_guide_content(author, tech_category, [django_tag, python_tag], count)
        elif content_type == 'case-study':
            self.create_case_study_content(author, tech_category, [django_tag, python_tag], count)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} {content_type} post(s)')
        )

    def create_tutorial_content(self, author, category, tags, count):
        """Create comprehensive tutorial content"""
        tutorials = [
            {
                'title': 'Advanced Django Performance Optimization: Complete Guide',
                'excerpt': 'Master Django performance optimization with database query optimization, caching strategies, and scalability techniques for high-traffic applications.',
                'content': self.get_performance_tutorial_content()
            },
            {
                'title': 'Building Secure Django Applications: Security Best Practices',
                'excerpt': 'Comprehensive security guide for Django applications covering authentication, authorization, input validation, and protection against common vulnerabilities.',
                'content': self.get_security_tutorial_content()
            }
        ]
        
        for i in range(min(count, len(tutorials))):
            tutorial = tutorials[i]
            post = Post.objects.create(
                title=tutorial['title'],
                slug=slugify(tutorial['title']),
                author=author,
                content=tutorial['content'],
                excerpt=tutorial['excerpt'],
                status='published',
                allow_comments=True,
                is_featured=True if i == 0 else False
            )
            post.categories.add(category)
            post.tags.set(tags)
            self.stdout.write(f'Created tutorial: {post.title}')

    def get_performance_tutorial_content(self):
        """Return performance optimization tutorial content"""
        return """
<h2>Introduction to Django Performance Optimization</h2>
<p>Performance optimization is crucial for creating scalable Django applications that can handle high traffic loads while maintaining excellent user experience. This comprehensive guide covers advanced techniques for optimizing Django applications at every level.</p>

<h2>Database Query Optimization</h2>
<p>Database queries are often the primary bottleneck in web applications. Optimizing these queries can dramatically improve performance.</p>

<h3>Understanding Query Patterns</h3>
<p>Before optimizing, it's essential to understand how Django ORM generates SQL queries and identify common performance issues.</p>

<h3>Using select_related and prefetch_related</h3>
<p>These methods help eliminate the N+1 query problem by fetching related objects in fewer database queries.</p>

<h3>Database Indexing Strategies</h3>
<p>Proper indexing can significantly improve query performance, especially for frequently accessed data.</p>

<h2>Caching Strategies</h2>
<p>Implementing effective caching strategies can reduce database load and improve response times.</p>

<h3>Template Fragment Caching</h3>
<p>Cache expensive template fragments to avoid repeated processing of complex data.</p>

<h3>View-Level Caching</h3>
<p>Cache entire views when appropriate to maximize performance gains.</p>

<h3>Database Query Caching</h3>
<p>Cache frequently executed database queries to reduce database load.</p>

<h2>Static File Optimization</h2>
<p>Optimizing static file delivery improves page load times and reduces server load.</p>

<h3>Content Delivery Networks (CDN)</h3>
<p>Use CDNs to serve static files from geographically distributed servers.</p>

<h3>File Compression and Minification</h3>
<p>Compress and minify CSS, JavaScript, and image files to reduce transfer sizes.</p>

<h2>Application-Level Optimizations</h2>
<p>Various application-level optimizations can improve overall performance.</p>

<h3>Asynchronous Task Processing</h3>
<p>Use Celery or similar tools to handle time-consuming tasks asynchronously.</p>

<h3>Connection Pooling</h3>
<p>Implement database connection pooling to reduce connection overhead.</p>

<h2>Monitoring and Profiling</h2>
<p>Continuous monitoring and profiling help identify performance bottlenecks and track improvements.</p>

<h3>Performance Monitoring Tools</h3>
<p>Use tools like Django Debug Toolbar, New Relic, or custom monitoring solutions.</p>

<h3>Load Testing</h3>
<p>Regular load testing ensures your application can handle expected traffic levels.</p>

<h2>Conclusion</h2>
<p>Django performance optimization requires a systematic approach addressing database queries, caching, static files, and application architecture. By implementing these techniques, you can create applications that scale effectively and provide excellent user experience.</p>
        """

    def get_security_tutorial_content(self):
        """Return security tutorial content"""
        return """
<h2>Django Security Fundamentals</h2>
<p>Security is paramount in web application development. Django provides many built-in security features, but proper configuration and additional measures are essential for production applications.</p>

<h2>Authentication and Authorization</h2>
<p>Implementing robust authentication and authorization systems protects user accounts and sensitive data.</p>

<h3>User Authentication Best Practices</h3>
<p>Use strong password policies, multi-factor authentication, and secure session management.</p>

<h3>Permission Systems</h3>
<p>Implement granular permission systems to control access to different parts of your application.</p>

<h3>Custom User Models</h3>
<p>Design custom user models that meet your specific security requirements.</p>

<h2>Input Validation and Sanitization</h2>
<p>Proper input validation prevents many common security vulnerabilities.</p>

<h3>Form Validation</h3>
<p>Use Django forms and validators to ensure all user input is properly validated.</p>

<h3>SQL Injection Prevention</h3>
<p>Always use parameterized queries and avoid raw SQL when possible.</p>

<h3>Cross-Site Scripting (XSS) Protection</h3>
<p>Implement proper output encoding and Content Security Policy headers.</p>

<h2>CSRF Protection</h2>
<p>Cross-Site Request Forgery protection is essential for preventing unauthorized actions.</p>

<h3>CSRF Tokens</h3>
<p>Ensure all forms include CSRF tokens and validate them properly.</p>

<h3>AJAX and CSRF</h3>
<p>Handle CSRF protection correctly in AJAX requests and single-page applications.</p>

<h2>HTTPS and Transport Security</h2>
<p>Secure data transmission is crucial for protecting sensitive information.</p>

<h3>SSL/TLS Configuration</h3>
<p>Properly configure SSL/TLS certificates and security headers.</p>

<h3>HTTP Strict Transport Security</h3>
<p>Implement HSTS to prevent protocol downgrade attacks.</p>

<h2>File Upload Security</h2>
<p>File uploads can introduce various security risks that must be addressed.</p>

<h3>File Type Validation</h3>
<p>Validate file types and scan for malicious content.</p>

<h3>Storage Security</h3>
<p>Store uploaded files securely and prevent direct execution.</p>

<h2>Security Headers</h2>
<p>Implement security headers to protect against various attacks.</p>

<h3>Content Security Policy</h3>
<p>Use CSP headers to prevent XSS and other injection attacks.</p>

<h3>Additional Security Headers</h3>
<p>Implement X-Frame-Options, X-Content-Type-Options, and other protective headers.</p>

<h2>Security Monitoring and Logging</h2>
<p>Comprehensive logging and monitoring help detect and respond to security incidents.</p>

<h3>Security Event Logging</h3>
<p>Log security-relevant events for analysis and incident response.</p>

<h3>Intrusion Detection</h3>
<p>Implement systems to detect and alert on suspicious activities.</p>

<h2>Conclusion</h2>
<p>Django security requires a multi-layered approach covering authentication, input validation, transport security, and monitoring. By implementing these security measures, you can protect your application and users from common threats.</p>
        """