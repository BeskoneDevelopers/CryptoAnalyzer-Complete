from crypto_analyzer_app.celery_app import app as celery_app
from django.core.cache import cache
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def _check_database() -> bool:
    try:
        with connection.cursor() as curs:
            curs.execute("SELECT 1")
        database_ok = True
    except DatabaseError:
        database_ok = False

    return database_ok


def _check_cache() -> bool:
    try:
        cache.set("health_check", "ok", timeout=5)
        cache_ok = cache.get("health_check") == "ok"
    except Exception:
        cache_ok = False

    return cache_ok


def _check_celery_broker() -> bool:
    try:
        with celery_app.connection_for_read() as broker_conn:
            broker_conn.ensure_connection(max_retries=0)
        celery_broker_ok = True
    except Exception:
        celery_broker_ok = False

    return celery_broker_ok


@require_GET
def health_check(request):
    database_ok = _check_database()
    cache_ok = _check_cache()
    celery_broker_ok = _check_celery_broker()

    all_ok = database_ok and cache_ok and celery_broker_ok

    data = {
        "status": "ok" if all_ok else "degraded",
        "database": "ok" if database_ok else "error",
        "redis": "ok" if cache_ok else "error",
        "celery_broker": "ok" if celery_broker_ok else "error",
    }
    status_code = 200 if all_ok else 503

    return JsonResponse(data, status=status_code)
