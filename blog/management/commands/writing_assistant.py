from django.core.management.base import BaseCommand
from blog.models import Post, Category, Tag
from django.utils.text import slugify
import re
import random

class Command(BaseCommand):
    help = 'Writing assistant for creating high-quality blog content'

    def add_arguments(self, parser):
        parser.add_argument('--expand', type=str, help='Expand a draft post by slug')
        parser.add_argument('--optimize', type=str, help='Optimize post for SEO by slug')
        parser.add_argument('--ideas', action='store_true', help='Generate content ideas')
        parser.add_argument('--research', type=str, help='Research topic and create outline')

    def handle(self, *args, **options):
        if options.get('expand'):
            self.expand_draft_post(options['expand'])
        
        if options.get('optimize'):
            self.optimize_post_seo(options['optimize'])
        
        if options.get('ideas'):
            self.generate_content_ideas()
        
        if options.get('research'):
            self.research_topic(options['research'])

    def expand_draft_post(self, slug):
        """Expand a draft post with comprehensive content"""
        try:
            post = Post.objects.get(slug=slug, status='draft')
        except Post.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Draft post with slug "{slug}" not found'))
            return
        
        self.stdout.write(f"Expanding draft post: {post.title}")
        
        # Analyze current content
        current_length = len(post.content)
        self.stdout.write(f"Current length: {current_length} characters")
        
        if current_length < 2000:
            # Add substantial content
            expanded_content = self.generate_expanded_content(post)
            post.content += expanded_content
            post.save()
            
            new_length = len(post.content)
            self.stdout.write(f"Expanded to: {new_length} characters (+{new_length - current_length})")
            self.stdout.write(self.style.SUCCESS(f'Successfully expanded "{post.title}"'))
        else:
            self.stdout.write("Post already has sufficient content length")

    def generate_expanded_content(self, post):
        """Generate additional content sections for a post"""
        topic_keywords = self.extract_keywords(post.title + " " + post.content)
        
        return f"""

<h2>Practical Implementation Guide</h2>
<p>Now that we've covered the fundamentals, let's dive into practical implementation strategies that you can apply immediately in your projects.</p>

<h3>Step-by-Step Implementation</h3>
<p>Follow these detailed steps to implement the concepts discussed:</p>
<ol>
    <li><strong>Planning Phase</strong>: Analyze your current setup and identify specific areas where these techniques will provide the most benefit.</li>
    <li><strong>Environment Setup</strong>: Ensure your development environment is properly configured with all necessary tools and dependencies.</li>
    <li><strong>Implementation</strong>: Apply the techniques systematically, testing each change before proceeding to the next.</li>
    <li><strong>Testing and Validation</strong>: Thoroughly test your implementation to ensure it meets your requirements and performs as expected.</li>
    <li><strong>Optimization</strong>: Fine-tune your implementation based on performance metrics and user feedback.</li>
</ol>

<h2>Advanced Techniques and Best Practices</h2>
<p>Once you've mastered the basics, these advanced techniques will help you take your implementation to the next level.</p>

<h3>Performance Optimization</h3>
<p>Performance is crucial for user experience and SEO. Consider these optimization strategies:</p>
<ul>
    <li>Implement efficient caching mechanisms to reduce server load and improve response times</li>
    <li>Optimize database queries to minimize resource usage and improve scalability</li>
    <li>Use content delivery networks (CDNs) to serve static assets faster</li>
    <li>Implement lazy loading for images and other heavy resources</li>
</ul>

<h3>Security Considerations</h3>
<p>Security should be integrated into every aspect of your implementation:</p>
<ul>
    <li>Implement proper input validation and sanitization</li>
    <li>Use secure authentication and authorization mechanisms</li>
    <li>Keep all dependencies and frameworks updated to the latest secure versions</li>
    <li>Regular security audits and penetration testing</li>
</ul>

<h2>Common Challenges and Solutions</h2>
<p>Based on real-world experience, here are the most common challenges developers face and proven solutions:</p>

<h3>Scalability Challenges</h3>
<p>As your application grows, you may encounter scalability bottlenecks. Address these proactively:</p>
<ul>
    <li>Design your architecture with horizontal scaling in mind</li>
    <li>Implement database sharding or read replicas for high-traffic applications</li>
    <li>Use microservices architecture for complex applications</li>
    <li>Monitor performance metrics continuously and optimize based on data</li>
</ul>

<h3>Maintenance and Updates</h3>
<p>Long-term maintenance is crucial for project success:</p>
<ul>
    <li>Establish clear documentation and coding standards</li>
    <li>Implement automated testing and continuous integration</li>
    <li>Plan for regular updates and security patches</li>
    <li>Create backup and disaster recovery procedures</li>
</ul>

<h2>Tools and Resources</h2>
<p>These tools and resources will help you implement and maintain your solution effectively:</p>

<h3>Development Tools</h3>
<ul>
    <li>Integrated Development Environments (IDEs) with debugging capabilities</li>
    <li>Version control systems for code management and collaboration</li>
    <li>Testing frameworks for automated quality assurance</li>
    <li>Performance monitoring and profiling tools</li>
</ul>

<h3>Learning Resources</h3>
<ul>
    <li>Official documentation and API references</li>
    <li>Community forums and discussion groups</li>
    <li>Online courses and certification programs</li>
    <li>Conference talks and technical presentations</li>
</ul>

<h2>Future Considerations and Trends</h2>
<p>Stay ahead of the curve by understanding emerging trends and future developments in this field:</p>

<h3>Emerging Technologies</h3>
<p>Keep an eye on these developing technologies that may impact your implementation:</p>
<ul>
    <li>Artificial intelligence and machine learning integration</li>
    <li>Edge computing and distributed architectures</li>
    <li>Serverless computing and function-as-a-service platforms</li>
    <li>Progressive web applications and modern frontend frameworks</li>
</ul>

<h3>Industry Best Practices Evolution</h3>
<p>Best practices continue to evolve. Stay informed about:</p>
<ul>
    <li>New security standards and compliance requirements</li>
    <li>Performance optimization techniques and tools</li>
    <li>Accessibility guidelines and inclusive design principles</li>
    <li>Environmental sustainability in software development</li>
</ul>

<h2>Conclusion and Next Steps</h2>
<p>Successfully implementing these concepts requires careful planning, systematic execution, and continuous learning. By following the guidelines and best practices outlined in this comprehensive guide, you'll be well-equipped to create robust, scalable, and maintainable solutions.</p>

<p>Remember that mastery comes through practice and experience. Start with small implementations, gradually increase complexity, and always prioritize code quality, security, and user experience. The investment in proper implementation will pay dividends in terms of maintainability, performance, and user satisfaction.</p>

<h3>Recommended Next Steps</h3>
<ol>
    <li>Review your current projects and identify opportunities to apply these techniques</li>
    <li>Set up a development environment to experiment with the concepts discussed</li>
    <li>Join relevant communities and forums to stay updated on best practices</li>
    <li>Consider contributing to open-source projects to gain practical experience</li>
    <li>Plan regular reviews and updates of your implementations</li>
</ol>

<p>Continue learning, experimenting, and refining your approach. The field of technology is constantly evolving, and staying current with new developments will ensure your skills remain relevant and valuable.</p>
        """

    def extract_keywords(self, text):
        """Extract keywords from text for content generation"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        return list(set(keywords))[:10]  # Return top 10 unique keywords

    def optimize_post_seo(self, slug):
        """Optimize a post for SEO"""
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Post with slug "{slug}" not found'))
            return
        
        self.stdout.write(f"Optimizing SEO for: {post.title}")
        
        optimizations = []
        
        # Check and optimize title
        if len(post.title) > 60:
            optimizations.append("Title is too long for SEO (>60 characters)")
        
        # Check and optimize meta description
        if not post.excerpt or len(post.excerpt) < 120:
            post.excerpt = self.generate_meta_description(post)
            optimizations.append("Generated meta description")
        
        # Check heading structure
        if not re.search(r'<h[2-6]', post.content):
            optimizations.append("Add proper heading structure (H2, H3 tags)")
        
        # Check for internal links
        internal_links = post.content.count('/blog/')
        if internal_links < 2:
            optimizations.append("Add more internal links to related posts")
        
        # Check for images
        if '<img' not in post.content and not post.featured_image:
            optimizations.append("Add images or visual content")
        
        # Save optimizations
        if post.excerpt:
            post.save()
        
        # Report optimizations
        if optimizations:
            self.stdout.write("SEO Optimizations needed:")
            for opt in optimizations:
                self.stdout.write(f"  • {opt}")
        else:
            self.stdout.write(self.style.SUCCESS("Post is well-optimized for SEO!"))

    def generate_meta_description(self, post):
        """Generate SEO-friendly meta description"""
        # Extract first meaningful paragraph
        content_text = re.sub(r'<[^>]+>', '', post.content)
        sentences = content_text.split('.')[:2]
        description = '. '.join(sentences).strip()
        
        if len(description) > 155:
            description = description[:152] + "..."
        elif len(description) < 120:
            description += f" Learn more about {post.title.lower()} with practical examples and expert insights."
        
        return description

    def generate_content_ideas(self):
        """Generate fresh content ideas based on current trends"""
        self.stdout.write("🧠 Generating fresh content ideas...")
        
        # Current trending topics in web development
        trending_topics = [
            {
                'title': 'Django 5.0 New Features: Complete Migration Guide',
                'category': 'Django Tutorials',
                'difficulty': 'Intermediate',
                'estimated_time': '3-4 hours to write',
                'keywords': ['Django 5.0', 'migration', 'new features', 'upgrade guide']
            },
            {
                'title': 'Building Real-time Applications with Django Channels',
                'category': 'Django Tutorials',
                'difficulty': 'Advanced',
                'estimated_time': '4-5 hours to write',
                'keywords': ['Django Channels', 'WebSockets', 'real-time', 'async']
            },
            {
                'title': 'Python Type Hints: Advanced Patterns and Best Practices',
                'category': 'Python Programming',
                'difficulty': 'Intermediate',
                'estimated_time': '2-3 hours to write',
                'keywords': ['Python', 'type hints', 'mypy', 'static typing']
            },
            {
                'title': 'API Rate Limiting with Redis and Django',
                'category': 'Security',
                'difficulty': 'Intermediate',
                'estimated_time': '3-4 hours to write',
                'keywords': ['API', 'rate limiting', 'Redis', 'Django', 'security']
            },
            {
                'title': 'Modern CSS: Container Queries and CSS Grid Subgrid',
                'category': 'Web Development',
                'difficulty': 'Intermediate',
                'estimated_time': '2-3 hours to write',
                'keywords': ['CSS', 'container queries', 'grid subgrid', 'responsive design']
            },
            {
                'title': 'Microservices with FastAPI and Docker',
                'category': 'Python Programming',
                'difficulty': 'Advanced',
                'estimated_time': '4-5 hours to write',
                'keywords': ['FastAPI', 'microservices', 'Docker', 'Python', 'API']
            },
            {
                'title': 'Database Sharding Strategies for Django Applications',
                'category': 'Database Management',
                'difficulty': 'Advanced',
                'estimated_time': '4-5 hours to write',
                'keywords': ['database sharding', 'Django', 'scalability', 'PostgreSQL']
            },
            {
                'title': 'Testing Django Applications: From Unit to Integration',
                'category': 'Best Practices',
                'difficulty': 'Intermediate',
                'estimated_time': '3-4 hours to write',
                'keywords': ['Django testing', 'unit tests', 'integration tests', 'pytest']
            }
        ]
        
        # Select 5 random ideas
        selected_ideas = random.sample(trending_topics, 5)
        
        self.stdout.write("\n📝 Content Ideas for This Week:")
        self.stdout.write("=" * 50)
        
        for i, idea in enumerate(selected_ideas, 1):
            self.stdout.write(f"\n{i}. {idea['title']}")
            self.stdout.write(f"   Category: {idea['category']}")
            self.stdout.write(f"   Difficulty: {idea['difficulty']}")
            self.stdout.write(f"   Time needed: {idea['estimated_time']}")
            self.stdout.write(f"   Keywords: {', '.join(idea['keywords'])}")
        
        # SEO keyword suggestions
        self.stdout.write(f"\n🔍 High-Value SEO Keywords to Target:")
        seo_keywords = [
            "Django tutorial 2024",
            "Python web development",
            "REST API best practices",
            "Database optimization techniques",
            "Web application security",
            "Django performance optimization",
            "Python async programming",
            "Modern JavaScript frameworks"
        ]
        
        for keyword in seo_keywords:
            self.stdout.write(f"  • {keyword}")

    def research_topic(self, topic):
        """Research a topic and create a comprehensive outline"""
        self.stdout.write(f"🔍 Researching topic: {topic}")
        
        # Generate comprehensive outline based on topic
        outline = self.generate_topic_outline(topic)
        
        self.stdout.write(f"\n📋 Comprehensive Outline for '{topic}':")
        self.stdout.write("=" * 60)
        self.stdout.write(outline)
        
        # Suggest related topics
        related_topics = self.suggest_related_topics(topic)
        self.stdout.write(f"\n🔗 Related Topics to Cover:")
        for related in related_topics:
            self.stdout.write(f"  • {related}")

    def generate_topic_outline(self, topic):
        """Generate a detailed outline for a given topic"""
        topic_lower = topic.lower()
        
        if 'django' in topic_lower:
            return self.get_django_outline(topic)
        elif 'python' in topic_lower:
            return self.get_python_outline(topic)
        elif 'javascript' in topic_lower:
            return self.get_javascript_outline(topic)
        elif 'database' in topic_lower:
            return self.get_database_outline(topic)
        elif 'security' in topic_lower:
            return self.get_security_outline(topic)
        else:
            return self.get_generic_outline(topic)

    def get_django_outline(self, topic):
        """Generate Django-specific outline"""
        return f"""
