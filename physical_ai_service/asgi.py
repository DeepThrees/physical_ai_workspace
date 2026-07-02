"""ASGI entrypoint for the Physical AI Service Plane."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physical_ai_service.settings")

application = get_asgi_application()
