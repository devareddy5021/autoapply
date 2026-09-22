"""JobAutoApply Django Configuration Package."""
import os

# Ensure Django ORM calls are permitted in async / Playwright execution threads
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

