"""ASGI config for JobAutoApply project."""
import os
from django.core.asgi import get_asgi_application

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
