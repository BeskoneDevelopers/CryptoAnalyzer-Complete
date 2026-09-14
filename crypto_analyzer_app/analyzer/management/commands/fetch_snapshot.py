from django.core.management.base import BaseCommand

from analyzer.tasks import fetch_snapshot_task

class Command(BaseCommand):
    help = "Извлекает крипто-данные и создает снимок"

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, default="coingecko")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        provider = options["provider"]
        limit = options["limit"]

        task = fetch_snapshot_task.delay(provider, limit)
        self.stdout.write(f"Операция создана: {task.id}")
