.PHONY: up down build logs migrate test lint format

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

test:
	docker compose exec backend pytest

lint:
	docker compose exec backend ruff check app tests
	docker compose exec backend mypy app

format:
	docker compose exec backend ruff format app tests
