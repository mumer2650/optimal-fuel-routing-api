from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        # Prevent loading the dataset when running migrations
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv:
            from .services.station_data import station_db
            try:
                station_db.load()
            except Exception as e:
                print(f"Failed to load station data: {e}")
