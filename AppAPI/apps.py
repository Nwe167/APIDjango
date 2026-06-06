from django.apps import AppConfig


class AppapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'AppAPI'
    verbose_name = 'File Sharing & Document Management'
    
    def ready(self):
        """Register signal handlers"""
        import AppAPI.signals