1. Introduction to {topic}
   - What is {topic} and why it matters
   - Prerequisites and setup requirements
   - What readers will learn

2. Django Fundamentals Review
   - Key Django concepts relevant to {topic}
   - Project structure and best practices
   - Virtual environment setup

3. Step-by-Step Implementation
   - Setting up the development environment
   - Creating the Django project structure
   - Implementing core functionality
   - Adding advanced features

4. Code Examples and Demonstrations
   - Complete working examples
   - Common use cases and scenarios
   - Error handling and edge cases

5. Testing and Quality Assurance
   - Writing unit tests
   - Integration testing strategies
   - Performance testing considerations

6. Deployment and Production Considerations
   - Production-ready configuration
   - Security best practices
   - Performance optimization
   - Monitoring and maintenance

7. Troubleshooting and Common Issues
   - Frequently encountered problems
   - Debugging techniques
   - Performance bottlenecks

8. Advanced Topics and Extensions
   - Advanced patterns and techniques
   - Third-party integrations
   - Customization options

9. Best Practices and Recommendations
   - Industry standards
   - Code organization
   - Documentation guidelines

10. Conclusion and Next Steps
    - Summary of key points
    - Additional resources
    - Suggested follow-up topics
        """

    def get_python_outline(self, topic):
        """Generate Python-specific outline"""
        return f"""
