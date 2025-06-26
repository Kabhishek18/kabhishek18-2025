from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

@shared_task(name="blog.tasks.generate_ai_blog_post")
def generate_ai_blog_post(publish=True, count=1):
    """
    A Celery task that calls the aicontent management command.
    
    This task can be configured from the Django Admin in Celery Beat
    by passing arguments in the 'Arguments' field, e.g., [false, 5]
    to create 5 draft posts.
    """
    print(f"[{timezone.now()}] Running AI blog post generation task...")
    
    try:
        # This is the corrected way to call the command with a boolean flag.
        call_command('aicontent', 'create_post', publish=publish, count=count)
        
        result_message = f"AI content generation command executed successfully. Created {count} post(s) with publish={publish}."
        print(result_message)
        return result_message
    except Exception as e:
        # It's good practice to log errors in scheduled tasks.
        error_message = f"An error occurred during AI content generation: {e}"
        print(error_message)
        return error_message
