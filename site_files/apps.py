from django.apps import AppConfig


class SiteFilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'site_files'
    verbose_name = 'Site Files Manager'
    
    def ready(self):
        """
        Initialize the app when Django starts.
        This is where we can register signals or perform other initialization tasks.
        """
        # Import signals or perform other initialization
        import site_files.tasks
        
        # Import the custom admin configuration for django-celery-beat
        try:
            import site_files.celery_admin
        except ImportError:
            pass
        
        # Register the periodic task
        # We need to use a try-except block to handle the case where the database is not yet ready
        try:
            site_files.tasks.ready()
        except Exception as e:
            # During initial migrations or when the database is not ready, this might fail
            # That's expected and we can safely ignore it
            pass
