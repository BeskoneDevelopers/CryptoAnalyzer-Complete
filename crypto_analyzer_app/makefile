COMPOSE = docker compose
EXEC = $(COMPOSE) exec web
MANAGE = $(EXEC) python manage.py
RUFF = ruff
PROJECT_ROOT = ..

.PHONY: help build up logs down down-volumes restart migrate makemigrations shell createsuperuser test lint format bash install

help:
	@echo "Доступные команды:"
	@echo "  make build           — Собрать образы"
	@echo "  make up              — Запустить контейнеры в фоне"
	@echo "  make logs            — Посмотреть логи"
	@echo "  make down            — Остановить контейнеры"
	@echo "  make down-volumes    — Остановить контейнеры и удалить volumes"
	@echo "  make restart         — Перезапустить контейнеры"
	@echo "  make migrate         — Применить миграции"
	@echo "  make makemigrations  — Создать миграции"
	@echo "  make shell           — Зайти в Django shell"
	@echo "  make createsuperuser — Создать администратора"
	@echo "  make test            — Запустить тесты"
	@echo "  make lint            — Проверить Ruff"
	@echo "  make format          — Отформатировать код Ruff"
	@echo "  make bash            — Зайти в bash контейнера web"
	@echo "  make install         — Установить зависимости в web-контейнер"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

logs:
	$(COMPOSE) logs -f

down:
	$(COMPOSE) down

down-volumes:
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
	$(RUFF) check $(PROJECT_ROOT)
	$(RUFF) format --check $(PROJECT_ROOT)

format:
	$(RUFF) format $(PROJECT_ROOT)
	$(RUFF) check --fix $(PROJECT_ROOT)

bash:
	$(EXEC) bash

install:
	$(EXEC) pip install -r requirements.txt