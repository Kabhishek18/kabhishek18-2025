import os,re
import json
import time
from io import BytesIO
from PIL import Image
import requests
import random
from datetime import datetime, timedelta

# Django Core Imports
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

# App-specific Imports
from blog.models import Post, Category

# Third-party Imports
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

# Dynamic content configuration - can be stored in DB or external config
class ContentTopicsManager:
    """
    Dynamic content topics manager that fetches trending topics from various sources
    """
    
    def __init__(self):
        self.cache_duration = 3600  # 1 hour cache
        self.last_update = None
        self.cached_topics = {}
        
    def get_trending_topics_from_web(self):
        """
        Fetch trending topics from various tech sources
        """
        trending_data = {}
        
        try:
            # GitHub Trending Topics
            github_trends = self.fetch_github_trends()
            if github_trends:
                trending_data['github_trends'] = github_trends
                
            # Hacker News Trending
            hn_trends = self.fetch_hackernews_trends()
            if hn_trends:
                trending_data['hackernews_trends'] = hn_trends
                
            # Reddit Programming Trends
            reddit_trends = self.fetch_reddit_programming_trends()
            if reddit_trends:
                trending_data['reddit_trends'] = reddit_trends
                
            # Stack Overflow Trends
            so_trends = self.fetch_stackoverflow_trends()
            if so_trends:
                trending_data['stackoverflow_trends'] = so_trends
                
        except Exception as e:
            print(f"⚠️ Error fetching web trends: {e}")
            
        return trending_data
    
    def fetch_github_trends(self):
        """Fetch trending repositories and topics from GitHub"""
        try:
            # GitHub trending repositories API
            url = "https://api.github.com/search/repositories?q=created:>2024-01-01&sort=stars&order=desc&per_page=20"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                topics = []
                
                for repo in data.get('items', [])[:10]:
                    # Extract topics from repo description and topics
                    repo_topics = repo.get('topics', [])
                    topics.extend(repo_topics)
                    
                    # Extract keywords from description
                    description = repo.get('description', '')
                    if description:
                        # Simple keyword extraction
                        keywords = self.extract_tech_keywords(description)
                        topics.extend(keywords)
                
                return list(set(topics))[:15]  # Return unique topics
                
        except Exception as e:
            print(f"GitHub trends fetch error: {e}")
            return []
    
    def fetch_hackernews_trends(self):
        """Fetch trending topics from Hacker News"""
        try:
            # HN Top Stories API
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                story_ids = response.json()[:20]  # Top 20 stories
                topics = []
                
                for story_id in story_ids[:10]:  # Limit to 10 to avoid rate limits
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_response = requests.get(story_url, timeout=5)
                    
                    if story_response.status_code == 200:
                        story = story_response.json()
                        title = story.get('title', '')
                        
                        # Extract tech keywords from title
                        keywords = self.extract_tech_keywords(title)
                        topics.extend(keywords)
                    
                    time.sleep(0.1)  # Rate limiting
                
                return list(set(topics))[:10]
                
        except Exception as e:
            print(f"Hacker News trends fetch error: {e}")
            return []
    
    def fetch_reddit_programming_trends(self):
        """Fetch trending topics from Reddit programming communities"""
        try:
            # Reddit hot posts (no auth needed for public endpoints)
            subreddits = ['programming', 'MachineLearning', 'webdev', 'Python', 'javascript']
            topics = []
            
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10"
                headers = {'User-Agent': 'BlogGenerator/1.0'}
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        title = post.get('data', {}).get('title', '')
                        keywords = self.extract_tech_keywords(title)
                        topics.extend(keywords)
                
                time.sleep(0.5)  # Rate limiting
            
            return list(set(topics))[:15]
            
        except Exception as e:
            print(f"Reddit trends fetch error: {e}")
            return []
    
    def fetch_stackoverflow_trends(self):
        """Fetch trending tags from Stack Overflow"""
        try:
            # Stack Overflow API for trending tags
            url = "https://api.stackexchange.com/2.3/tags?order=desc&sort=popular&site=stackoverflow&pagesize=30"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                tags = []
                
                for item in data.get('items', []):
                    tag_name = item.get('name', '')
                    if self.is_tech_relevant(tag_name):
                        tags.append(tag_name.replace('-', ' ').title())
                
                return tags[:20]
                
        except Exception as e:
            print(f"Stack Overflow trends fetch error: {e}")
            return []
    
    def extract_tech_keywords(self, text):
        """Extract technology-related keywords from text"""
        tech_patterns = [
            r'\b(AI|ML|Machine Learning|Deep Learning|Neural Network)\b',
            r'\b(React|Vue|Angular|Node\.js|Django|Flask|FastAPI)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins)\b',
            r'\b(Python|JavaScript|TypeScript|Rust|Go|Java)\b',
            r'\b(Blockchain|Cryptocurrency|DeFi|NFT|Web3)\b',
            r'\b(DevOps|CI/CD|Microservices|Serverless|API)\b',
            r'\b(Quantum|IoT|Edge Computing|5G|AR|VR)\b',
            r'\b(Cybersecurity|Privacy|GDPR|Compliance)\b'
        ]
        
        keywords = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        return [kw.strip() for kw in keywords if len(kw.strip()) > 2]
    
    def is_tech_relevant(self, tag):
        """Check if a tag is technology-relevant"""
        tech_keywords = {
            'python', 'javascript', 'java', 'c++', 'rust', 'go', 'typescript',
            'react', 'vue', 'angular', 'node.js', 'django', 'flask',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'machine-learning', 'ai', 'deep-learning', 'neural-networks',
            'blockchain', 'cryptocurrency', 'web3', 'defi',
            'cybersecurity', 'privacy', 'devops', 'cicd'
        }
        
        return tag.lower() in tech_keywords or any(kw in tag.lower() for kw in tech_keywords)
    
    def get_ai_generated_topics(self):
        """
        Use AI to generate trending topics based on current tech landscape
        """
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return {}
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            prompt = f"""
            Based on the current tech landscape as of {current_date}, generate trending topics for a tech blog.
            
            Consider these areas:
            1. Latest AI/ML developments and breakthroughs
            2. Emerging programming languages and frameworks
            3. Cloud computing and DevOps trends
            4. Web3 and blockchain innovations
            5. Cybersecurity and privacy concerns
            6. Mobile and web development trends
            7. IoT and edge computing
            8. Sustainable tech and green computing
            
            Return a JSON object with categories and trending topics:
            {{
                "ai_ml": ["topic1", "topic2", ...],
                "web_dev": ["topic1", "topic2", ...],
                "cloud_devops": ["topic1", "topic2", ...],
                "blockchain": ["topic1", "topic2", ...],
                "cybersecurity": ["topic1", "topic2", ...],
                "emerging_tech": ["topic1", "topic2", ...]
            }}
            
            Focus on topics that are:
            - Currently trending (last 3-6 months)
            - Practically relevant to developers
            - Not basic tutorials but advanced insights
            - Industry-focused and valuable
            """
            
            response = model.generate_content(prompt)
            
            if response.text:
                try:
                    clean_text = response.text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    
                    ai_topics = json.loads(clean_text.strip())
                    return ai_topics
                    
                except json.JSONDecodeError:
                    print("⚠️ Failed to parse AI-generated topics")
                    return {}
            
        except Exception as e:
            print(f"⚠️ AI topic generation error: {e}")
            return {}
    
    def get_dynamic_topics(self, force_refresh=False):
        """
        Get trending topics from multiple sources with caching
        """
        current_time = time.time()
        
        # Check cache validity
        if (not force_refresh and 
            self.last_update and 
            current_time - self.last_update < self.cache_duration and 
            self.cached_topics):
            print("📋 Using cached trending topics")
            return self.cached_topics
        
        print("🔄 Fetching fresh trending topics...")
        
        # Combine multiple sources
        all_topics = {}
        
        # 1. Web scraping trends
        web_trends = self.get_trending_topics_from_web()
        if web_trends:
            all_topics.update(web_trends)
        
        # 2. AI-generated trends
        ai_trends = self.get_ai_generated_topics()
        if ai_trends:
            all_topics.update(ai_trends)
        
        # 3. Fallback to curated topics if all else fails
        if not all_topics:
            all_topics = self.get_fallback_topics()
        
        # Cache the results
        self.cached_topics = all_topics
        self.last_update = current_time
        
        return all_topics
    
    def get_fallback_topics(self):
        """Fallback curated topics when dynamic fetching fails"""
        return {
            'ai_ml': [
                'Large Language Models in Production', 'AI Ethics and Bias Mitigation',
                'Generative AI for Code Development', 'Machine Learning Operations at Scale',
                'Neural Architecture Search Advances', 'AI-Powered Developer Tools'
            ],
            'web_dev': [
                'Server-Side Rendering Evolution', 'Progressive Web Apps 2024',
                'Frontend Performance Optimization', 'API Design Best Practices',
                'Modern CSS Architecture', 'JavaScript Runtime Innovations'
            ],
            'cloud_devops': [
                'Multi-Cloud Strategy Implementation', 'Serverless Architecture Patterns',
                'Container Security Best Practices', 'Infrastructure as Code Evolution',
                'DevOps Culture Transformation', 'Cost Optimization Strategies'
            ],
            'blockchain': [
                'Enterprise Blockchain Applications', 'DeFi Security Auditing',
                'NFT Technology Beyond Art', 'Blockchain Scalability Solutions',
                'Web3 Development Frameworks', 'Cryptocurrency Integration'
            ],
            'cybersecurity': [
                'Zero Trust Architecture Implementation', 'Cloud Security Posture',
                'AI-Powered Threat Detection', 'DevSecOps Integration',
                'Privacy-Preserving Technologies', 'Incident Response Automation'
            ],
            'emerging_tech': [
                'Quantum Computing Applications', 'Edge AI Development',
                'IoT Security Challenges', 'Sustainable Software Architecture',
                'Augmented Reality in Enterprise', 'Voice Interface Evolution'
            ]
        }

