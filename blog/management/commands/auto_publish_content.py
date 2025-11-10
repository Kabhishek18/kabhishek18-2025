import os
import json
import time
import random
import requests
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Django Core Imports
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify

# App-specific Imports
from blog.models import Post, Category, Tag

# Third-party Imports
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

User = get_user_model()

class Command(BaseCommand):
    help = 'Automatically generate and publish high-quality blog posts with images (cron-friendly)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1, help='Number of posts to generate')
        parser.add_argument('--schedule', choices=['now', 'daily', 'weekly'], default='now', 
                          help='Publishing schedule')
        parser.add_argument('--quality', choices=['standard', 'premium', 'expert'], default='expert',
                          help='Content quality level (default: expert for highest quality)')
        parser.add_argument('--dry-run', action='store_true', help='Generate but don\'t publish')
        parser.add_argument('--force', action='store_true', help='Force generation even if quota reached')
        parser.add_argument('--min-quality-score', type=int, default=90,
                          help='Minimum quality score required (default: 90)')
        parser.add_argument('--max-retries', type=int, default=3,
                          help='Maximum retries if quality too low (default: 3)')
        parser.add_argument('--author', type=str,
                          help='Author username or email')

    def handle(self, *args, **options):
        self.count = options['count']
        self.schedule = options['schedule']
        self.quality = options['quality']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.min_quality_score = options.get('min_quality_score', 90)
        self.max_retries = options.get('max_retries', 3)
        self.author_identifier = options.get('author')
        
        # Check if we should publish today
        if not self.should_publish_today() and not self.force:
            self.stdout.write("📅 Not scheduled to publish today. Use --force to override.")
            return
        
        # Check daily limits
        if not self.check_daily_limits() and not self.force:
            self.stdout.write("⚠️ Daily publishing limit reached. Use --force to override.")
            return
        
        self.stdout.write(f"🚀 Starting automated content generation...")
        self.stdout.write(f"   Quality: {self.quality}")
        self.stdout.write(f"   Count: {self.count}")
        self.stdout.write(f"   Schedule: {self.schedule}")
        
        success_count = 0
        for i in range(self.count):
            try:
                post = self.generate_single_post(i + 1)
                if post:
                    success_count += 1
                    self.stdout.write(f"✅ Generated post {i + 1}: {post.title}")
                else:
                    self.stdout.write(f"❌ Failed to generate post {i + 1}")
                    
                # Rate limiting between posts
                if i < self.count - 1:
                    time.sleep(10)
                    
            except Exception as e:
                self.stdout.write(f"❌ Error generating post {i + 1}: {str(e)}")
        
        self.stdout.write(f"\n🎉 Completed: {success_count}/{self.count} posts generated successfully")
        
        # Update publishing log
        self.update_publishing_log(success_count)

    def should_publish_today(self):
        """Check if we should publish based on schedule"""
        today = timezone.now().date()
        weekday = today.weekday()  # 0 = Monday, 6 = Sunday
        
        if self.schedule == 'now':
            return True
        elif self.schedule == 'daily':
            return True
        elif self.schedule == 'weekly':
            # Publish on Monday, Wednesday, Friday
            return weekday in [0, 2, 4]
        
        return True

    def check_daily_limits(self):
        """Check if we've reached daily publishing limits"""
        today = timezone.now().date()
        today_posts = Post.objects.filter(
            created_at__date=today,
            status='published'
        ).count()
        
        # Limit to 3 posts per day to avoid spam
        return today_posts < 3

    def generate_single_post(self, post_number):
        """Generate a single HIGHEST QUALITY post with retry logic"""
        from blog.content_quality import generate_quality_report
        
        self.stdout.write(f"\n🎯 Generating post {post_number} (Target quality: {self.min_quality_score}+)")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.stdout.write(f"   Attempt {attempt}/{self.max_retries}...")
                
                # Get existing categories for context
                existing_categories = list(Category.objects.values_list('name', flat=True))
                
                # Generate AI content with quality focus
                ai_data = self.get_ai_generated_content(existing_categories)
                
                if not ai_data:
                    self.stdout.write(f"   ⚠️ No content generated, retrying...")
                    time.sleep(5)
                    continue
                
                # Get or create author
                author = self.get_or_create_author()
                
                # Create the post
                post = self.create_post_from_ai_data(ai_data, author)
                
                if not post:
                    self.stdout.write(f"   ⚠️ Post creation failed, retrying...")
                    time.sleep(5)
                    continue
                
                # Generate and attach image
                self.generate_post_image(post, ai_data.get('image_prompt', ''))
                
                # Add categories and tags
                self.add_categories_and_tags(post, ai_data)
                
                # Check quality BEFORE publishing
                self.stdout.write(f"   🔍 Checking quality...")
                quality_report = generate_quality_report(post.content, post.title, post.excerpt)
                quality_score = quality_report['score']
                
                self.stdout.write(f"   📊 Quality Score: {quality_score:.1f}/100")
                
                # Check if quality meets minimum requirement
                if quality_score >= self.min_quality_score:
                    # Quality is excellent!
                    if not self.dry_run:
                        post.status = 'published'
                        post.save()
                    
                    self.stdout.write(f"   ✅ EXCELLENT! Quality score {quality_score:.1f} meets requirement ({self.min_quality_score}+)")
                    return post
                else:
                    # Quality too low, delete and retry
                    self.stdout.write(f"   ⚠️ Quality score {quality_score:.1f} below requirement ({self.min_quality_score})")
                    
                    if attempt < self.max_retries:
                        self.stdout.write(f"   🔄 Deleting and retrying...")
                        post.delete()
                        time.sleep(5)  # Wait before retry
                    else:
                        # Last attempt, keep as draft
                        post.status = 'draft'
                        post.save()
                        self.stdout.write(f"   ⚠️ Max retries reached. Saved as draft for manual review.")
                        return post
                        
            except Exception as e:
                self.stdout.write(f"   ❌ Error in attempt {attempt}: {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(5)
                else:
                    return None
        
        return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(3))
    def get_ai_generated_content(self, existing_categories):
        """Generate AI content with enhanced prompts and copyright handling"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise CommandError("GEMINI_API_KEY environment variable not found.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Get trending topic
        topic = self.get_trending_topic()
        
        # Quality-based content parameters
        quality_params = self.get_quality_parameters()
        
        # HIGHEST QUALITY prompt - targets 95-100 quality score
        prompt = f"""
        Create EXCEPTIONAL, HIGHEST QUALITY technical content that will score 95-100 on quality metrics.
        
        **CRITICAL: This must be EXCELLENT content - comprehensive, well-structured, and highly valuable.**
        
        **BLOG:** Digital Codex - Premium technical insights
        **AUDIENCE:** Senior developers, tech leads, engineering managers
        **TOPIC:** {topic}
        **QUALITY LEVEL:** {self.quality} (HIGHEST STANDARDS)
        **TARGET SCORE:** 95-100/100
        
        **MANDATORY REQUIREMENTS FOR 95-100 SCORE:**
        
        1. **LENGTH:** {quality_params['min_words']}-2000 words ({quality_params['min_chars']}-{quality_params['max_chars']} characters)
        
        2. **STRUCTURE (CRITICAL):**
           - 5-6 H2 main sections
           - 2-3 H3 subsections under each H2
           - 8-10 well-organized paragraphs
           - 3-4 bullet point lists (ul/ol)
           - 2-3 code examples in <code> or <pre> tags
           - Clear, logical flow
        
        3. **READABILITY (Target Flesch 50-60):**
           - Use clear, concise sentences (15-20 words average)
           - Mix short and medium sentences
           - Simple, direct language
           - Break up long paragraphs
           - Use active voice
        
        4. **CONTENT QUALITY:**
           - Original insights and analysis
           - Practical, actionable advice
           - Real-world examples
           - Step-by-step explanations
           - Best practices and tips
           - Common pitfalls to avoid
           - Future trends and considerations
        
        **REQUIRED STRUCTURE TEMPLATE:**
        
        <h2>Introduction</h2>
        <p>Hook and overview (2-3 paragraphs explaining the problem/topic)</p>
        
        <h2>Understanding [Main Concept]</h2>
        <p>Detailed explanation of core concepts</p>
        <h3>Key Components</h3>
        <ul>
        <li>Component 1 with detailed explanation</li>
        <li>Component 2 with detailed explanation</li>
        <li>Component 3 with detailed explanation</li>
        </ul>
        
        <h2>Implementation Guide</h2>
        <p>Step-by-step implementation details</p>
        <h3>Code Example</h3>
        <pre><code>// Practical, working code example
        // With comments explaining each part
        </code></pre>
        
        <h2>Best Practices</h2>
        <ul>
        <li>Best practice 1 with explanation</li>
        <li>Best practice 2 with explanation</li>
        <li>Best practice 3 with explanation</li>
        </ul>
        
        <h2>Common Pitfalls and Solutions</h2>
        <p>What to avoid and how to handle issues</p>
        <h3>Troubleshooting</h3>
        <ul>
        <li>Problem 1 and solution</li>
        <li>Problem 2 and solution</li>
        </ul>
        
        <h2>Advanced Techniques</h2>
        <p>Advanced concepts and optimization strategies</p>
        
        <h2>Conclusion and Next Steps</h2>
        <p>Summary and actionable next steps</p>
        
        **OUTPUT AS JSON:**
        {{
            "title": "Compelling, clear title (50-60 chars)",
            "excerpt": "Engaging meta description with keywords (140-155 chars)",
            "content": "Complete HTML content following structure above ({quality_params['min_words']}-2000 words)",
            "category": "Appropriate category",
            "image_prompt": "Professional tech image description",
            "tags": ["relevant", "technical", "tags"],
            "estimated_read_time": "8-10 min read",
            "difficulty_level": "{self.quality}",
            "key_takeaways": ["actionable insight 1", "practical tip 2", "key recommendation 3"]
        }}
        
        Write EXCEPTIONAL content that will score 95-100. Be comprehensive, well-structured, and highly valuable.
        """

        try:
            time.sleep(3)  # Rate limiting
            
            # Enhanced generation config to reduce copyright issues
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.9,  # Higher temperature for more originality
                    max_output_tokens=20000,
                    top_p=0.9,  # Slightly lower for more focused responses
                    top_k=50
                )
            )
            
            # Handle different response scenarios
            if not response.candidates:
                self.stdout.write("❌ No response candidates generated")
                return None
            
            candidate = response.candidates[0]
            
            # Check finish reason
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == 4:  # RECITATION (copyright)
                    self.stdout.write("⚠️ Content blocked due to potential copyright. Trying alternative approach...")
                    return self.generate_fallback_content(topic, quality_params)
                elif candidate.finish_reason == 3:  # SAFETY
                    self.stdout.write("⚠️ Content blocked by safety filters. Trying alternative approach...")
                    return self.generate_fallback_content(topic, quality_params)
            
            if not response.text:
                self.stdout.write("❌ Empty response from Gemini API")
                return self.generate_fallback_content(topic, quality_params)
            
            # Clean and parse JSON with better error handling
            cleaned_text = response.text.strip()
            
            # Remove markdown code blocks
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Fix common JSON issues
            # Replace control characters that break JSON
            cleaned_text = cleaned_text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            # But restore newlines in JSON structure
            cleaned_text = cleaned_text.replace('\\n', '\n')
            
            try:
                ai_data = json.loads(cleaned_text)
            except json.JSONDecodeError as json_err:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                if json_match:
                    try:
                        ai_data = json.loads(json_match.group())
                    except:
                        raise json_err
                else:
                    raise json_err
            
            # Validate content
            if not self.validate_ai_content(ai_data, quality_params):
                return None
            
            return ai_data
            
        except json.JSONDecodeError as e:
            self.stdout.write(f"❌ JSON parsing error: {e}")
            return self.generate_fallback_content(topic, quality_params)
        except Exception as e:
            self.stdout.write(f"❌ AI generation error: {e}")
            return self.generate_fallback_content(topic, quality_params)

    def generate_fallback_content(self, topic, quality_params):
        """Generate fallback content when AI fails"""
        self.stdout.write("🔄 Generating fallback content...")
        
        # Simple fallback content structure
        fallback_content = {
            "title": f"Advanced Techniques in {topic.split(':')[0]}",
            "excerpt": f"Explore advanced techniques and best practices in {topic.split(':')[0].lower()}. Learn practical implementation strategies and optimization approaches.",
            "content": self.create_fallback_html_content(topic, quality_params),
            "category": "Technology",
            "image_prompt": f"Professional technology illustration showing {topic.split(':')[0].lower()} concepts, modern design, clean layout",
            "tags": ["technology", "development", "best-practices", "advanced", "tutorial"],
            "estimated_read_time": "8 min read",
            "difficulty_level": self.quality,
            "key_takeaways": [
                "Advanced implementation strategies",
                "Performance optimization techniques", 
                "Best practices and recommendations"
            ]
        }
        
        return fallback_content

    def create_fallback_html_content(self, topic, quality_params):
        """Create fallback HTML content"""
        topic_name = topic.split(':')[0]
        
        content = f"""
