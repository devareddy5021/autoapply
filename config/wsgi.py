"""WSGI config for JobAutoApply project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
