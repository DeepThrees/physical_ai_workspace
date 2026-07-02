"""WSGI entrypoint for the Physical AI Service Plane."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physical_ai_service.settings")

application = get_wsgi_application()