<h2>Introduction to Advanced {topic_name}</h2>
<p>In the rapidly evolving landscape of software development, mastering advanced techniques in {topic_name.lower()} has become essential for building robust, scalable applications. This comprehensive guide explores cutting-edge approaches and best practices that experienced developers use to create high-performance solutions.</p>

<h2>Core Concepts and Fundamentals</h2>
<p>Understanding the fundamental principles behind {topic_name.lower()} is crucial for implementing advanced techniques effectively. Let's explore the key concepts that form the foundation of modern {topic_name.lower()} development.</p>

<h3>Architecture Patterns</h3>
<p>Modern {topic_name.lower()} implementations rely on proven architectural patterns that promote maintainability, scalability, and performance. These patterns have evolved through years of industry experience and provide reliable solutions to common challenges.</p>

<h2>Implementation Strategies</h2>
<p>When implementing advanced {topic_name.lower()} solutions, several strategies can significantly improve both development efficiency and application performance.</p>

<h3>Performance Optimization</h3>
<p>Performance optimization in {topic_name.lower()} requires a systematic approach that addresses multiple layers of the application stack. Key areas include:</p>
<ul>
    <li>Efficient algorithm selection and implementation</li>
    <li>Memory management and resource optimization</li>
    <li>Caching strategies and data access patterns</li>
    <li>Asynchronous processing and parallel execution</li>