# Initialize the dynamic content manager
content_manager = ContentTopicsManager()

# Content depth levels
CONTENT_DEPTHS = {
    'beginner': {
        'min_chars': 8000,
        'max_chars': 12000,
        'complexity': 'accessible to newcomers',
        'structure': 'step-by-step with examples'
    },
    'intermediate': {
        'min_chars': 12000,
        'max_chars': 18000,
        'complexity': 'moderate technical depth',
        'structure': 'detailed analysis with practical applications'
    },
    'advanced': {
        'min_chars': 18000,
        'max_chars': 25000,
        'complexity': 'expert-level technical content',
        'structure': 'comprehensive deep-dive with advanced concepts'
    }
}

def get_trending_topic():
    """Get a dynamic trending topic from various sources"""
    try:
        # Get dynamic topics
        dynamic_topics = content_manager.get_dynamic_topics()
        
        if dynamic_topics:
            # Choose a random category
            category = random.choice(list(dynamic_topics.keys()))
            topics_list = dynamic_topics[category]
            
            if topics_list:
                topic = random.choice(topics_list)
                return topic, category
        
        # Fallback to curated topics
        fallback_topics = content_manager.get_fallback_topics()
        category = random.choice(list(fallback_topics.keys()))
        topic = random.choice(fallback_topics[category])
        return topic, category
        
    except Exception as e:
        print(f"⚠️ Error getting trending topic: {e}")
        # Ultimate fallback
        return "Advanced Software Architecture Patterns", "practical_guides"