1. Introduction to {topic}
   - Overview and importance
   - Python version requirements
   - Learning objectives

2. Python Fundamentals
   - Core concepts and syntax
   - Relevant Python features
   - Environment setup

3. Practical Implementation
   - Step-by-step coding examples
   - Real-world applications
   - Code organization patterns

4. Advanced Techniques
   - Performance optimization
   - Memory management
   - Error handling strategies

5. Testing and Debugging
   - Unit testing with pytest
   - Debugging techniques
   - Code quality tools

6. Best Practices
   - PEP 8 compliance
   - Code documentation
   - Project structure

7. Integration and Deployment
   - Package management
   - Virtual environments
   - Production deployment

8. Performance and Optimization
   - Profiling techniques
   - Optimization strategies
   - Scalability considerations

9. Conclusion and Resources
   - Key takeaways
   - Further reading
   - Community resources
        """

    def suggest_related_topics(self, topic):
        """Suggest related topics for comprehensive coverage"""
        topic_lower = topic.lower()
        
        if 'django' in topic_lower:
            return [
                "Django REST Framework integration",
                "Django security best practices",
                "Django performance optimization",
                "Django testing strategies",
                "Django deployment with Docker"
            ]
        elif 'python' in topic_lower:
            return [
                "Python web frameworks comparison",
                "Python async programming",
                "Python testing best practices",
                "Python package management",
                "Python performance optimization"
            ]
        elif 'javascript' in topic_lower:
            return [
                "Modern JavaScript frameworks",
                "JavaScript performance optimization",
                "JavaScript testing strategies",
                "JavaScript build tools",
                "JavaScript security best practices"
            ]
        else:
            return [
                "Related implementation patterns",
                "Performance considerations",
                "Security implications",
                "Testing strategies",
                "Deployment best practices"
            ]

    def get_generic_outline(self, topic):
        """Generate generic outline for any topic"""
        return f"""
1. Introduction to {topic}
   - Problem statement and context
   - Why this topic matters
   - Learning objectives

2. Background and Fundamentals
   - Core concepts and terminology
   - Historical context
   - Current state of the field

3. Technical Deep Dive
   - Detailed technical explanation
   - Architecture and design patterns
   - Implementation considerations

4. Practical Examples
   - Real-world use cases
   - Step-by-step implementations
   - Code examples and demonstrations

5. Best Practices and Guidelines
   - Industry standards
   - Common patterns
   - Recommended approaches

6. Common Challenges and Solutions
   - Typical problems encountered
   - Proven solutions and workarounds
   - Troubleshooting guide

7. Performance and Optimization
   - Performance considerations
   - Optimization techniques
   - Monitoring and metrics

8. Security Considerations
   - Security implications
   - Best practices for secure implementation
   - Common vulnerabilities and mitigation

9. Tools and Resources
   - Recommended tools and libraries
   - Documentation and references
   - Community resources

10. Conclusion and Future Directions
    - Summary of key points
    - Emerging trends and developments
    - Next steps for readers
        """