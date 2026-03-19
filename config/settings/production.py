"""Settings de producao do WAS Contabil.

Todas as variaveis sensiveis sao OBRIGATORIAS via variaveis de ambiente.
Sem fallbacks inseguros.

Deploy via Docker + Nginx + Cloudflare Tunnel.
"""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Obrigatorios — sem fallback
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DATABASES["default"]["PASSWORD"] = os.environ["DB_PASSWORD"]  # noqa: F405
DATABASES["default"]["HOST"] = os.environ.get("DB_HOST", "db")  # noqa: F405

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Cloudflare Tunnel: HTTPS termina no Cloudflare, chega como HTTP no nginx
# Confiar no header X-Forwarded-Proto do Cloudflare
# Cloudflare Tunnel: HTTPS termina no Cloudflare, chega como HTTP no nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Cloudflare Tunnel garante HTTPS externamente
# Internamente (Docker network) trafego e HTTP puro
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False  # Cloudflare garante HTTPS no edge
CSRF_COOKIE_SECURE = False  # Trafego interno e HTTP

# CSRF: confiar nos dominios do Cloudflare
CSRF_TRUSTED_ORIGINS = [f"https://{host.strip()}" for host in ALLOWED_HOSTS if host.strip()]

# Static files (servidos pelo nginx)
STATIC_ROOT = "/app/staticfiles"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "WARNING"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Email (para convites — configurar SMTP)
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@was.dev.br")
