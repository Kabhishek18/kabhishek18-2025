# python manage.py aicontent create_post --topic "The Impact of AI on UI/UX Design"
# python manage.py aicontent create_post
# python manage.py aicontent create_post --no-image
import os
import json
from io import BytesIO
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.files.base import ContentFile
from blog.models import Post, Category
import google.generativeai as genai
from google.generativeai import types
from google import genai as new_genai
from google.genai import types as new_types
from PIL import Image

def get_ai_generated_content(existing_categories: list, topic: str = None, existing_titles: list = None) -> dict:
    """
    Calls the Google Gemini API to generate structured blog content,
    avoiding previously generated titles.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    category_list_str = ", ".join(f"'{cat}'" for cat in existing_categories) if existing_categories else "None"
    existing_titles_str = ", ".join(f'"{title}"' for title in existing_titles) if existing_titles else "None"

    prompt = f"""
    You are an expert content creator for the 'Digital Codex' tech blog. Your audience is software developers and AI enthusiasts.
    Generate a complete, high-quality blog post.

    **Topic:**
    {'Generate a new, engaging, and specific blog post topic related to artificial intelligence, machine learning, or modern software development trends.' if not topic else f"Write about: '{topic}'."}
    IMPORTANT: Do not generate a topic with a title that is similar to any of these existing post titles: [{existing_titles_str}].

    **Category Assignment:**
    Existing categories: [{category_list_str}]. Assign the most appropriate category. Create a new one only if necessary.

    **Content Requirements:**
    1.  **Title:** An engaging, SEO-friendly title that is distinct from the existing titles provided.
    2.  **Excerpt:** A compelling plain text summary (~500 characters).
    3.  **Content:** A comprehensive HTML article (5000-20000 characters) with h2, h3, p, ul, li, and strong tags.
    4.  **Image Prompt:** A descriptive, artistic prompt for a text-to-image AI like Gemini. Focus on concepts, not just literal descriptions.

    **Output Format:**
    You MUST return your response as a single, valid JSON object.
    Schema: {{"title": "string", "excerpt": "string", "content": "string (HTML)", "category": "string", "image_prompt": "string"}}
    """
    
    print("\n🤖 Asking Gemini AI to generate a blog post...")
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_data = json.loads(cleaned_response_text)
        print("✅ AI has successfully generated the text content.")
        return ai_data
    except Exception as e:
        raise CommandError(f"Failed to get a valid response from the Gemini AI for text generation: {e}")

def generate_image_with_gemini(post: Post, prompt: str):
    """
    Generates an image using the new Gemini 2.0 Image Generation API and saves it to the Post.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found.")
    
    print(f"🎨 Requesting image from Gemini 2.0 for prompt: '{prompt[:100]}...'")
    
    try:
        # Initialize the new genai client
        client = new_genai.Client(api_key=api_key)
        
        # Create a more detailed image prompt
        full_image_prompt = f"{prompt}, high quality, professional, widescreen aspect ratio, modern tech aesthetic"
        
        # Generate content with both text and image modalities
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=full_image_prompt,
            config=new_types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        # Extract image data from response
        image_saved = False
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # Convert the image data to PIL Image
                image = Image.open(BytesIO(part.inline_data.data))
                
                # Convert PIL Image to bytes for Django file handling
                img_buffer = BytesIO()
                image.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # Save to Django model
                image_name = f"{post.slug}.png"
                if post.featured_image:
                    post.featured_image.delete(save=False)
                post.featured_image.save(
                    image_name, 
                    ContentFile(img_buffer.getvalue()), 
                    save=True
                )
                
                print(f"✅ Image successfully generated and saved to post '{post.title}'.")
                image_saved = True
                break
        
        if not image_saved:
            raise Exception("No image data received from Gemini response")
            
    except Exception as e:
        print(f"⚠️  Could not generate image using Gemini 2.0: {e}")
        print("   Continuing without featured image...")
        # Don't raise CommandError here, just log and continue