def get_content_angle():
    """Get a unique content angle to avoid repetitive content"""
    angles = [
        'comprehensive guide', 'industry analysis', 'future predictions',
        'case study analysis', 'comparative review', 'best practices',
        'implementation strategy', 'troubleshooting guide', 'optimization techniques',
        'security considerations', 'performance analysis', 'cost-benefit analysis',
        'real-world applications', 'expert insights', 'trend analysis'
    ]
    return random.choice(angles)

def get_content_depth():
    """Randomly select content depth level"""
    depths = list(CONTENT_DEPTHS.keys())
    weights = [0.3, 0.5, 0.2]  # Favor intermediate content
    return random.choices(depths, weights=weights)[0]

@retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(3))
def get_ai_generated_content(existing_categories: list, topic: str = None, force_variety: bool = True) -> dict:
    """
    Enhanced AI content generation with better variety and quality controls
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Get content parameters
    if not topic:
        trending_topic, trend_category = get_trending_topic()
        content_angle = get_content_angle()
        topic = f"{trending_topic}: {content_angle}"
    
    depth_level = get_content_depth()
    depth_config = CONTENT_DEPTHS[depth_level]
    
    # Enhanced category selection
    category_list_str = ", ".join(f"'{cat}'" for cat in existing_categories) if existing_categories else "None"
    
    # Get recent posts to avoid repetition
    recent_topics_context = "Ensure this content is unique and doesn't repeat common tutorial topics like 'how to install Python' or 'basic error handling guides'."

    prompt = f"""
    You are an expert content creator for 'Digital Codex' - a premium tech blog for software developers, tech leaders, and AI enthusiasts.
    
    **CONTENT MISSION:**
    Create engaging, subscriber-worthy content that provides genuine value and unique insights.
    
    **TARGET AUDIENCE:**
    - Experienced developers and tech professionals
    - CTO/Tech leads making strategic decisions  
    - AI/ML practitioners and researchers
    - Entrepreneurs in the tech space
    - Advanced students and career switchers
    
    **TOPIC FOCUS:**
    {topic}
    
    **CONTENT REQUIREMENTS:**
    1. **Depth Level:** {depth_level.title()} ({depth_config['complexity']})
    2. **Content Length:** {depth_config['min_chars']}-{depth_config['max_chars']} characters
    3. **Structure:** {depth_config['structure']}
    4. **Uniqueness:** {recent_topics_context}
    
    **STRICT CONTENT GUIDELINES:**
    - NO basic tutorials (how to install X, basic error handling, etc.)
    - NO rehashed common knowledge
    - FOCUS ON: Industry insights, emerging trends, advanced techniques, real-world case studies
    - INCLUDE: Multiple code examples, diagrams descriptions, practical implementations
    - ADD: Industry statistics, expert quotes, future predictions
    - PROVIDE: Actionable insights that readers can implement immediately
    
    **ENHANCED STRUCTURE:**
    - Compelling introduction with hook
    - Multiple detailed sections with subheadings
    - Code examples with explanations
    - Real-world use cases and examples
    - Industry context and market insights
    - Future implications and trends
    - Actionable takeaways and next steps
    - Resource recommendations
    
    **EXISTING CATEGORIES:**
    [{category_list_str}]
    Choose the most appropriate category or create a new one that's specific and valuable.
    
    **IMAGE REQUIREMENTS:**
    Create a detailed, artistic prompt for a professional blog featured image that represents the content visually.
    
    **OUTPUT FORMAT (JSON):**
    {{
        "title": "Compelling, SEO-optimized title (avoid generic terms)",
        "excerpt": "Engaging summary that makes readers want to read more (400-600 chars)",
        "content": "Comprehensive HTML content with h2, h3, p, ul, li, strong, code, pre tags",
        "category": "Specific, valuable category name",
        "image_prompt": "Detailed prompt for professional blog image",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "estimated_read_time": "X min read",
        "difficulty_level": "{depth_level}",
        "key_takeaways": ["takeaway1", "takeaway2", "takeaway3"]
    }}
    
    **CRITICAL:** Ensure content is genuinely valuable, unique, and worth subscribing for. Avoid tutorial-style content unless it covers advanced, cutting-edge techniques.
    """

    print(f"\n🤖 Generating {depth_level}-level content about: {topic}")
    try:
        # Add rate limiting for free tier
        time.sleep(3)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.8,  # Increased for more creativity
                max_output_tokens=20000,  # Increased for longer content
                top_p=0.95,
                top_k=40
            )
        )
        
        if not response.text:
            raise CommandError("Empty response from Gemini API")
            
        cleaned_response_text = response.text.strip()
        # Remove markdown code blocks if present
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        cleaned_response_text = cleaned_response_text.strip()
        
        ai_data = json.loads(cleaned_response_text)
        
        # Validate required fields
        required_fields = ['title', 'excerpt', 'content', 'category', 'image_prompt']
        for field in required_fields:
            if field not in ai_data or not ai_data[field]:
                raise CommandError(f"Missing or empty field: {field}")
        
        # Validate content length
        content_length = len(ai_data['content'])
        if content_length < depth_config['min_chars']:
            print(f"⚠️  Content too short ({content_length} chars), requesting expansion...")
            return expand_content(ai_data, depth_config, topic)
        
        print(f"✅ Generated {depth_level} content ({content_length} chars)")
        return ai_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Response text: {response.text[:500]}...")
        raise CommandError("Invalid JSON response from AI")
    except Exception as e:
        print(f"❌ Error in content generation: {e}")
        raise

def expand_content(ai_data: dict, depth_config: dict, topic: str) -> dict:
    """Expand content if it's too short"""
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    expansion_prompt = f"""
    The following blog post content needs to be expanded to meet quality standards.
    
    **Current Content:** {ai_data['content']}
    
    **Requirements:**
    - Expand to {depth_config['min_chars']}-{depth_config['max_chars']} characters
    - Add more detailed examples and code snippets
    - Include additional sections with practical applications
    - Add industry insights and real-world case studies
    - Maintain the same topic focus: {topic}
    
    Return the expanded content in the same JSON format, keeping all existing fields but with enhanced content.
    """
    
    try:
        response = model.generate_content(expansion_prompt)
        expanded_data = json.loads(response.text.strip())
        return expanded_data
    except:
        # If expansion fails, return original
        return ai_data

