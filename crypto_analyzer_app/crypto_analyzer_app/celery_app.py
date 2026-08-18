import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_analyzer_app.settings")
app = Celery("crypto_analyzer_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()