# python manage.py aicontent create_post --topic "The Impact of AI on UI/UX Design"
# python manage.py aicontent create_post

import os
import json
import random
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from blog.models import Post, Category
import google.generativeai as genai

# --- AI Interaction using Google Gemini API ---
def get_ai_generated_content(existing_categories: list, topic: str = None) -> dict:
    """
    Calls the Google Gemini API to generate structured blog content.
    If no topic is provided, the AI will generate one.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise CommandError("GEMINI_API_KEY environment variable not found. Please add it to your .env file.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Prepare the list of existing categories for the prompt
    category_list_str = ", ".join(f"'{cat}'" for cat in existing_categories) if existing_categories else "None"

    # Construct the detailed prompt for the AI
    prompt = f"""
    You are an expert content creator and SEO specialist for a high-traffic tech blog called 'Digital Codex'.
    Your audience consists of software developers, AI enthusiasts, and tech leaders.
    Your task is to generate a complete, high-quality blog post in a single pass.

    **Topic:**
    {'Generate a new, engaging, and specific blog post topic related to artificial intelligence, machine learning, or modern software development trends.' if not topic else f"Write about the following topic: '{topic}'."}

    **Category Assignment:**
    Here is a list of existing categories on the blog: [{category_list_str}].
    Based on the post's topic, you must decide on the most appropriate category.
    - If the topic fits well into an existing category, please use it.
    - If the topic is novel or specific enough to warrant a new category, create a new one. Be descriptive.
    - Aim for a good balance. Do not create new categories for topics that are slight variations of existing ones.

    **Content Requirements:**
    1.  **Title:** An engaging, SEO-friendly title for the post.
    2.  **Excerpt:** A short, compelling summary (2-3 sentences) for list views and meta descriptions.
    3.  **Content:** The main body of the article, formatted in clean HTML. It should be well-structured with `<h2>`, `<h3>`, `<p>`, `<ul>`, `<li>`, and `<strong>` tags. The content should be informative, insightful, and at least 400 words long.
    4.  **Image Prompt:** A descriptive prompt for a text-to-image AI (like Midjourney or DALL-E) to create a stunning, relevant featured image for this post. The prompt should be detailed and specific.

    **Output Format:**
    You MUST return your response as a single, valid JSON object. Do not include any text, markdown, or code fences before or after the JSON object.

    The JSON schema is as follows:
    {{
        "title": "string",
        "excerpt": "string",
        "content": "string (HTML)",
        "category": "string",
        "image_prompt": "string"
    }}
    """
    
    print("\n🤖 Asking Gemini AI to generate a blog post...")
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_data = json.loads(cleaned_response_text)
        print("✅ AI has successfully generated the content.")
        return ai_data
    except Exception as e:
        print(f"❌ An error occurred while interacting with the AI: {e}")
        print(f"Raw AI Response was:\n{response.text if 'response' in locals() else 'No response received.'}")
        raise CommandError("Failed to get a valid response from the AI.")


class Command(BaseCommand):
    """
    A Django management command to generate blog content using the Google Gemini AI.
    Can be run with a specific topic or autonomously to generate a new topic.
    Suitable for running as a cron job.

    Example usage:
    # Autonomous mode (for cron jobs)
    python manage.py aicontent create_post

    # With a specific topic
    python manage.py aicontent create_post --topic "The Future of Edge Computing"

    # Specifying an author
    python manage.py aicontent create_post --author "admin"
    """
    help = 'Uses AI to generate content for the blog app.'

    def add_arguments(self, parser):
        parser.add_argument('command', type=str, choices=['create_post'], help='The subcommand to run.')
        parser.add_argument('--topic', type=str, help='(Optional) The topic for the AI to write about.')
        parser.add_argument('--author', type=str, help='(Optional) Username of the author. Defaults to the first superuser.')

    def handle(self, *args, **options):
        """The main entry point for the command."""
        self.create_post(options.get('topic'), options.get('author'))

    def create_post(self, topic, author_username):
        self.stdout.write(self.style.HTTP_INFO("🚀 Starting AI content creation process..."))

        # --- Get Author ---
        try:
            User = get_user_model()
            if author_username:
                author = User.objects.get(username=author_username)
            else:
                author = User.objects.filter(is_superuser=True).order_by('pk').first()
            if not author:
                raise CommandError("No author found. Create a superuser or specify one with --author.")
            self.stdout.write(f"✍️  Author set to: {author.username}")
        except User.DoesNotExist:
            raise CommandError(f"Author with username '{author_username}' not found.")

        # --- Get existing categories to help the AI make a decision ---
        existing_categories = list(Category.objects.values_list('name', flat=True))

        # --- Call the AI to get content ---
        ai_data = get_ai_generated_content(existing_categories, topic)

        # --- Find or Create the Category from AI response ---
        category_name = ai_data['category']
        category, created = Category.objects.get_or_create(
            name__iexact=category_name,
            defaults={'name': category_name}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created new category: '{category.name}'"))
        else:
            self.stdout.write(f"Using existing category: '{category.name}'")

        # --- Create the Blog Post ---
        post_title = ai_data['title']
        if Post.objects.filter(title__iexact=post_title).exists():
            raise CommandError(f"A post with the title '{post_title}' already exists. The AI generated a duplicate topic.")

        try:
            new_post = Post.objects.create(
                title=post_title,
                author=author,
                content=ai_data['content'],
                excerpt=ai_data['excerpt'],
                status='draft'
            )
            new_post.categories.add(category)
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created new DRAFT post: '{new_post.title}'"))
            self.stdout.write(self.style.HTTP_INFO("\n--- Media Generation Prompt ---"))
            self.stdout.write(self.style.WARNING(f"{ai_data['image_prompt']}"))
            self.stdout.write(self.style.SUCCESS("\n🎉 Process complete! Review the draft post in the admin panel."))
        except Exception as e:
            raise CommandError(f"Failed to save the new post to the database: {e}")
