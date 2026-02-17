from django.apps import AppConfig


class IrrigationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'irrigation'
    verbose_name = 'Water Irrigation Management'
    
    def ready(self):
        import irrigation.signals
