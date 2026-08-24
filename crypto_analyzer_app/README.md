Coin API
REST API для работы с криптовалютами и историей цен. Реализовано на Django + Django REST Framework.

Возможности
Список и детали монет с фильтрацией и поиском.
История цен по монете с курсорной пагинацией (по 10 записей, от новых к старым).
Контроль доступа: чтение - всем, изменение - только администраторам.
Оптимизированные запросы к БД (prefetch_related, фильтрация, поиск).

Технологии
- Python 3.14
- Django 6.0
- DRF
- PostgreSQL
- Celery + Redis
- JWT (simplejwt)
- drf-spectacular (Swagger)

Установка
git clone https://github.com/BeskoneDevelopers/CryptoAnalyzer-Complete.git
cd crypto_analyzer_app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Запуск
# Сервер (Windows)
waitress-serve --listen=127.0.0.1:8000 crypto_analyzer_app.wsgi:application
# Celery worker
celery -A crypto_analyzer_app worker -l info -P solo
# Celery Beat
celery -A crypto_analyzer_app beat -l info

Api документация
Swagger: /api/docs/

Тесты
python manage.py test