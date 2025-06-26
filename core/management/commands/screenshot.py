import os
import time
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from blog.models import Post # Import the Post model to get a real URL

def take_screenshot(url, output_file):
    """
    Takes a screenshot of a given URL using a headless Chrome browser.
    """
    print(f"📸 Taking screenshot of {url}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1280,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--hide-scrollbars")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        # Give the page time to load completely, including any JS animations
        time.sleep(20) 
        driver.save_screenshot(output_file)
        driver.quit()
        print(f"✅ Screenshot saved to {output_file}")
    except Exception as e:
        print(f"❌ Could not take screenshot of {url}. Error: {e}")


class Command(BaseCommand):
    help = 'Takes screenshots of key pages of the website.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("Starting website screenshot process..."))
        
        # Make sure you are using a consistent base URL
        # Best practice is to set this in your settings.py and import it
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')

        # --- Define URLs to Screenshot ---
        # We make this more dynamic by using Django's URL reversing
        pages_to_screenshot = {
            # FIX: Use the root URL for the homepage directly to avoid NoReverseMatch errors.
            "homepage": base_url + '/',
            "blog": base_url + reverse('blog:list'),
            "admin": base_url + reverse('admin:index'),
        }

        # Dynamically get the URL of the most recent published blog post
        latest_post = Post.objects.filter(status='published').order_by('-created_at').first()
        if latest_post:
            try:
                pages_to_screenshot['blog_detail'] = base_url + reverse('blog:detail', kwargs={'slug': latest_post.slug})
            except NoReverseMatch:
                self.stderr.write(self.style.ERROR("Could not reverse URL for latest blog post. Check your blog/urls.py."))
        else:
            self.stdout.write(self.style.WARNING("No published blog posts found, skipping detail page screenshot."))

        # --- Loop and Capture ---
        for name, url in pages_to_screenshot.items():
            output_path = os.path.join(settings.BASE_DIR, 'screenshots', f'{name}.png')
            take_screenshot(url, output_path)
            
        self.stdout.write(self.style.SUCCESS("🎉 Screenshot process complete!"))

