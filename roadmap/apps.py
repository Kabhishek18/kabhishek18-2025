from django.apps import AppConfig


class RoadmapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'roadmap'
    verbose_name = 'Resume Parser'
    
    def ready(self):
        """
        Initialize the roadmap app when Django starts.
        This method is called when the app is ready.
        """
        pass
