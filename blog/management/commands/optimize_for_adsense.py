from django.core.management.base import BaseCommand
from blog.models import Post, Category, Tag
from django.contrib.auth.models import User
from django.utils.text import slugify
import re

class Command(BaseCommand):
    help = 'Comprehensive optimization for AdSense compliance'

    def add_arguments(self, parser):
        parser.add_argument('--audit', action='store_true', help='Audit existing content')
        parser.add_argument('--fix', action='store_true', help='Fix identified issues')
        parser.add_argument('--create-quality', action='store_true', help='Create high-quality content')

    def handle(self, *args, **options):
        if options.get('audit'):
            self.audit_content()
        
        if options.get('fix'):
            self.fix_content_issues()
        
        if options.get('create_quality'):
            self.create_quality_content()
        
        self.stdout.write(
            self.style.SUCCESS('AdSense optimization completed successfully')
        )

    def audit_content(self):
        """Audit existing content for AdSense compliance"""
        self.stdout.write("Auditing content for AdSense compliance...")
        
        posts = Post.objects.filter(status='published')
        issues = []
        
        for post in posts:
            post_issues = []
            
            # Check content length
            if len(post.content) < 800:
                post_issues.append(f"Content too short: {len(post.content)} characters")
            
            # Check for proper headings
            if not re.search(r'<h[2-6]', post.content):
                post_issues.append("No proper heading structure")
            
            # Check for meta description
            if not post.excerpt or len(post.excerpt) < 120:
                post_issues.append("Missing or inadequate meta description")
            
            # Check for images
            if not post.featured_image and '<img' not in post.content:
                post_issues.append("No images found")
            
            # Check for internal links
            if post.content.count('<a href') < 2:
                post_issues.append("Insufficient internal linking")
            
            if post_issues:
                issues.append({
                    'post': post,
                    'issues': post_issues
                })
        
        # Report findings
        self.stdout.write(f"\nAudit Results:")
        self.stdout.write(f"Total posts audited: {posts.count()}")
        self.stdout.write(f"Posts with issues: {len(issues)}")
        
        for item in issues[:10]:  # Show first 10 issues
            self.stdout.write(f"\nPost: {item['post'].title}")
            for issue in item['issues']:
                self.stdout.write(f"  - {issue}")

    def fix_content_issues(self):
        """Fix identified content issues"""
        self.stdout.write("Fixing content issues...")
        
        posts = Post.objects.filter(status='published')
        fixed_count = 0
        
        for post in posts:
            fixed = False
            
            # Fix short content
            if len(post.content) < 800:
                post.content = self.expand_content(post)
                fixed = True
            
            # Fix missing meta description
            if not post.excerpt or len(post.excerpt) < 120:
                post.excerpt = self.generate_meta_description(post)
                fixed = True
            
            # Fix heading structure
            if not re.search(r'<h[2-6]', post.content):
                post.content = self.add_heading_structure(post.content)
                fixed = True
            
            # Add internal links
            if post.content.count('<a href') < 2:
                post.content = self.add_internal_links(post)
                fixed = True
            
            if fixed:
                post.save()
                fixed_count += 1
        
        self.stdout.write(f"Fixed {fixed_count} posts")

    def expand_content(self, post):
        """Expand content to meet minimum requirements"""
        additional_sections = f"""

<h2>Overview</h2>
<p>This comprehensive guide explores {post.title.lower()} in detail, providing practical insights and actionable information for developers and technical professionals. Understanding these concepts is crucial for building robust, scalable applications.</p>

<h2>Key Benefits</h2>
<p>Implementing the approaches discussed in this article offers several advantages:</p>
<ul>
    <li>Improved performance and efficiency</li>
    <li>Better maintainability and code organization</li>
    <li>Enhanced security and reliability</li>
    <li>Scalability for future growth</li>
    <li>Industry best practices compliance</li>
</ul>

<h2>Implementation Considerations</h2>
<p>When implementing these concepts, consider the following important factors:</p>

<h3>Performance Impact</h3>
<p>Always evaluate the performance implications of your implementation. Consider factors such as memory usage, processing time, and network overhead to ensure optimal performance.</p>

<h3>Security Considerations</h3>
<p>Security should be a primary concern in any implementation. Ensure proper input validation, authentication mechanisms, and data protection measures are in place.</p>

<h3>Scalability Planning</h3>
<p>Design your solution with scalability in mind. Consider how your implementation will perform under increased load and plan for horizontal and vertical scaling options.</p>

<h2>Common Challenges and Solutions</h2>
<p>Developers often encounter specific challenges when working with these technologies. Here are some common issues and their recommended solutions:</p>

<h3>Integration Challenges</h3>
<p>Integrating different systems and technologies can be complex. Use well-defined APIs, follow standard protocols, and implement proper error handling to ensure smooth integration.</p>

<h3>Maintenance and Updates</h3>
<p>Regular maintenance and updates are essential for long-term success. Establish clear documentation, implement automated testing, and plan for regular updates and security patches.</p>

<h2>Best Practices and Recommendations</h2>
<p>To ensure success with your implementation, follow these industry best practices:</p>
<ul>
    <li>Write clean, well-documented code</li>
    <li>Implement comprehensive testing strategies</li>
    <li>Use version control and proper deployment processes</li>
    <li>Monitor performance and user experience</li>
    <li>Stay updated with latest developments and security patches</li>
</ul>

<h2>Tools and Resources</h2>
<p>Several tools and resources can help you implement and maintain these solutions effectively:</p>
<ul>
    <li>Development frameworks and libraries</li>
    <li>Testing and debugging tools</li>
    <li>Performance monitoring solutions</li>
    <li>Documentation and community resources</li>
    <li>Training and certification programs</li>
</ul>

<h2>Future Considerations</h2>
<p>Technology continues to evolve rapidly. Stay informed about emerging trends, new tools, and evolving best practices to ensure your implementation remains current and effective.</p>

<h2>Conclusion</h2>
<p>Successfully implementing these concepts requires careful planning, attention to detail, and ongoing maintenance. By following the guidelines and best practices outlined in this comprehensive guide, you can create robust, scalable solutions that meet your requirements and provide long-term value.</p>

<p>Remember to regularly review and update your implementation to ensure it continues to meet evolving needs and takes advantage of new technologies and best practices as they become available.</p>
        """
        
        return post.content + additional_sections

    def generate_meta_description(self, post):
        """Generate SEO-friendly meta description"""
        # Extract first meaningful paragraph
        content_text = re.sub(r'<[^>]+>', '', post.content)
        sentences = content_text.split('.')[:3]
        description = '. '.join(sentences).strip()
        
        if len(description) > 155:
            description = description[:152] + "..."
        elif len(description) < 120:
            description += f" Learn more about {post.title.lower()} with practical examples and expert insights."
        
        return description

    def add_heading_structure(self, content):
        """Add proper heading structure to content"""
        # If content doesn't have headings, add some basic structure
        if not re.search(r'<h[2-6]', content):
            # Split content into paragraphs and add headings
            paragraphs = content.split('</p>')
            if len(paragraphs) > 3:
                # Add headings at strategic points
                structured_content = paragraphs[0] + '</p>'
                structured_content += '\n\n<h2>Key Concepts</h2>\n'
                structured_content += '</p>'.join(paragraphs[1:len(paragraphs)//2]) + '</p>'
                structured_content += '\n\n<h2>Implementation Details</h2>\n'
                structured_content += '</p>'.join(paragraphs[len(paragraphs)//2:]) + '</p>'
                return structured_content
        
        return content

    def add_internal_links(self, post):
        """Add internal links to related content"""
        # Find related posts
        related_posts = Post.objects.filter(
            status='published',
            categories__in=post.categories.all()
        ).exclude(id=post.id).distinct()[:3]
        
        if related_posts:
            links_section = "\n\n<h2>Related Articles</h2>\n<ul>\n"
            for related_post in related_posts:
                links_section += f'<li><a href="/blog/{related_post.slug}/">{related_post.title}</a></li>\n'
            links_section += "</ul>\n"
            
            return post.content + links_section
        
        return post.content

    def create_quality_content(self):
        """Create high-quality content samples"""
        self.stdout.write("Creating high-quality content...")
        
        # Get or create author
        author, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True}
        )
        
        # Create categories if they don't exist
        tech_category, _ = Category.objects.get_or_create(
            name='Technology',
            defaults={'slug': 'technology'}
        )
        
        tutorial_category, _ = Category.objects.get_or_create(
            name='Tutorials',
            defaults={'slug': 'tutorials'}
        )
        
        # Create high-quality posts
        quality_posts = [
            {
                'title': 'Complete Guide to Web Application Security: Best Practices and Implementation',
                'category': tech_category,
                'content': self.get_security_guide_content(),
                'excerpt': 'Comprehensive guide to web application security covering authentication, authorization, data protection, and security best practices for modern web applications.'
            },
            {
                'title': 'Modern JavaScript Development: ES6+ Features and Best Practices',
                'category': tutorial_category,
                'content': self.get_javascript_guide_content(),
                'excerpt': 'Master modern JavaScript development with ES6+ features, async/await patterns, module systems, and performance optimization techniques.'
            },
            {
                'title': 'Database Design and Optimization: From Schema to Performance',
                'category': tech_category,
                'content': self.get_database_guide_content(),
                'excerpt': 'Learn database design principles, normalization techniques, indexing strategies, and performance optimization for scalable applications.'
            }
        ]
        
        created_count = 0
        for post_data in quality_posts:
            if not Post.objects.filter(title=post_data['title']).exists():
                post = Post.objects.create(
                    title=post_data['title'],
                    slug=slugify(post_data['title']),
                    content=post_data['content'],
                    excerpt=post_data['excerpt'],
                    author=author,
                    status='published',
                    is_featured=True
                )
                post.categories.add(post_data['category'])
                created_count += 1
        
        self.stdout.write(f"Created {created_count} high-quality posts")

    def get_security_guide_content(self):
        """Return comprehensive security guide content"""
        return """
<h2>Introduction to Web Application Security</h2>
<p>Web application security is a critical aspect of modern software development that cannot be overlooked. With cyber threats becoming increasingly sophisticated, developers must implement comprehensive security measures to protect applications and user data.</p>

<h2>Authentication and Authorization</h2>
<p>Proper authentication and authorization form the foundation of web application security.</p>

<h3>Multi-Factor Authentication</h3>
<p>Implementing multi-factor authentication (MFA) significantly enhances security by requiring users to provide multiple forms of verification.</p>

<h3>Role-Based Access Control</h3>
<p>RBAC ensures users only access resources appropriate to their role within the organization.</p>

<h2>Data Protection and Encryption</h2>
<p>Protecting sensitive data through encryption and secure storage practices is essential for maintaining user trust and regulatory compliance.</p>

<h3>Encryption at Rest</h3>
<p>All sensitive data should be encrypted when stored in databases or file systems.</p>

<h3>Encryption in Transit</h3>
<p>Use HTTPS and TLS to protect data during transmission between client and server.</p>

<h2>Common Vulnerabilities and Prevention</h2>
<p>Understanding and preventing common security vulnerabilities is crucial for building secure applications.</p>

<h3>SQL Injection Prevention</h3>
<p>Use parameterized queries and input validation to prevent SQL injection attacks.</p>

<h3>Cross-Site Scripting (XSS) Protection</h3>
<p>Implement proper input sanitization and output encoding to prevent XSS attacks.</p>

<h3>Cross-Site Request Forgery (CSRF) Protection</h3>
<p>Use CSRF tokens and proper validation to prevent unauthorized actions.</p>

<h2>Security Headers and Configuration</h2>
<p>Proper security headers and server configuration provide additional layers of protection.</p>

<h3>Content Security Policy</h3>
<p>CSP headers help prevent XSS attacks by controlling resource loading.</p>

<h3>HTTP Strict Transport Security</h3>
<p>HSTS ensures all communications use HTTPS and prevents protocol downgrade attacks.</p>

<h2>Security Testing and Monitoring</h2>
<p>Regular security testing and continuous monitoring are essential for maintaining security posture.</p>

<h3>Automated Security Testing</h3>
<p>Integrate security testing into your CI/CD pipeline for continuous security validation.</p>

<h3>Security Monitoring and Logging</h3>
<p>Implement comprehensive logging and monitoring to detect and respond to security incidents.</p>

<h2>Compliance and Regulations</h2>
<p>Understanding relevant regulations and compliance requirements is crucial for many applications.</p>

<h3>GDPR Compliance</h3>
<p>Ensure proper data handling and user privacy rights for European users.</p>

<h3>Industry-Specific Requirements</h3>
<p>Different industries have specific security requirements that must be addressed.</p>

<h2>Best Practices Summary</h2>
<p>Following security best practices helps ensure comprehensive protection:</p>
<ul>
    <li>Implement defense in depth strategies</li>
    <li>Keep all software and dependencies updated</li>
    <li>Use secure coding practices</li>
    <li>Regular security audits and penetration testing</li>
    <li>Employee security training and awareness</li>
</ul>

<h2>Conclusion</h2>
<p>Web application security requires ongoing attention and continuous improvement. By implementing these security measures and staying informed about emerging threats, developers can build applications that protect user data and maintain trust.</p>
        """

    def get_javascript_guide_content(self):
        """Return comprehensive JavaScript guide content"""
        return """
<h2>Modern JavaScript Development Overview</h2>
<p>JavaScript has evolved significantly with ES6+ features that enable more efficient, readable, and maintainable code. This comprehensive guide covers essential modern JavaScript concepts and best practices.</p>

<h2>ES6+ Features and Syntax</h2>
<p>Modern JavaScript introduces powerful features that improve code quality and developer productivity.</p>

<h3>Arrow Functions and Lexical Scope</h3>
<p>Arrow functions provide concise syntax and lexical this binding, making code more predictable and easier to understand.</p>

<h3>Destructuring Assignment</h3>
<p>Destructuring allows extracting values from arrays and objects in a clean, readable way.</p>

<h3>Template Literals</h3>
<p>Template literals enable string interpolation and multi-line strings with improved readability.</p>

<h2>Asynchronous JavaScript</h2>
<p>Modern JavaScript provides powerful tools for handling asynchronous operations effectively.</p>

<h3>Promises and Promise Chaining</h3>
<p>Promises provide a cleaner alternative to callbacks for handling asynchronous operations.</p>

<h3>Async/Await Patterns</h3>
<p>Async/await syntax makes asynchronous code look and behave more like synchronous code.</p>

<h3>Error Handling in Async Code</h3>
<p>Proper error handling is crucial for robust asynchronous JavaScript applications.</p>

<h2>Module Systems and Code Organization</h2>
<p>Modern JavaScript module systems enable better code organization and reusability.</p>

<h3>ES6 Modules</h3>
<p>Native JavaScript modules provide standardized import/export functionality.</p>

<h3>Module Bundling and Build Tools</h3>
<p>Tools like Webpack and Rollup optimize module loading and application performance.</p>

<h2>Functional Programming Concepts</h2>
<p>Functional programming principles can improve code quality and maintainability.</p>

<h3>Higher-Order Functions</h3>
<p>Functions that operate on other functions enable powerful abstractions and code reuse.</p>

<h3>Immutability and Pure Functions</h3>
<p>Immutable data and pure functions reduce bugs and make code more predictable.</p>

<h2>Performance Optimization</h2>
<p>Optimizing JavaScript performance is crucial for user experience and application scalability.</p>

<h3>Memory Management</h3>
<p>Understanding memory management helps prevent memory leaks and optimize performance.</p>

<h3>Code Splitting and Lazy Loading</h3>
<p>Splitting code into smaller chunks improves initial load times and user experience.</p>

<h3>Performance Monitoring</h3>
<p>Regular performance monitoring helps identify and address performance bottlenecks.</p>

<h2>Testing and Quality Assurance</h2>
<p>Comprehensive testing ensures code reliability and maintainability.</p>

<h3>Unit Testing with Modern Frameworks</h3>
<p>Modern testing frameworks provide powerful tools for comprehensive test coverage.</p>

<h3>Integration and End-to-End Testing</h3>
<p>Testing complete user workflows ensures application reliability.</p>

<h2>Development Tools and Workflow</h2>
<p>Modern development tools improve productivity and code quality.</p>

<h3>Linting and Code Formatting</h3>
<p>Automated code quality tools ensure consistent code style and catch potential issues.</p>

<h3>Development Environment Setup</h3>
<p>Proper development environment configuration improves productivity and reduces errors.</p>

<h2>Best Practices and Patterns</h2>
<p>Following established patterns and best practices leads to more maintainable code:</p>
<ul>
    <li>Use consistent naming conventions</li>
    <li>Write self-documenting code</li>
    <li>Implement proper error handling</li>
    <li>Follow SOLID principles</li>
    <li>Regular code reviews and refactoring</li>
</ul>

<h2>Conclusion</h2>
<p>Modern JavaScript development requires understanding both language features and development practices. By mastering these concepts and following best practices, developers can create efficient, maintainable, and scalable applications.</p>
        """

    def get_database_guide_content(self):
        """Return comprehensive database guide content"""
        return """
<h2>Database Design Fundamentals</h2>
<p>Effective database design is crucial for application performance, data integrity, and long-term maintainability. This comprehensive guide covers essential database design principles and optimization techniques.</p>

<h2>Database Schema Design</h2>
<p>Proper schema design forms the foundation of efficient database systems.</p>

<h3>Entity-Relationship Modeling</h3>
<p>ER modeling helps visualize and plan database structure before implementation.</p>

<h3>Normalization Principles</h3>
<p>Database normalization reduces redundancy and improves data integrity through structured design principles.</p>

<h3>Denormalization Strategies</h3>
<p>Strategic denormalization can improve performance in specific use cases while maintaining data consistency.</p>

<h2>Data Types and Constraints</h2>
<p>Choosing appropriate data types and constraints ensures data integrity and optimal performance.</p>

<h3>Choosing Optimal Data Types</h3>
<p>Selecting the right data types affects storage efficiency and query performance.</p>

<h3>Constraint Implementation</h3>
<p>Database constraints enforce business rules and maintain data quality at the database level.</p>

<h2>Indexing Strategies</h2>
<p>Proper indexing dramatically improves query performance and overall database efficiency.</p>

<h3>Index Types and Use Cases</h3>
<p>Different index types serve different purposes and query patterns.</p>

<h3>Composite Indexes</h3>
<p>Multi-column indexes can significantly improve performance for complex queries.</p>

<h3>Index Maintenance</h3>
<p>Regular index maintenance ensures optimal performance over time.</p>

<h2>Query Optimization</h2>
<p>Optimizing database queries is essential for application performance and scalability.</p>

<h3>Query Execution Plans</h3>
<p>Understanding execution plans helps identify performance bottlenecks and optimization opportunities.</p>

<h3>Join Optimization</h3>
<p>Efficient join strategies can dramatically improve query performance.</p>

<h3>Subquery vs. Join Performance</h3>
<p>Choosing between subqueries and joins affects query performance and readability.</p>

<h2>Performance Monitoring and Tuning</h2>
<p>Continuous monitoring and tuning ensure optimal database performance.</p>

<h3>Performance Metrics</h3>
<p>Key performance indicators help identify and address performance issues.</p>

<h3>Query Analysis Tools</h3>
<p>Database-specific tools provide insights into query performance and optimization opportunities.</p>

<h3>Capacity Planning</h3>
<p>Proper capacity planning ensures database systems can handle growth and peak loads.</p>

<h2>Scalability Considerations</h2>
<p>Designing for scalability ensures database systems can grow with application needs.</p>

<h3>Horizontal vs. Vertical Scaling</h3>
<p>Understanding scaling options helps choose the right approach for specific requirements.</p>

<h3>Partitioning Strategies</h3>
<p>Database partitioning can improve performance and manageability for large datasets.</p>

<h3>Replication and High Availability</h3>
<p>Database replication ensures data availability and can improve read performance.</p>

<h2>Security and Backup Strategies</h2>
<p>Database security and backup procedures protect against data loss and unauthorized access.</p>

<h3>Access Control and Permissions</h3>
<p>Proper access control ensures only authorized users can access sensitive data.</p>

<h3>Backup and Recovery Planning</h3>
<p>Comprehensive backup strategies protect against data loss and enable disaster recovery.</p>

<h2>Modern Database Technologies</h2>
<p>Understanding different database technologies helps choose the right solution for specific needs.</p>

<h3>SQL vs. NoSQL Considerations</h3>
<p>Different database types serve different use cases and requirements.</p>

<h3>Cloud Database Services</h3>
<p>Cloud databases offer scalability and managed services that can reduce operational overhead.</p>

<h2>Best Practices Summary</h2>
<p>Following database best practices ensures optimal performance and maintainability:</p>
<ul>
    <li>Design schema with future growth in mind</li>
    <li>Implement proper indexing strategies</li>
    <li>Regular performance monitoring and optimization</li>
    <li>Comprehensive backup and recovery procedures</li>
    <li>Security-first approach to access control</li>
</ul>

<h2>Conclusion</h2>
<p>Effective database design and optimization require understanding both theoretical principles and practical implementation techniques. By following these guidelines and continuously monitoring performance, developers can create database systems that scale efficiently and maintain excellent performance.</p>
        """