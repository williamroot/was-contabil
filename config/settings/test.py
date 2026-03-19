from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["*"]

# SQLite para testes — não exige PostgreSQL rodando
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Desabilitar redirecionamentos de segurança em testes
SECURE_SSL_REDIRECT = False

# Convites gerenciados manualmente via apps.core.models.Invitation