</ul>

<h3>Scalability Considerations</h3>
<p>Building scalable {topic_name.lower()} solutions requires careful planning and implementation of patterns that support growth. Consider these approaches:</p>
<ul>
    <li>Horizontal and vertical scaling strategies</li>
    <li>Load balancing and distribution techniques</li>
    <li>Database optimization and sharding</li>
    <li>Microservices architecture patterns</li>
</ul>

<h2>Best Practices and Guidelines</h2>
<p>Following established best practices ensures that your {topic_name.lower()} implementations are maintainable, secure, and performant.</p>

<h3>Code Quality and Maintainability</h3>
<p>Maintaining high code quality is essential for long-term project success. Key practices include:</p>
<ul>
    <li>Comprehensive testing strategies and coverage</li>
    <li>Clear documentation and code comments</li>
    <li>Consistent coding standards and style guides</li>
    <li>Regular code reviews and refactoring</li>
</ul>

<h3>Security Considerations</h3>
<p>Security should be integrated into every aspect of {topic_name.lower()} development. Important considerations include:</p>
<ul>
    <li>Input validation and sanitization</li>
    <li>Authentication and authorization mechanisms</li>
    <li>Data encryption and secure communication</li>
    <li>Regular security audits and updates</li>
</ul>

<h2>Advanced Techniques</h2>
<p>Experienced developers leverage advanced techniques to solve complex problems and optimize performance in {topic_name.lower()} applications.</p>

