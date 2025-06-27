# # Create a single post (tries Gemini → Free API → Placeholder)
# python manage.py ai_blog_generator create_post --topic "Advanced Django Patterns"

# # Create multiple posts with longer content
# python manage.py ai_blog_generator create_post --count 3

# # Create and publish immediately
# python manage.py ai_blog_generator create_post --publish --topic "AI in Web Development"

# # Skip image generation entirely
# python manage.py ai_blog_generator create_post --no-image
import os
import json
import time
from io import BytesIO
from PIL import Image
import requests

# Django Core Imports
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

# App-specific Imports
from blog.models import Post, Category

# Third-party Imports
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

# --- AI CONTENT GENERATION ---

@retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(3))
def get_ai_generated_content(existing_categories: list, topic: str = None) -> dict:
    """
    Generates blog post content (title, excerpt, content, category, and image prompt)
    from the Gemini AI, with retry logic for network resilience.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    category_list_str = ", ".join(f"'{cat}'" for cat in existing_categories) if existing_categories else "None"

    prompt = f"""
    You are an expert content creator for the 'Digital Codex' tech blog.
    Your audience is software developers and AI enthusiasts.
    Generate a complete, high-quality blog post.

    **Topic:**
    {'Generate a new, engaging, and specific blog post topic.' if not topic else f"Write about: '{topic}'."}

    **Category Assignment:**
    Existing categories: [{category_list_str}].
    Assign the most appropriate category. Create a new one only if necessary.

    **Content Requirements:**
    1.  **Title:** An engaging, SEO-friendly title.
    2.  **Excerpt:** A compelling plain text summary (~500 characters).
    3.  **Content:** A comprehensive HTML article (5000-20000 characters) using h2, h3, p, ul, li, and strong tags.
    4.  **Image Prompt:** A descriptive, artistic prompt for a text-to-image AI.

    **Output Format:**
    You MUST return your response as a single, valid JSON object.
    Schema: {{"title": "string", "excerpt": "string", "content": "string (HTML)", "category": "string", "image_prompt": "string"}}
    """

    print("\n🤖 Asking Gemini AI to generate a blog post...")
    try:
        # Add rate limiting for free tier
        time.sleep(2)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=16000,  # Increased for longer content
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
        
        print("✅ AI has successfully generated the content.")
        return ai_data
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Response text: {response.text[:500]}...")
        raise CommandError("Invalid JSON response from AI")
    except Exception as e:
        print(f"❌ An error occurred while interacting with the text generation AI: {e}")
        raise

# --- AI IMAGE GENERATION (Fallback chain: Gemini -> Free API -> Placeholder) ---

def generate_and_save_real_image(post: Post, prompt: str):
    """
    Try to generate image with Gemini first, then fallback to free API, then placeholder.
    """
    print(f"🎨 Attempting to generate image with Gemini for prompt: '{prompt}'...")
    
    # First try: Gemini image generation
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found")
            
        genai.configure(api_key=api_key)
        
        # Try using Gemini Pro Vision for image generation
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Note: Gemini doesn't directly generate images, but we'll try the approach
        # If this fails, we'll catch the exception and move to next method
        response = model.generate_content(
            contents=[f"Generate an image: {prompt}"],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="image/png"
            )
        )
        
        image_data = None
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    break
        
        if image_data:
            image_name = f"{post.slug}.png"
            content_file = ContentFile(image_data, name=image_name)
            post.featured_image.save(image_name, content_file, save=True)
            print(f"✅ Gemini image successfully generated and saved to post '{post.title}'.")
            return True
        else:
            raise Exception("No image data received from Gemini")
            
    except Exception as e:
        print(f"❌ Gemini image generation failed: {e}")
        print("🔄 Falling back to free API...")
        
        # Second try: Free API
        if generate_image_with_free_api(post, prompt):
            return True
        
        # Third try: Placeholder
        print("🔄 Falling back to placeholder image...")
        generate_placeholder_image(post, prompt)
        return True

def generate_placeholder_image(post: Post, prompt: str):
    """
    Creates a placeholder image as final fallback.
    """
    print(f"🎨 Creating placeholder image for prompt: '{prompt}'...")
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a 1080x720 image with a gradient background
        width, height = 1080, 720
        image = Image.new('RGB', (width, height), color='#1f2937')
        draw = ImageDraw.Draw(image)
        
        # Add a simple gradient effect
        for i in range(height):
            color_value = int(31 + (i / height) * 100)  # Gradient from dark to lighter
            draw.line([(0, i), (width, i)], fill=(color_value, color_value + 20, color_value + 40))
        
        # Add text overlay
        try:
            # Try to use a default font, fallback to default if not available
            font = ImageFont.load_default()
        except:
            font = None
        
        # Wrap text to fit image
        words = post.title.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > width - 80:  # Leave 40px margin on each side
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Center the text
        total_height = len(lines) * 40
        start_y = (height - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + i * 40
            draw.text((x, y), line, fill='white', font=font)
        
        # Save the image
        image_buffer = BytesIO()
        image.save(image_buffer, format='PNG')
        image_buffer.seek(0)
        
        image_name = f"{post.slug}.png"
        content_file = ContentFile(image_buffer.getvalue(), name=image_name)
        post.featured_image.save(image_name, content_file, save=True)
        
        print(f"✅ Placeholder image (1080x720) created and saved to post '{post.title}'.")
        
    except Exception as e:
        print(f"❌ Could not generate or save the placeholder image. Error: {e}")

# Alternative: Use a free image generation API
def generate_image_with_free_api(post: Post, prompt: str):
    """
    Use free image generation API as second fallback.
    Returns True if successful, False if failed.
    """
    print(f"🎨 Generating image with free API for prompt: '{prompt}'...")
    try:
        # Using Pollinations.ai (free, no API key required)
        encoded_prompt = requests.utils.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=720&nologo=true"
        
        # Add a small delay to be respectful to the free service
        time.sleep(2)
        
        response = requests.get(image_url, timeout=60)
        if response.status_code == 200:
            image_name = f"{post.slug}.jpg"
            content_file = ContentFile(response.content, name=image_name)
            post.featured_image.save(image_name, content_file, save=True)
            print(f"✅ Free API image (1080x720) generated and saved to post '{post.title}'.")
            return True
        else:
            print(f"❌ Free API failed. Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Could not generate image with free API. Error: {e}")
        return False

# --- DJANGO MANAGEMENT COMMAND ---

class Command(BaseCommand):
    help = 'Uses AI to generate a complete blog post with a featured image (optimized for free tier).'

    def add_arguments(self, parser):
        parser.add_argument('command', type=str, choices=['create_post'])
        parser.add_argument('--topic', type=str, help='(Optional) The topic for the AI to write about.')
        parser.add_argument('--author', type=str, help='(Optional) Username of the author. Defaults to the first superuser.')
        parser.add_argument('--count', type=int, default=1, help='Number of posts to create in one run.')
        parser.add_argument('--publish', action='store_true', help='If set, the generated post(s) will be published immediately.')
        parser.add_argument('--no-image', action='store_true', help='If set, skips the image generation step.')


    def handle(self, *args, **options):
        count = options['count']
        
        # Limit count for free tier to avoid hitting rate limits
        if count > 5:
            self.stdout.write(self.style.WARNING(f"Limiting count to 5 posts to respect free tier limits. You requested {count}."))
            count = 5
            
        self.stdout.write(self.style.HTTP_INFO(f"🚀 Starting AI content creation process for {count} post(s)..."))

        for i in range(count):
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Generating post {i + 1} of {count} ---"))
            try:
                self.create_single_post(options)
                # Add delay between posts to respect rate limits
                if i < count - 1:  # Don't sleep after the last post
                    self.stdout.write("⏳ Waiting 5 seconds before next post (rate limiting)...")
                    time.sleep(5)
            except (CommandError, Exception) as e:
                self.stderr.write(self.style.ERROR(f"Failed to create post {i + 1}: {e}"))

    def create_single_post(self, options):
        User = get_user_model()
        try:
            author_username = options.get('author')
            if author_username:
                author = User.objects.get(username=author_username)
            else:
                author = User.objects.filter(is_superuser=True).order_by('pk').first()
            if not author:
                raise CommandError("No author found. Create a superuser or specify one with --author.")
            self.stdout.write(f"✍️  Author set to: {author.username}")
        except User.DoesNotExist:
            raise CommandError(f"Author with username '{options.get('author')}' not found.")

        existing_categories = list(Category.objects.values_list('name', flat=True))
        ai_data = get_ai_generated_content(existing_categories, options.get('topic'))

        post_title = ai_data['title']
        if Post.objects.filter(title__iexact=post_title).exists():
            # Add timestamp to make title unique
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            post_title = f"{post_title} ({timestamp})"
            self.stdout.write(self.style.WARNING(f"Post title already exists. Modified to: '{post_title}'"))

        category_name = ai_data['category']
        category, created = Category.objects.get_or_create(
            name__iexact=category_name, defaults={'name': category_name}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created new category: '{category.name}'"))
        else:
            self.stdout.write(f"Using existing category: '{category.name}'")

        post_status = 'published' if options['publish'] else 'draft'
        new_post = Post.objects.create(
            title=post_title,
            author=author,
            content=ai_data['content'],
            excerpt=ai_data['excerpt'],
            status=post_status
        )
        new_post.categories.add(category)

        self.stdout.write(self.style.SUCCESS(f"Successfully created new {post_status.upper()} post: '{new_post.title}'"))

        if not options['no_image']:
            generate_and_save_real_image(new_post, ai_data['image_prompt'])
        else:
            self.stdout.write(self.style.WARNING("Skipping image generation as per --no-image flag."))