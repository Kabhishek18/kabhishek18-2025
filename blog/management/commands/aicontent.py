# python manage.py aicontent create_post --topic "The Impact of AI on UI/UX Design"
# python manage.py aicontent create_post
# python manage.py aicontent create_post --no-image
import os
import json
import base64
import requests
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.files.base import ContentFile
from blog.models import Post, Category
import google.generativeai as genai

def get_ai_generated_content(existing_categories: list, topic: str = None) -> dict:
    """
    Calls the Google Gemini API to generate structured blog content.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    category_list_str = ", ".join(f"'{cat}'" for cat in existing_categories) if existing_categories else "None"

    prompt = f"""
    You are an expert content creator for the 'Digital Codex' tech blog. Your audience is software developers and AI enthusiasts.
    Generate a complete, high-quality blog post.
    **Topic:** {'Generate a new, engaging, and specific blog post topic.' if not topic else f"Write about: '{topic}'."}
    **Category Assignment:** Existing categories: [{category_list_str}]. Assign the most appropriate category. Create a new one only if necessary.
    **Content Requirements:**
    1.  **Title:** An engaging, SEO-friendly title.
    2.  **Excerpt:** A compelling plain text summary (~500 characters).
    3.  **Content:** A comprehensive HTML article (5000-20000 characters) with h2, h3, p, ul, li, and strong tags.
    4.  **Image Prompt:** A descriptive, artistic prompt for a text-to-image AI like Stability Diffusion. Focus on concepts, not just literal descriptions.
    **Output Format:** You MUST return your response as a single, valid JSON object.
    Schema: {{"title": "string", "excerpt": "string", "content": "string (HTML)", "category": "string", "image_prompt": "string"}}
    """
    
    print("\n🤖 Asking Gemini AI to generate a blog post...")
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_data = json.loads(cleaned_response_text)
        print("✅ AI has successfully generated the content.")
        return ai_data
    except Exception as e:
        raise CommandError(f"Failed to get a valid response from the Gemini AI: {e}")

def generate_image_with_stabilityai(post: Post, prompt: str):
    """
    Generates an image using the Stability AI API and saves it to the Post.
    """
    api_key = os.getenv("STABILITY_API_KEY")
    if not api_key:
        raise CommandError("STABILITY_API_KEY environment variable not found.")

    print(f"🎨 Requesting image from Stability AI for prompt: '{prompt}'...")
    
    api_host = 'https://api.stability.ai'
    engine_id = 'stable-diffusion-v1-6'
    
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 512,
            "width": 1024, # Widescreen for blog headers
            "samples": 1,
            "steps": 30,
        },
    )

    if response.status_code != 200:
        raise CommandError(f"Stability AI non-200 response: {response.text}")

    data = response.json()
    
    try:
        image_base64 = data["artifacts"][0]["base64"]
        image_data = base64.b64decode(image_base64)
        
        image_name = f"{post.slug}.png"
        content_file = ContentFile(image_data, name=image_name)
        
        post.featured_image.save(image_name, content_file, save=True)
        print(f"✅ Image successfully generated and saved to post '{post.title}'.")
    except (KeyError, IndexError) as e:
        raise CommandError(f"Could not find image data in Stability AI response: {e}")
    except Exception as e:
        raise CommandError(f"Could not save the generated image. Error: {e}")


class Command(BaseCommand):
    help = 'Uses AI to generate blog content and a real featured image via Stability AI.'

    def add_arguments(self, parser):
        parser.add_argument('command', type=str, choices=['create_post'])
        parser.add_argument('--topic', type=str, help='(Optional) The topic for the AI to write about.')
        parser.add_argument('--author', type=str, help='(Optional) Username of the author.')
        parser.add_argument('--count', type=int, default=1, help='Number of posts to create.')
        parser.add_argument('--publish', action='store_true', help='Publish the post(s) immediately.')
        parser.add_argument('--no-image', action='store_true', help='Skip the image generation step.')

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(self.style.HTTP_INFO(f"🚀 Starting AI content pipeline for {count} post(s)..."))
        
        for i in range(count):
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Generating post {i + 1} of {count} ---"))
            try:
                self.create_post(options)
            except (CommandError, Exception) as e:
                self.stderr.write(self.style.ERROR(f"Failed to create post {i + 1}: {e}"))

    def create_post(self, options):
        User = get_user_model()
        try:
            author = User.objects.get(username=options.get('author')) if options.get('author') else User.objects.filter(is_superuser=True).first()
            if not author: raise CommandError("No author found.")
            self.stdout.write(f"✍️  Author set to: {author.username}")
        except User.DoesNotExist:
            raise CommandError(f"Author '{options.get('author')}' not found.")

        existing_categories = list(Category.objects.values_list('name', flat=True))
        ai_data = get_ai_generated_content(existing_categories, options.get('topic'))
        
        if Post.objects.filter(title__iexact=ai_data['title']).exists():
            raise CommandError(f"Post with title '{ai_data['title']}' already exists. Skipping.")

        category, _ = Category.objects.get_or_create(name__iexact=ai_data['category'], defaults={'name': ai_data['category']})
        
        post_status = 'draft' if options['publish'] else 'draft'
        new_post = Post.objects.create(
            title=ai_data['title'],
            author=author,
            content=ai_data['content'],
            excerpt=ai_data['excerpt'],
            status=post_status
        )
        new_post.categories.add(category)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created new {post_status.upper()} post: '{new_post.title}'"))
        
        if not options['no_image']:
            generate_image_with_stabilityai(new_post, ai_data['image_prompt'])
        else:
            self.stdout.write(self.style.WARNING("Skipping image generation as per --no-image flag."))