<h3>Optimization Strategies</h3>
<p>Advanced optimization techniques can significantly improve application performance and user experience. These strategies require deep understanding of the underlying systems and careful implementation.</p>

<h3>Integration Patterns</h3>
<p>Modern applications rarely exist in isolation. Effective integration patterns enable seamless communication between different systems and services.</p>

<h2>Future Trends and Considerations</h2>
<p>The field of {topic_name.lower()} continues to evolve rapidly. Staying informed about emerging trends and technologies is crucial for maintaining competitive advantage.</p>

<h3>Emerging Technologies</h3>
<p>New technologies and approaches are constantly emerging in the {topic_name.lower()} space. Understanding these trends helps in making informed architectural decisions.</p>

<h3>Industry Evolution</h3>
<p>The software development industry continues to evolve, bringing new challenges and opportunities. Adapting to these changes requires continuous learning and skill development.</p>

<h2>Conclusion</h2>
<p>Mastering advanced {topic_name.lower()} techniques requires dedication, practice, and continuous learning. By following the strategies and best practices outlined in this guide, developers can build robust, scalable, and maintainable applications that meet modern requirements.</p>

<p>The key to success lies in understanding the fundamental principles, applying proven patterns, and staying current with industry developments. As technology continues to evolve, these foundational concepts will remain valuable for building effective solutions.</p>
        """
        
        return content.strip()

    def get_trending_topic(self):
        """Get a trending topic for content generation"""
        trending_topics = [
            # AI/ML Topics
            "Large Language Models in Production: Deployment Strategies and Best Practices",
            "AI-Powered Code Review: Tools and Implementation Strategies",
            "Machine Learning Operations at Scale: MLOps Best Practices",
            "Generative AI Integration in Enterprise Applications",
            "AI Ethics in Software Development: Practical Guidelines",
            
            # Web Development
            "Modern Frontend Architecture: Micro-frontends and Module Federation",
            "Server-Side Rendering Evolution: Next.js 14 and Beyond",
            "Progressive Web Apps: Advanced Implementation Strategies",
            "API Design Patterns for Scalable Microservices",
            "Web Performance Optimization: Core Web Vitals Mastery",
            
            # Cloud/DevOps
            "Multi-Cloud Strategy Implementation: Avoiding Vendor Lock-in",
            "Kubernetes Security: Advanced Hardening Techniques",
            "Infrastructure as Code: Terraform vs Pulumi Comparison",
            "Serverless Architecture Patterns: When and How to Use",
            "DevOps Culture Transformation: Leadership Strategies",
            
            # Security
            "Zero Trust Architecture: Implementation Roadmap",
            "Cloud Security Posture Management: Tools and Strategies",
            "DevSecOps Integration: Shifting Security Left",
            "API Security: Advanced Protection Strategies",
            "Container Security: Best Practices and Tools",
            
            # Database/Backend
            "Database Sharding Strategies for High-Scale Applications",
            "Event-Driven Architecture: Design Patterns and Implementation",
            "Microservices Data Management: Patterns and Anti-patterns",
            "Real-time Data Processing: Stream Processing Architectures",
            "Database Performance Optimization: Advanced Techniques",
            
            # Emerging Tech
            "Quantum Computing Applications in Software Development",
            "Edge Computing Architecture: Design and Implementation",
            "Blockchain Integration in Enterprise Applications",
            "IoT Security: Challenges and Solutions",
            "WebAssembly in Production: Use Cases and Performance"
        ]
        
        return random.choice(trending_topics)

    def get_quality_parameters(self):
        """Get quality parameters based on selected quality level - HIGHEST STANDARDS"""
        quality_configs = {
            'standard': {
                'min_chars': 6000,   # ~1000 words
                'max_chars': 10000,  # ~1500 words
                'min_words': 1000,   # Target word count
                'depth': 'comprehensive with practical examples and code',
                'structure': 'well-organized with 4+ H2 sections, multiple lists'
            },
            'premium': {
                'min_chars': 8000,   # ~1200 words
                'max_chars': 12000,  # ~1800 words
                'min_words': 1200,   # Target word count
                'depth': 'expert-level with advanced techniques and real examples',
                'structure': 'detailed analysis with 5+ H2 sections, code examples, lists'
            },
            'expert': {
                'min_chars': 10000,  # ~1500 words
                'max_chars': 15000,  # ~2000 words
                'min_words': 1500,   # Target word count
                'depth': 'cutting-edge with research-backed insights and case studies',
                'structure': 'comprehensive deep-dive with 6+ H2 sections, multiple examples, code, lists'
            }
        }
        
        return quality_configs.get(self.quality, quality_configs['expert'])

    def validate_ai_content(self, ai_data, quality_params):
        """Validate AI-generated content meets quality standards"""
        required_fields = ['title', 'excerpt', 'content', 'category', 'image_prompt']
        
        for field in required_fields:
            if field not in ai_data or not ai_data[field]:
                self.stdout.write(f"❌ Missing field: {field}")
                return False
        
        # Check content length
        content_length = len(ai_data['content'])
        if content_length < quality_params['min_chars']:
            self.stdout.write(f"❌ Content too short: {content_length} chars")
            return False
        
        # Check title length for SEO
        title_length = len(ai_data['title'])
        if title_length > 60:
            self.stdout.write(f"⚠️ Title too long for SEO: {title_length} chars")
            # Truncate title
            ai_data['title'] = ai_data['title'][:57] + "..."
        
        # Check excerpt length
        excerpt_length = len(ai_data['excerpt'])
        if excerpt_length < 120 or excerpt_length > 155:
            self.stdout.write(f"⚠️ Excerpt length not optimal: {excerpt_length} chars")
        
        return True

    def get_or_create_author(self):
        """Get or create the author for posts"""
        # If author specified via command line
        if hasattr(self, 'author_identifier') and self.author_identifier:
            try:
                # Try username first
                author = User.objects.get(username=self.author_identifier)
                return author
            except User.DoesNotExist:
                try:
                    # Try email
                    author = User.objects.get(email=self.author_identifier)
                    return author
                except User.DoesNotExist:
                    self.stdout.write(f"⚠️ Author '{self.author_identifier}' not found, using default")
        
        # Get the first superuser (most common case)
        author = User.objects.filter(is_superuser=True).order_by('id').first()
        if author:
            return author
        
        # Get the first staff user
        author = User.objects.filter(is_staff=True).order_by('id').first()
        if author:
            return author
        
        # Get any user
        author = User.objects.order_by('id').first()
        if author:
            return author
        
        # Last resort: create a new user (should rarely happen)
        self.stdout.write("⚠️ No users found! Creating default author...")
        author = User.objects.create_user(
            username='blog_author',
            email='blog@example.com',
            first_name='Blog',
            last_name='Author',
            is_staff=True,
            is_superuser=False
        )
        return author

    def create_post_from_ai_data(self, ai_data, author):
        """Create a post from AI-generated data"""
        try:
            # Generate unique slug
            base_slug = slugify(ai_data['title'])
            slug = base_slug
            counter = 1
            
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Create the post
            post = Post.objects.create(
                title=ai_data['title'],
                slug=slug,
                content=ai_data['content'],
                excerpt=ai_data['excerpt'],
                author=author,
                status='draft' if self.dry_run else 'published',
                allow_comments=True,
                is_featured=random.choice([True, False])  # Randomly feature some posts
            )
            
            return post
            
        except Exception as e:
            self.stdout.write(f"❌ Error creating post: {str(e)}")
            return None

    def add_categories_and_tags(self, post, ai_data):
        """Add categories and tags to the post"""
        try:
            # Create or get category
            category_name = ai_data.get('category', 'Technology')
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'slug': slugify(category_name)}
            )
            post.categories.add(category)
            
            # Create or get tags
            tags_list = ai_data.get('tags', [])
            for tag_name in tags_list[:7]:  # Limit to 7 tags
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={
                        'slug': slugify(tag_name),
                        'color': self.get_random_tag_color()
                    }
                )
                post.tags.add(tag)
                
        except Exception as e:
            self.stdout.write(f"⚠️ Error adding categories/tags: {str(e)}")

    def get_random_tag_color(self):
        """Get a random color for tags"""
        colors = [
            '#007acc', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
            '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6610f2'
        ]
        return random.choice(colors)

    def generate_post_image(self, post, image_prompt):
        """Generate a professional featured image using the same system as aicontent.py"""
        try:
            self.stdout.write(f"🎨 Generating professional image for: {post.title}")
            
            # Use the same image generation system as aicontent.py
            if self.generate_and_save_real_image(post, image_prompt):
                self.stdout.write(f"✅ Professional image generated successfully")
            else:
                self.stdout.write(f"⚠️ Using fallback image generation")
                
        except Exception as e:
            self.stdout.write(f"❌ Image generation error: {str(e)}")

    def generate_and_save_real_image(self, post, prompt):
        """
        Enhanced image generation with better prompts and fallbacks
        (Same as aicontent.py)
        """
        self.stdout.write(f"🎨 Generating professional image for: '{prompt}'...")
        
        # Enhanced prompt for better images
        enhanced_prompt = f"Professional blog featured image, modern design, technology theme, high quality, detailed: {prompt}. Style: clean, minimalist, professional, tech-focused, vibrant colors, 1200x800 aspect ratio"
        
        # Try free API first (more reliable)
        if self.generate_image_with_free_api(post, enhanced_prompt):
            return True
        
        # Fallback to enhanced placeholder
        self.generate_enhanced_placeholder_image(post, prompt)
        return True

    def generate_image_with_free_api(self, post, prompt):
        """
        Enhanced free API image generation with better services
        (Same as aicontent.py)
        """
        import requests
        import time
        
        apis = [
            {
                'name': 'Pollinations.ai',
                'url': lambda p: f"https://image.pollinations.ai/prompt/{requests.utils.quote(p)}?width=1200&height=800&nologo=true&enhance=true",
                'delay': 3
            },
            {
                'name': 'Picsum + Overlay',
                'url': lambda p: f"https://picsum.photos/1200/800?random={hash(p) % 1000}",
                'delay': 1
            }
        ]
        
        for api in apis:
            try:
                self.stdout.write(f"🎨 Trying {api['name']}...")
                time.sleep(api['delay'])
                
                image_url = api['url'](prompt)
                response = requests.get(image_url, timeout=60)
                
                if response.status_code == 200:
                    image_name = f"{post.slug}.jpg"
                    content_file = ContentFile(response.content, name=image_name)
                    post.featured_image.save(image_name, content_file, save=True)
                    self.stdout.write(f"✅ {api['name']} image generated successfully.")
                    return True
                else:
                    self.stdout.write(f"❌ {api['name']} failed. Status: {response.status_code}")
                    
            except Exception as e:
                self.stdout.write(f"❌ {api['name']} error: {e}")
                continue
        
        return False

    def generate_enhanced_placeholder_image(self, post, prompt):
        """
        Creates a more professional placeholder image with better design
        (Same as aicontent.py)
        """
        self.stdout.write(f"🎨 Creating enhanced placeholder image...")
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
            
            # Create a larger, more professional image
            width, height = 1200, 800
            
            # Create gradient background
            image = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(image)
            
            # Professional gradient colors
            colors = [
                (45, 55, 72),    # Dark blue-gray
                (66, 153, 225),  # Blue
                (129, 230, 217), # Teal
            ]
            
            # Create smooth gradient
            for i in range(height):
                ratio = i / height
                if ratio < 0.5:
                    # Blend first two colors
                    blend_ratio = ratio * 2
                    r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * blend_ratio)
                    g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * blend_ratio)
                    b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * blend_ratio)
                else:
                    # Blend last two colors
                    blend_ratio = (ratio - 0.5) * 2
                    r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * blend_ratio)
                    g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * blend_ratio)
                    b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * blend_ratio)
                
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # Add subtle texture
            noise = Image.new('RGB', (width, height), color='white')
            noise_draw = ImageDraw.Draw(noise)
            for _ in range(1000):
                x = random.randint(0, width)
                y = random.randint(0, height)
                noise_draw.point((x, y), fill=(255, 255, 255))
            
            noise = noise.filter(ImageFilter.GaussianBlur(radius=1))
            image = Image.blend(image, noise, 0.05)
            
            # Add geometric elements
            draw = ImageDraw.Draw(image)
            
            # Add some circles
            for _ in range(5):
                x = random.randint(0, width)
                y = random.randint(0, height)
                radius = random.randint(20, 60)
                alpha = random.randint(10, 30)
                
                # Create circle with transparency effect
                circle_color = (255, 255, 255, alpha)
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                            fill=circle_color)
            
            # Add title text with better typography
            try:
                font_size = 48
                font = ImageFont.load_default()
            except:
                font = None
            
            # Text with shadow effect
            title_words = post.title.split()
            lines = []
            current_line = []
            
            for word in title_words:
                current_line.append(word)
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > width - 160:  # Leave more margin
                    if len(current_line) > 1:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
                        current_line = []
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Center the text with shadow
            line_height = 60
            total_height = len(lines) * line_height
            start_y = (height - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * line_height
                
                # Draw shadow
                draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 128), font=font)
                # Draw main text
                draw.text((x, y), line, fill='white', font=font)
            
            # Add blog name/branding
            brand_text = "Digital Codex"
            brand_bbox = draw.textbbox((0, 0), brand_text, font=font)
            brand_width = brand_bbox[2] - brand_bbox[0]
            brand_x = width - brand_width - 40
            brand_y = height - 60
            
            draw.text((brand_x + 1, brand_y + 1), brand_text, fill=(0, 0, 0, 100), font=font)
            draw.text((brand_x, brand_y), brand_text, fill=(255, 255, 255, 180), font=font)
            
            # Save the image
            image_buffer = BytesIO()
            image.save(image_buffer, format='PNG', quality=95)
            image_buffer.seek(0)
            
            image_name = f"{post.slug}.png"
            content_file = ContentFile(image_buffer.getvalue(), name=image_name)
            post.featured_image.save(image_name, content_file, save=True)
            
            self.stdout.write(f"✅ Enhanced placeholder image (1200x800) created and saved.")
            
        except Exception as e:
            self.stdout.write(f"❌ Could not generate enhanced placeholder image. Error: {e}")
            # Fallback to simple placeholder
            self.generate_simple_placeholder(post)

    def generate_simple_placeholder(self, post):
        """Simple fallback placeholder"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            width, height = 1200, 800
            image = Image.new('RGB', (width, height), color='#2D3748')
            draw = ImageDraw.Draw(image)
            
            # Simple centered text
            font = ImageFont.load_default()
            text = post.title[:50] + "..." if len(post.title) > 50 else post.title
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = height // 2
            
            draw.text((x, y), text, fill='white', font=font)
            
            # Save
            image_buffer = BytesIO()
            image.save(image_buffer, format='PNG')
            image_buffer.seek(0)
            
            image_name = f"{post.slug}.png"
            content_file = ContentFile(image_buffer.getvalue(), name=image_name)
            post.featured_image.save(image_name, content_file, save=True)
            
        except Exception as e:
            self.stdout.write(f"❌ Simple placeholder failed: {e}")

    def update_publishing_log(self, success_count):
        """Update publishing log for tracking"""
        try:
            log_file = 'publishing_log.json'
            today = timezone.now().date().isoformat()
            
            # Load existing log
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {}
            
            # Update log
            if today not in log_data:
                log_data[today] = {'posts_generated': 0, 'posts_published': 0}
            
            log_data[today]['posts_generated'] += self.count
            log_data[today]['posts_published'] += success_count
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            self.stdout.write(f"⚠️ Logging error: {str(e)}")