def generate_enhanced_placeholder_image(post: Post, prompt: str):
    """
    Creates a more professional placeholder image with better design
    """
    print(f"🎨 Creating enhanced placeholder image...")
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
        
        print(f"✅ Enhanced placeholder image (1200x800) created and saved.")
        
    except Exception as e:
        print(f"❌ Could not generate enhanced placeholder image. Error: {e}")
        # Fallback to simple placeholder
        generate_simple_placeholder(post)

def generate_simple_placeholder(post: Post):
    """Simple fallback placeholder"""
    try:
        from PIL import Image, ImageDraw
        
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
        print(f"❌ Simple placeholder failed: {e}")

def generate_and_save_real_image(post: Post, prompt: str):
    """
    Enhanced image generation with better prompts and fallbacks
    """
    print(f"🎨 Generating professional image for: '{prompt}'...")
    
    # Enhanced prompt for better images
    enhanced_prompt = f"Professional blog featured image, modern design, technology theme, high quality, detailed: {prompt}. Style: clean, minimalist, professional, tech-focused, vibrant colors, 1200x800 aspect ratio"
    
    # Try free API first (more reliable)
    if generate_image_with_free_api(post, enhanced_prompt):
        return True
    
    # Fallback to enhanced placeholder
    generate_enhanced_placeholder_image(post, prompt)
    return True

