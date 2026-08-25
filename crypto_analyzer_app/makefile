COMPOSE = docker-compose
EXEC = $(COMPOSE) exec web
MANAGE = $(EXEC) python manage.py

.PHONY: help
help:
        @echo "Доступные команды:"
        @echo "  make build       — Собрать образы"
        @echo "  make up          — Запустить контейнеры в фоне"
        @echo "  make logs        — Посмотреть логи"
        @echo "  make migrate     — Применить миграции"
        @echo "  make shell       — Зайти в shell Django"
        @echo "  make test        — Запустить тесты"
        @echo "  make bash        — Зайти в bash контейнера web"
        @echo "  make down        — Остановить и удалить контейнеры"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

logs:
	$(COMPOSE) logs -f

down:
	$(COMPOSE) down -v

restart:
    $(MAKE) down
    $(MAKE) up

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

createsuperuser:
	$(MANAGE) createsuperuser

test:
	$(MANAGE) test

lint:
	$(EXEC) ruff check .
	$(EXEC) ruff format --check .

format:
	$(EXEC) ruff format .
	$(EXEC) ruff check --fix .

bash:
	$(EXEC) bash

install:
	$(EXEC) pip install -r requirements.txt