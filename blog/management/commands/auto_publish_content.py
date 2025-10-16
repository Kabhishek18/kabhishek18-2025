import os
import json
import time
import random
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
        parser.add_argument('--quality', choices=['standard', 'premium', 'expert'], default='premium',
                          help='Content quality level')
        parser.add_argument('--dry-run', action='store_true', help='Generate but don\'t publish')
        parser.add_argument('--force', action='store_true', help='Force generation even if quota reached')

    def handle(self, *args, **options):
        self.count = options['count']
        self.schedule = options['schedule']
        self.quality = options['quality']
        self.dry_run = options['dry_run']
        self.force = options['force']
        
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
        """Generate a single high-quality post"""
        try:
            # Get existing categories for context
            existing_categories = list(Category.objects.values_list('name', flat=True))
            
            # Generate AI content
            ai_data = self.get_ai_generated_content(existing_categories)
            
            if not ai_data:
                return None
            
            # Get or create author
            author = self.get_or_create_author()
            
            # Create the post
            post = self.create_post_from_ai_data(ai_data, author)
            
            if post:
                # Generate and attach image
                self.generate_post_image(post, ai_data.get('image_prompt', ''))
                
                # Add categories and tags
                self.add_categories_and_tags(post, ai_data)
                
                # Set publishing status
                if not self.dry_run:
                    post.status = 'published'
                    post.save()
                
                return post
                
        except Exception as e:
            self.stdout.write(f"❌ Error in generate_single_post: {str(e)}")
            return None

    @retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(3))
    def get_ai_generated_content(self, existing_categories):
        """Generate AI content with enhanced prompts"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise CommandError("GEMINI_API_KEY environment variable not found.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Get trending topic
        topic = self.get_trending_topic()
        
        # Quality-based content parameters
        quality_params = self.get_quality_parameters()
        
        prompt = f"""
        You are an expert content creator for 'Digital Codex' - a premium tech blog for software developers and tech leaders.
        
        **CONTENT MISSION:**
        Create engaging, high-value content that provides genuine insights and practical value.
        
        **TARGET AUDIENCE:**
        - Senior developers and tech leads
        - CTOs and engineering managers  
        - AI/ML practitioners
        - Tech entrepreneurs
        - Advanced developers seeking cutting-edge insights
        
        **TOPIC FOCUS:**
        {topic}
        
        **QUALITY LEVEL:** {self.quality.upper()}
        **CONTENT REQUIREMENTS:**
        - Length: {quality_params['min_chars']}-{quality_params['max_chars']} characters
        - Depth: {quality_params['depth']}
        - Structure: {quality_params['structure']}
        
        **CONTENT GUIDELINES:**
        - NO basic tutorials or common knowledge
        - FOCUS ON: Advanced techniques, industry insights, emerging trends
        - INCLUDE: Multiple code examples, real-world case studies, industry statistics
        - PROVIDE: Actionable insights and practical implementations
        - ADD: Expert perspectives and future predictions
        
        **STRUCTURE REQUIREMENTS:**
        - Compelling introduction with industry context
        - Multiple detailed sections with practical examples
        - Code snippets with thorough explanations
        - Real-world use cases and implementation strategies
        - Industry trends and market analysis
        - Future implications and recommendations
        - Actionable takeaways and next steps
        
        **EXISTING CATEGORIES:**
        {', '.join(existing_categories) if existing_categories else 'None'}
        
        **IMAGE REQUIREMENTS:**
        Create a detailed prompt for a professional, modern blog featured image.
        
        **OUTPUT FORMAT (JSON):**
        {{
            "title": "SEO-optimized, compelling title (50-60 characters)",
            "excerpt": "Engaging meta description (120-155 characters)",
            "content": "Comprehensive HTML content with proper tags",
            "category": "Specific, valuable category name",
            "image_prompt": "Detailed professional image prompt",
            "tags": ["relevant", "technical", "tags", "here", "5-7 tags"],
            "estimated_read_time": "X min read",
            "difficulty_level": "{self.quality}",
            "key_takeaways": ["actionable takeaway 1", "practical insight 2", "implementation tip 3"]
        }}
        
        **CRITICAL:** Content must be genuinely valuable, unique, and worth reading. Focus on advanced, practical insights.
        """

        try:
            time.sleep(3)  # Rate limiting
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=25000,
                    top_p=0.95,
                    top_k=40
                )
            )
            
            if not response.text:
                raise CommandError("Empty response from Gemini API")
            
            # Clean and parse JSON
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            ai_data = json.loads(cleaned_text)
            
            # Validate content
            if not self.validate_ai_content(ai_data, quality_params):
                return None
            
            return ai_data
            
        except json.JSONDecodeError as e:
            self.stdout.write(f"❌ JSON parsing error: {e}")
            return None
        except Exception as e:
            self.stdout.write(f"❌ AI generation error: {e}")
            return None

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
        """Get quality parameters based on selected quality level"""
        quality_configs = {
            'standard': {
                'min_chars': 8000,
                'max_chars': 12000,
                'depth': 'comprehensive with practical examples',
                'structure': 'well-organized with clear sections'
            },
            'premium': {
                'min_chars': 12000,
                'max_chars': 18000,
                'depth': 'expert-level with advanced techniques',
                'structure': 'detailed analysis with industry insights'
            },
            'expert': {
                'min_chars': 18000,
                'max_chars': 25000,
                'depth': 'cutting-edge with research-backed insights',
                'structure': 'comprehensive deep-dive with case studies'
            }
        }
        
        return quality_configs.get(self.quality, quality_configs['premium'])

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
        try:
            author = User.objects.get(username='admin')
        except User.DoesNotExist:
            author = User.objects.create_user(
                username='admin',
                email='admin@digitalcodex.com',
                first_name='Digital',
                last_name='Codex',
                is_staff=True,
                is_superuser=True
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
        """Generate a professional featured image for the post"""
        try:
            self.stdout.write(f"🎨 Generating image for: {post.title}")
            
            # Create professional gradient image
            width, height = 1200, 800
            image = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(image)
            
            # Professional color schemes
            color_schemes = [
                [(45, 55, 72), (66, 153, 225), (129, 230, 217)],  # Blue gradient
                [(74, 85, 104), (160, 174, 192), (237, 242, 247)],  # Gray gradient
                [(49, 130, 206), (76, 217, 100), (255, 235, 59)],  # Blue-green-yellow
                [(139, 69, 19), (255, 140, 0), (255, 215, 0)],  # Brown-orange-gold
                [(75, 0, 130), (138, 43, 226), (186, 85, 211)]  # Purple gradient
            ]
            
            colors = random.choice(color_schemes)
            
            # Create smooth gradient
            for i in range(height):
                ratio = i / height
                if ratio < 0.5:
                    blend_ratio = ratio * 2
                    r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * blend_ratio)
                    g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * blend_ratio)
                    b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * blend_ratio)
                else:
                    blend_ratio = (ratio - 0.5) * 2
                    r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * blend_ratio)
                    g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * blend_ratio)
                    b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * blend_ratio)
                
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            
            # Add geometric elements
            self.add_geometric_elements(draw, width, height)
            
            # Add title text
            self.add_title_text(draw, post.title, width, height)
            
            # Add branding
            self.add_branding(draw, width, height)
            
            # Save image
            image_buffer = BytesIO()
            image.save(image_buffer, format='PNG', quality=95, optimize=True)
            image_buffer.seek(0)
            
            image_name = f"{post.slug}.png"
            content_file = ContentFile(image_buffer.getvalue(), name=image_name)
            post.featured_image.save(image_name, content_file, save=True)
            
            self.stdout.write(f"✅ Professional image created (1200x800)")
            
        except Exception as e:
            self.stdout.write(f"❌ Image generation error: {str(e)}")

    def add_geometric_elements(self, draw, width, height):
        """Add geometric elements to the image"""
        # Add circles
        for _ in range(random.randint(3, 6)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            radius = random.randint(30, 100)
            alpha = random.randint(20, 60)
            
            # Create semi-transparent circles
            overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                               fill=(255, 255, 255, alpha))
        
        # Add lines
        for _ in range(random.randint(2, 4)):
            x1, y1 = random.randint(0, width), random.randint(0, height)
            x2, y2 = random.randint(0, width), random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 30), width=2)

    def add_title_text(self, draw, title, width, height):
        """Add title text to the image"""
        try:
            font = ImageFont.load_default()
            
            # Split title into lines
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                test_line = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > width - 200:
                    if len(current_line) > 1:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
                        current_line = []
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text with shadow
            line_height = 70
            total_height = len(lines) * line_height
            start_y = (height - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * line_height
                
                # Shadow
                draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 150), font=font)
                # Main text
                draw.text((x, y), line, fill='white', font=font)
                
        except Exception as e:
            self.stdout.write(f"⚠️ Text rendering error: {str(e)}")

    def add_branding(self, draw, width, height):
        """Add branding to the image"""
        try:
            font = ImageFont.load_default()
            brand_text = "Digital Codex"
            
            bbox = draw.textbbox((0, 0), brand_text, font=font)
            brand_width = bbox[2] - bbox[0]
            brand_x = width - brand_width - 50
            brand_y = height - 80
            
            # Shadow
            draw.text((brand_x + 2, brand_y + 2), brand_text, fill=(0, 0, 0, 100), font=font)
            # Main text
            draw.text((brand_x, brand_y), brand_text, fill=(255, 255, 255, 200), font=font)
            
        except Exception as e:
            self.stdout.write(f"⚠️ Branding error: {str(e)}")

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