def generate_image_with_free_api(post: Post, prompt: str):
    """
    Enhanced free API image generation with better services
    """
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
            print(f"🎨 Trying {api['name']}...")
            time.sleep(api['delay'])
            
            image_url = api['url'](prompt)
            response = requests.get(image_url, timeout=60)
            
            if response.status_code == 200:
                image_name = f"{post.slug}.jpg"
                content_file = ContentFile(response.content, name=image_name)
                post.featured_image.save(image_name, content_file, save=True)
                print(f"✅ {api['name']} image generated successfully.")
                return True
            else:
                print(f"❌ {api['name']} failed. Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {api['name']} error: {e}")
            continue
    
    return False

class Command(BaseCommand):
    help = 'Enhanced AI blog generator with improved content quality and variety'

    def add_arguments(self, parser):
        parser.add_argument('command', type=str, choices=['create_post'])
        parser.add_argument('--topic', type=str, help='Specific topic (will be enhanced with trending angles)')
        parser.add_argument('--author', type=str, help='Username of the author')
        parser.add_argument('--count', type=int, default=1, help='Number of posts to create')
        parser.add_argument('--publish', action='store_true', help='Publish immediately')
        parser.add_argument('--no-image', action='store_true', help='Skip image generation')
        parser.add_argument('--depth', type=str, choices=['beginner', 'intermediate', 'advanced'], 
                          help='Force specific content depth level')
        parser.add_argument('--trending', action='store_true', help='Use only trending topics')
        parser.add_argument('--refresh-topics', action='store_true', help='Force refresh of trending topics cache')
        parser.add_argument('--source', type=str, choices=['web', 'ai', 'mixed'], default='mixed',
                          help='Source for trending topics: web scraping, AI generation, or mixed')

    def handle(self, *args, **options):
        count = min(options['count'], 10)  # Limit to 10 for safety
        
        # Refresh topics cache if requested
        if options.get('refresh_topics'):
            self.stdout.write(self.style.HTTP_INFO("🔄 Refreshing trending topics cache..."))
            content_manager.get_dynamic_topics(force_refresh=True)
            self.stdout.write(self.style.SUCCESS("✅ Topics cache refreshed!"))
        
        # Show current trending topics
        if options.get('trending') or options.get('refresh_topics'):
            self.show_trending_topics()
        
        self.stdout.write(self.style.HTTP_INFO(f"🚀 Creating {count} high-quality blog post(s)..."))
        
        successful_posts = 0
        for i in range(count):
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Creating post {i + 1} of {count} ---"))
            try:
                if self.create_single_post(options):
                    successful_posts += 1
                    
                # Rate limiting
                if i < count - 1:
                    delay = random.randint(5, 10)
                    self.stdout.write(f"⏳ Waiting {delay} seconds (rate limiting)...")
                    time.sleep(delay)
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to create post {i + 1}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully created {successful_posts} out of {count} posts!"))

    def show_trending_topics(self):
        """Display current trending topics"""
        try:
            topics = content_manager.get_dynamic_topics()
            
            self.stdout.write(self.style.HTTP_INFO("\n📈 Current Trending Topics:"))
            for category, topic_list in topics.items():
                self.stdout.write(f"\n🏷️  {category.replace('_', ' ').title()}:")
                for topic in topic_list[:5]:  # Show top 5
                    self.stdout.write(f"   • {topic}")
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Could not display trending topics: {e}"))

    def create_single_post(self, options):
        User = get_user_model()
        
        # Get author
        try:
            author_username = options.get('author')
            if author_username:
                author = User.objects.get(username=author_username)
            else:
                author = User.objects.filter(is_superuser=True).first()
            if not author:
                raise CommandError("No author found")
        except User.DoesNotExist:
            raise CommandError(f"Author '{author_username}' not found")

        # Get existing categories
        existing_categories = list(Category.objects.values_list('name', flat=True))
        
        # Generate content
        topic = options.get('topic')
        if options.get('trending') and not topic:
            topic = None  # Let the system choose trending topics
            
        ai_data = get_ai_generated_content(existing_categories, topic)

        # Handle duplicate titles
        post_title = ai_data['title']
        counter = 1
        original_title = post_title
        while Post.objects.filter(title__iexact=post_title).exists():
            post_title = f"{original_title} - Part {counter}"
            counter += 1

        # Create or get category
        category_name = ai_data['category']
        category, created = Category.objects.get_or_create(
            name__iexact=category_name, 
            defaults={'name': category_name}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✨ Created new category: '{category.name}'"))

        # Create post
        post_status = 'published' if options['publish'] else 'draft'
        new_post = Post.objects.create(
            title=post_title,
            author=author,
            content=ai_data['content'],
            excerpt=ai_data['excerpt'],
            status=post_status
        )
        new_post.categories.add(category)

        # Add tags if available
        if 'tags' in ai_data and ai_data['tags']:
            # Assuming you have a tags field or model
            pass

        self.stdout.write(self.style.SUCCESS(f"📝 Created {post_status}: '{new_post.title}'"))
        self.stdout.write(f"📊 Content length: {len(ai_data['content'])} characters")
        
        if 'difficulty_level' in ai_data:
            self.stdout.write(f"🎯 Difficulty: {ai_data['difficulty_level']}")

        # Generate image
        if not options['no_image']:
            generate_and_save_real_image(new_post, ai_data['image_prompt'])

        return True