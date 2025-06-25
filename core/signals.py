from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .apps import CoreConfig

@receiver(post_migrate)
def sync_templates_on_migrate(sender, **kwargs):
    # We only want this to run when the 'core' app's migrations are applied.
    if isinstance(sender, CoreConfig):
        from .models import TemplateFile
        print("\nChecking for new template files to sync...")
        created_count = TemplateFile.sync_from_filesystem()
        if created_count > 0:
            print(f"Successfully synced {created_count} new template(s).")
        else:
            print("Template files are already up to date.")