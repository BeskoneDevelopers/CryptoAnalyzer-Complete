from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Тестовое необработанной исключение для Sentry"

    def handle(self, *args, **options):
        raise RuntimeError("sentry test error")
