from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

@shared_task(name="blog.tasks.generate_ai_blog_post")
def generate_ai_blog_post(publish=False, count=1,depth="intermediate"):
    print(f"[{timezone.now()}] Running AI blog post generation task...")
    
    try:
        # This is the corrected way to call the command with a boolean flag.
        call_command('aicontent', 'create_post', publish=publish, count=count, depth=depth)
        
        result_message = f"AI content generation command executed successfully. Created {count} post(s) with publish={publish}."
        print(result_message)
        return result_message
    except Exception as e:
        # It's good practice to log errors in scheduled tasks.
        error_message = f"An error occurred during AI content generation: {e}"
        print(error_message)
        return error_message
