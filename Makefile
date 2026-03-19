# Detecta automaticamente se deve usar docker-compose ou docker compose
DOCKER_COMPOSE := $(shell command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose)
DJANGO_LOCAL := DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_TEST := DJANGO_SETTINGS_MODULE=config.settings.test
PYTHON := python3
MANAGE := $(PYTHON) manage.py

.DEFAULT_GOAL := help

help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║           WAS CONTABIL - Comandos Disponíveis                ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 BUILD & SETUP:"
	@echo "  make build              - Builda as imagens Docker"
	@echo "  make setup              - Setup completo (build + migrate + superuser)"
	@echo "  make migrate            - Roda migracoes do banco"
	@echo "  make makemigrations     - Cria novas migracoes"
	@echo "  make createsuperuser    - Cria superusuario"
	@echo "  make seed               - Cria superuser + organizacao de teste"
	@echo ""
	@echo "🚀 DESENVOLVIMENTO:"
	@echo "  make run                - Sobe tudo (postgres + redis + app)"
	@echo "  make runserver          - Inicia servidor Django local (sem Docker)"
	@echo "  make shell              - Abre Django shell"
	@echo "  make dbshell            - Abre psql no banco"
	@echo "  make urls               - Lista todas as URLs do projeto"
	@echo ""
	@echo "⚙️  WORKERS:"
	@echo "  make worker             - Inicia worker RQ (fila default)"
	@echo "  make sync-indices       - Sincroniza indices SELIC/IPCA do BCB"
	@echo ""
	@echo "🧪 TESTES:"
	@echo "  make test               - Roda todos os testes"
	@echo "  make test-v             - Roda testes com verbose"
	@echo "  make test-cov           - Roda testes com cobertura"
	@echo "  make test-compat        - Roda testes de compatibilidade HPR"
	@echo "  make test-fast          - Roda testes sem cobertura (rapido)"
	@echo "  make test-app APP=core  - Roda testes de um app especifico"
	@echo ""
	@echo "🎨 QUALIDADE:"
	@echo "  make lint               - Roda black + isort + flake8"
	@echo "  make format             - Formata codigo (black + isort)"
	@echo "  make check              - Django system check"
	@echo "  make quality            - lint + check + test (tudo junto)"
	@echo ""
	@echo "🐳 DOCKER:"
	@echo "  make up                 - Sobe containers (postgres + redis)"
	@echo "  make down               - Para containers"
	@echo "  make logs               - Mostra logs dos containers"
	@echo "  make ps                 - Status dos containers"
	@echo "  make clean              - Remove containers, volumes e cache"
	@echo ""

# ============================================================================
# BUILD & SETUP
# ============================================================================

build:
	$(DOCKER_COMPOSE) build --parallel

setup: up migrate seed
	@echo "✅ Setup completo! Acesse http://localhost:8000"
	@echo "   Login: admin@wascontabil.com / WAS@2026!"

migrate:
	$(DJANGO_LOCAL) $(MANAGE) migrate

makemigrations:
	$(DJANGO_LOCAL) $(MANAGE) makemigrations

createsuperuser:
	$(DJANGO_LOCAL) $(MANAGE) createsuperuser

seed:
	@$(DJANGO_LOCAL) $(MANAGE) shell -c "\
from django.contrib.auth import get_user_model; \
from apps.core.models import Organization, Membership; \
User = get_user_model(); \
user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@wascontabil.com', 'is_staff': True, 'is_superuser': True, 'first_name': 'Admin', 'last_name': 'WAS'}); \
created and user.set_password('WAS@2026!'); \
created and user.save(); \
org, _ = Organization.objects.get_or_create(slug='was-contabil', defaults={'name': 'WAS Contabil (Teste)'}); \
Membership.objects.get_or_create(user=user, organization=org, defaults={'is_owner': True}); \
print('Superuser: admin@wascontabil.com / WAS@2026!') if created else print('Superuser ja existe'); \
"

# ============================================================================
# DESENVOLVIMENTO
# ============================================================================

run: up
	$(DJANGO_LOCAL) $(MANAGE) runserver 0.0.0.0:8000

runserver:
	$(DJANGO_LOCAL) $(MANAGE) runserver

shell:
	$(DJANGO_LOCAL) $(MANAGE) shell

dbshell:
	$(DJANGO_LOCAL) $(MANAGE) dbshell

urls:
	$(DJANGO_LOCAL) $(MANAGE) show_urls 2>/dev/null || $(DJANGO_LOCAL) $(PYTHON) -c "\
import django; django.setup(); \
from django.urls import get_resolver; \
for pattern in sorted(get_resolver().url_patterns, key=lambda p: str(p.pattern)): \
    print(f'  {pattern.pattern}'); \
"

# ============================================================================
# WORKERS
# ============================================================================

worker:
	$(DJANGO_LOCAL) $(MANAGE) rqworker default

sync-indices:
	$(DJANGO_LOCAL) $(MANAGE) sync_indices

# ============================================================================
# TESTES
# ============================================================================

test:
	$(DJANGO_TEST) $(PYTHON) -m pytest

test-v:
	$(DJANGO_TEST) $(PYTHON) -m pytest -v --tb=short

test-cov:
	$(DJANGO_TEST) $(PYTHON) -m pytest --cov=apps --cov-report=term-missing

test-compat:
	$(DJANGO_TEST) $(PYTHON) -m pytest tests/test_compatibilidade_hpr.py -v

test-fast:
	$(DJANGO_TEST) $(PYTHON) -m pytest -x -q --no-header

test-app:
	$(DJANGO_TEST) $(PYTHON) -m pytest apps/$(APP)/tests/ -v --tb=short

# ============================================================================
# QUALIDADE
# ============================================================================

format:
	black .
	isort .

lint: format
	flake8 apps/ config/

check:
	$(DJANGO_LOCAL) $(MANAGE) check

quality: lint check test
	@echo "✅ Tudo limpo: lint + check + testes passando"

# ============================================================================
# DOCKER
# ============================================================================

up:
	$(DOCKER_COMPOSE) up -d postgres redis

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

ps:
	$(DOCKER_COMPOSE) ps

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

.PHONY: help build setup migrate makemigrations createsuperuser seed \
        run runserver shell dbshell urls \
        worker sync-indices \
        test test-v test-cov test-compat test-fast test-app \
        format lint check quality \
        up down logs ps clean
