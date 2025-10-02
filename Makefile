.PHONY: help test coverage lint format run migrate shell docker-build docker-up docker-down clean

help:
	@echo "BlockShelf Development Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run tests with pytest"
	@echo "  make coverage       - Run tests with coverage report"
	@echo "  make test-fast      - Run tests excluding slow tests"
	@echo ""
	@echo "Development:"
	@echo "  make run            - Run development server"
	@echo "  make migrate        - Run database migrations"
	@echo "  make shell          - Open Django shell"
	@echo "  make createsuperuser - Create admin user"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-up      - Start Docker containers"
	@echo "  make docker-down    - Stop Docker containers"
	@echo "  make docker-logs    - View Docker logs"
	@echo "  make docker-shell   - Open shell in web container"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Remove temporary files"
	@echo "  make collectstatic  - Collect static files"
	@echo "  make backup         - Backup database"

# Testing
test:
	pytest

coverage:
	pytest --cov=inventory --cov-report=html --cov-report=term

test-fast:
	pytest -m "not slow"

test-auth:
	pytest -m auth

test-permissions:
	pytest -m permissions

test-imports:
	pytest -m imports

# Development
run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

createsuperuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec web bash

docker-test:
	docker-compose exec web pytest

docker-clean:
	docker-compose down -v

# Database
backup:
	@if [ -f scripts/backup_database.sh ]; then \
		bash scripts/backup_database.sh; \
	else \
		echo "Backup script not found"; \
	fi

restore:
	@if [ -f scripts/restore_database.sh ]; then \
		bash scripts/restore_database.sh; \
	else \
		echo "Restore script not found"; \
	fi

# Maintenance
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type f -name '.coverage' -delete
	find . -type d -name 'htmlcov' -exec rm -rf {} +
	find . -type f -name '*.log' -delete

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-django pytest-cov pytest-mock factory-boy

# Health checks
health:
	@curl -f http://localhost:8000/inventory/health/ || echo "Health check failed"

liveness:
	@curl -f http://localhost:8000/inventory/health/liveness/ || echo "Liveness check failed"

readiness:
	@curl -f http://localhost:8000/inventory/health/readiness/ || echo "Readiness check failed"
