"""Settings de produção do WAS Contábil.

Todas as variáveis sensíveis são OBRIGATÓRIAS via variáveis de ambiente.
Sem fallbacks inseguros.
"""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # OBRIGATÓRIO em produção

DATABASES["default"]["PASSWORD"] = os.environ["DB_PASSWORD"]  # noqa: F405  # OBRIGATÓRIO

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