class Command(BaseCommand):
    help = 'Uses Gemini AI to generate blog content and a featured image.'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", required=True)
        parser_create = subparsers.add_parser("create_post", help="Create a new blog post using AI.")
        parser_create.add_argument('--topic', type=str, help='(Optional) The topic for the AI to write about.')
        parser_create.add_argument('--author', type=str, help='(Optional) Username of the author.')
        parser_create.add_argument('--count', type=int, default=1, help='Number of posts to create.')
        parser_create.add_argument('--publish', action='store_true', help='Publish the post(s) immediately.')
        parser_create.add_argument('--no-image', action='store_true', help='Skip the image generation step.')
        parser_update = subparsers.add_parser("update_image", help="Regenerate the featured image for an existing post.")
        parser_update.add_argument('--slug', type=str, required=True, help='The slug of the blog post to update.')

    def handle(self, *args, **options):
        command = options['command']
        if command == 'create_post':
            self.create_post_workflow(options)
        elif command == 'update_image':
            self.update_post_image(options['slug'])
            
    def create_post_workflow(self, options):
        count = options['count']
        self.stdout.write(self.style.HTTP_INFO(f"🚀 Starting AI content pipeline for {count} post(s)..."))
        # This set will track titles generated within this single run
        generated_titles_this_run = set()
        successful_posts = 0
        
        for i in range(count):
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Generating post {i + 1} of {count} ---"))
            try:
                # Pass the set of titles to the creation function
                new_title = self.create_post(options, generated_titles_this_run)
                if new_title:
                    generated_titles_this_run.add(new_title)
                    successful_posts += 1
            except (CommandError, Exception) as e:
                self.stderr.write(self.style.ERROR(f"Failed to create post {i + 1}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully created {successful_posts} out of {count} requested posts."))

    def create_post(self, options, generated_titles_this_run):
        User = get_user_model()
        try:
            author = User.objects.get(username=options.get('author')) if options.get('author') else User.objects.filter(is_superuser=True).first()
            if not author: 
                raise CommandError("No author found. Please specify --author or ensure a superuser exists.")
            self.stdout.write(f"✍️  Author set to: {author.username}")
        except User.DoesNotExist:
            raise CommandError(f"Author '{options.get('author')}' not found.")

        # Get recent post titles from DB to avoid duplication across runs
        db_titles = set(Post.objects.order_by('-created_at').values_list('title', flat=True)[:50])
        # Combine with titles generated in this specific run
        all_existing_titles = db_titles.union(generated_titles_this_run)

        existing_categories = list(Category.objects.values_list('name', flat=True))
        ai_data = get_ai_generated_content(existing_categories, options.get('topic'), list(all_existing_titles))
        
        post_title = ai_data['title']
        if Post.objects.filter(title__iexact=post_title).exists():
            raise CommandError(f"Post with title '{post_title}' already exists. The AI failed to generate a unique topic.")

        # Use get_or_create with case-insensitive lookup
        category, created = Category.objects.get_or_create(
            name__iexact=ai_data['category'], 
            defaults={'name': ai_data['category']}
        )
        if created:
            self.stdout.write(f"📁 Created new category: '{category.name}'")
        
        post_status = 'draft' if options['publish'] else 'draft'
        new_post = Post.objects.create(
            title=post_title, 
            author=author, 
            content=ai_data['content'],
            excerpt=ai_data['excerpt'], 
            status=post_status
        )
        new_post.categories.add(category)
        
        self.stdout.write(self.style.SUCCESS(f"📝 Successfully created new {post_status.upper()} post: '{new_post.title}'"))
        
        if not options.get('no_image', False):
            try:
                generate_image_with_gemini(new_post, ai_data['image_prompt'])
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Image generation failed: {e}"))
                self.stdout.write(self.style.WARNING("   Continuing without featured image..."))
        else:
            self.stdout.write(self.style.WARNING("🖼️  Skipping image generation as per --no-image flag."))
        
        return new_post.title # Return the new title to be added to the set for this run

    def update_post_image(self, slug: str):
        self.stdout.write(self.style.HTTP_INFO(f"🔄 Updating image for post with slug: {slug}"))
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            raise CommandError(f"Post with slug '{slug}' not found.")
        
        prompt = f"An artistic, abstract, high-resolution image for a tech blog post titled '{post.title}'. The style should be modern and clean."
        
        try:
            generate_image_with_gemini(post, prompt)
            self.stdout.write(self.style.SUCCESS("✅ Image update process complete."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Image update failed: {e}"))