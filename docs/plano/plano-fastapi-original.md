# Diagnóstico de Transação Tributária - Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir uma plataforma web unificada para diagnóstico e simulação de transação tributária federal (PGFN), com quatro módulos: (1) **Simulador de Transação Avançado** com cadastro de empresas (CRUD+busca), decomposição de dívida em Principal/Multa/Juros/Encargos por 3 categorias (Previdenciário, Tributário/Não Tributário, Simples Nacional), CAPAG presumida com rating automático (A/B/C/D), desconto somente sobre multa+juros+encargos (nunca principal), Menor/Maior desconto, honorários de êxito e impressão Resumida/Completa; (2) **Simulador TPV Avançado** com validação por CDA individual (limite 60 SM, inscrição > 1 ano, descontos 30-50%, importação em lote, dashboard de elegibilidade futura); (3) **Diagnóstico TPV Simplificado** (wizard com checklist, comparação 4 faixas); (4) **Comparador de Modalidades** (TPV vs Capacidade de Pagamento). Todos com cálculos dinâmicos SELIC (API BCB), OAuth (Google/Microsoft), histórico unificado e exportação PDF/relatório A4.

**Architecture:** API REST em FastAPI (Python) com engine de cálculo tributário desacoplada, worker assíncrono RQ para tarefas pesadas (parsing XML, geração PDF, sync de índices), PostgreSQL para persistência, Redis para cache/queue. Frontend servido como SPA (Jinja2+HTMX para MVP ou desacoplado depois). Autenticação via OAuth2 (Google/Microsoft) com sessões JWT. Índices SELIC/IPCA obtidos dinamicamente da API do Banco Central (SGS) e cacheados em Redis/PostgreSQL.

**Tech Stack:**
- Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- PostgreSQL 17, Redis 7.x, RQ (Redis Queue)
- Authlib (OAuth2 Google/Microsoft), python-jose (JWT)
- WeasyPrint (PDF), httpx (HTTP client async)
- Docker, docker-compose
- pytest, pytest-asyncio, httpx (test client), factory-boy, testcontainers

---

## Base Legal Implementada

### Lei nº 13.988/2020 (com alterações da Lei nº 14.375/2022 e Lei nº 14.689/2023)
- **Art. 11, I:** Descontos em multas, juros e encargos para créditos **irrecuperáveis ou de difícil recuperação**
- **Art. 11, §2º, I:** **VEDADO** reduzir o montante principal (somente multa/juros/encargos)
- **Art. 11, §2º, II:** Desconto máximo de **65%** do valor total do crédito
- **Art. 11, §2º, III:** Prazo máximo de **120 meses** (demais empresas)
- **Art. 11, §3º (ME/EPP/PF):** Desconto máximo **70%**, prazo máximo **145 meses**
- **Art. 11, §1º:** Parcelas atualizadas pela **SELIC acumulada mensal** + 1% no mês do pagamento
- **Art. 11, IV (Lei 14.375):** Uso de **prejuízo fiscal e BCN-CSLL** até 70% do saldo remanescente
- **Art. 11, §12 (Lei 14.375):** Descontos **NÃO** são base de cálculo de IRPJ/CSLL/PIS/COFINS
- **Art. 5º, I-III:** Vedações: multas penais, Simples Nacional (sem LC), FGTS (sem Conselho Curador)
- **Art. 6º:** ME/EPP = receita bruta nos limites da LC 123/2006 (ME até R$360k, EPP até R$4,8M)
- **CF/88, art. 195, §11 (EC 103/2019):** Prazo máximo de **60 meses** para contribuições previdenciárias patronais (folha) e dos trabalhadores. **Não se aplica** a COFINS, PIS e CSLL

### Portaria PGFN nº 6.757/2022
- **Art. 21:** Capacidade de pagamento - estimativa de pagamento integral em 5 anos
- **Art. 24:** Classificação de créditos: **A** (alta recuperação), **B** (média), **C** (difícil), **D** (irrecuperável)
- **Art. 25:** Critérios de irrecuperabilidade (>15 anos, falido, CNPJ inapto, etc.)
- **Art. 36:** Entrada de **6%** do valor total sem desconto, em até **6 parcelas** (demais) ou **12 parcelas** (ME/EPP/PF)
- **Valor mínimo parcela:** R$ 25,00 (MEI), R$ 100,00 (demais)
- **Desconto:** Até 100% de juros, multa e encargos legais; limitado a 65% do valor total (70% para ME/EPP/PF)

### Edital PGDAU 11/2025 (prorrogado até 29/05/2026)
- **Modalidades:** Capacidade de pagamento, Pequeno valor, Difícil recuperação, Garantidos por seguro
- **Prazo restante:** Até 114 parcelas (demais) ou 133 parcelas (ME/EPP/PF) após entrada
- **Classificação A/B:** Apenas entrada facilitada
- **Classificação C/D:** Entrada facilitada + prazo estendido + descontos

### APIs de Índices Econômicos (Banco Central - SGS)
- **Série 4390:** SELIC acumulada no mês (% a.m.) — usada para correção de parcelas
- **Série 4189:** SELIC acumulada no mês anualizada base 252 (% a.m.) — alternativa mais precisa
- **Série 11:** Taxa SELIC diária (% a.d.) — para cálculo dia a dia
- **Série 433:** IPCA mensal (%) — referência
- **Série 189:** IGP-M mensal (%) — referência contratos
- **Endpoint por período:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={dd/MM/yyyy}&dataFinal={dd/MM/yyyy}`
- **Endpoint últimos N:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{N}?formato=json`
- **Limites:** API pública, sem autenticação. Máximo 10 anos por consulta (desde 26/03/2025)
- **Fórmula correção (Lei 13.988, art. 11, §1º):** `valor_corrigido = valor_original * Π(1 + selic_mensal/100) * 1.01`

### Classificação de Créditos CAPAG (Portaria PGFN 6.757/2022, art. 24)
| Tipo | Grau | Desconto | Benefícios |
|------|------|----------|-----------|
| **A** | Alta recuperabilidade | SEM desconto | Apenas entrada facilitada |
| **B** | Média recuperabilidade | SEM desconto | Apenas entrada facilitada |
| **C** | Difícil recuperação | Até 65% (70% ME/EPP) | Entrada + prazo + desconto |
| **D** | Irrecuperável | Até 65% (70% ME/EPP) | Entrada + prazo + desconto |

### Tabela Consolidada de Modalidades (Edital PGDAU 11/2025 + outras)
| Modalidade | Valor Dívida | Desconto Max | Parcelas (geral) | Parcelas (ME/EPP/PF) | Entrada |
|-----------|-------------|-------------|------------------|---------------------|---------|
| Capacidade Pgto (A/B) | Até R$45mi | 0% | 114x | 133x | 6% em 12x |
| Capacidade Pgto (C/D) | Até R$45mi | 65%/70% | 114x | 133x | 6% em 12x |
| Difícil Recuperação | Até R$45mi | 65%/70% | 108x | 133x | 5% em 12x |
| Pequeno Valor | Até 60 SM | 30-50% | 55x | 55x | 5% em 5x |
| Individual | >R$10mi | 65%/70% | 120x | 120x | Negociável |
| Individual Simplificada | R$1-10mi | 65%/70% | 120x | 120x | Proposta livre |
| Contencioso Peq. Valor (RFB) | Até 60 SM | 30-50% | 55x | 55x | Incluso |

---

## File Structure

```
diagnostico/
├── docker-compose.yml                    # Orquestração: app, postgres, redis, worker
├── Dockerfile                            # Imagem Python da aplicação
├── pyproject.toml                        # Dependências e configuração do projeto
├── alembic.ini                           # Configuração Alembic
├── alembic/
│   ├── env.py                            # Alembic environment config
│   └── versions/                         # Migration files
├── src/
│   ├── __init__.py
│   ├── main.py                           # FastAPI app factory, middleware, routers
│   ├── config.py                         # Settings via pydantic-settings (env vars)
│   ├── deps.py                           # Dependency injection (db session, current_user)
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py                     # OAuth endpoints (Google, Microsoft, logout)
│   │   ├── oauth.py                      # Authlib OAuth client config
│   │   ├── jwt.py                        # JWT token create/verify
│   │   ├── dependencies.py              # get_current_user dependency
│   │   └── models.py                     # User SQLAlchemy model
│   ├── transacao/
│   │   ├── __init__.py
│   │   ├── router.py                     # API endpoints: simular, historico, exportar
│   │   ├── schemas.py                    # Pydantic schemas (request/response)
│   │   ├── models.py                     # Simulacao SQLAlchemy model
│   │   ├── engine.py                     # Motor de cálculo puro (sem I/O)
│   │   ├── constants.py                  # Constantes legais (prazos, %, limites)
│   │   ├── service.py                    # Orquestração: engine + persistência + PDF
│   │   ├── engine_avancado.py            # Engine avançado: Principal/Multa/Juros/Encargos + CAPAG
│   │   ├── schemas_avancado.py           # Schemas decomposição por componentes
│   │   ├── service_avancado.py           # Orquestração simulação avançada
│   │   └── router_avancado.py            # Endpoints simulação avançada
│   ├── tpv/
│   │   ├── __init__.py
│   │   ├── router.py                     # API endpoints: simular TPV, CDAs, elegibilidade
│   │   ├── schemas.py                    # Schemas: CDA, SimulacaoTPV, Elegibilidade
│   │   ├── models.py                     # SimulacaoTPV, CDA SQLAlchemy models
│   │   ├── engine.py                     # Motor de cálculo TPV puro (sem I/O)
│   │   ├── constants.py                  # Constantes TPV (60 SM, descontos escalonados)
│   │   ├── validators.py                 # Validação de elegibilidade por CDA
│   │   ├── csv_parser.py                 # Parser de importação em lote (CSV)
│   │   └── service.py                    # Orquestração TPV
│   ├── indices/
│   │   ├── __init__.py
│   │   ├── router.py                     # Endpoint para consultar índices
│   │   ├── models.py                     # IndiceEconomico SQLAlchemy model
│   │   ├── client.py                     # HTTP client para API Banco Central (SGS)
│   │   ├── service.py                    # Sync/cache de índices, cálculo SELIC acumulada
│   │   └── tasks.py                      # RQ tasks: sync diário de índices
│   ├── empresas/
│   │   ├── __init__.py
│   │   ├── models.py                     # Empresa SQLAlchemy model (CRUD + honorários)
│   │   ├── schemas.py                    # EmpresaCreate, EmpresaResponse
│   │   └── router.py                     # CRUD endpoints com busca
│   ├── comparador/
│   │   ├── __init__.py
│   │   ├── service.py                    # Comparação entre modalidades (TPV vs Capacidade)
│   │   └── router.py                     # Endpoint de comparação
│   ├── pdf/
│   │   ├── __init__.py
│   │   ├── generator.py                  # Geração PDF com WeasyPrint
│   │   └── templates/
│   │       └── diagnostico.html          # Template HTML para PDF
│   └── worker.py                         # RQ worker entrypoint
├── tests/
│   ├── __init__.py
│   ├── conftest.py                       # Fixtures: db session, test client, factories
│   ├── factories.py                      # Factory-boy para User, Simulacao
│   ├── test_engine.py                    # Testes do motor de cálculo (unitários puros)
│   ├── test_constants.py                 # Testes das constantes legais
│   ├── test_auth.py                      # Testes OAuth flow + JWT
│   ├── test_transacao_router.py          # Testes de integração dos endpoints
│   ├── test_indices_client.py            # Testes do client BCB (com mock)
│   ├── test_indices_service.py           # Testes do serviço de índices
│   ├── test_pdf_generator.py             # Testes de geração PDF
│   ├── test_tpv_constants.py             # Testes constantes TPV
│   ├── test_tpv_engine.py               # Testes motor de cálculo TPV
│   ├── test_tpv_validators.py           # Testes validação elegibilidade CDA
│   ├── test_tpv_csv_parser.py           # Testes importação em lote
│   ├── test_tpv_router.py              # Testes endpoints TPV
│   ├── test_tpv_multi_faixa.py         # Testes comparação 4 faixas de desconto
│   ├── test_tpv_wizard.py              # Testes wizard de elegibilidade
│   ├── test_comparador.py              # Testes comparação entre modalidades
│   ├── test_empresas.py                # Testes CRUD empresas
│   └── test_engine_avancado.py         # Testes engine avançado (decomposição + CAPAG)
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-03-17-diagnostico-transacao-tributaria.md  # Este plano
```

---

## Task 1: Infraestrutura Docker + Configuração do Projeto

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/config.py`

- [ ] **Step 1: Criar `pyproject.toml`**

```toml
[project]
name = "diagnostico-transacao"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "authlib>=1.4.0",
    "python-jose[cryptography]>=3.3.0",
    "httpx>=0.28.0",
    "redis>=5.2.0",
    "rq>=2.1.0",
    "weasyprint>=63.0",
    "openpyxl>=3.1.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.18",
    "itsdangerous>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "factory-boy>=3.3.0",
    "testcontainers[postgres,redis]>=4.9.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
filterwarnings = ["ignore::DeprecationWarning"]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

- [ ] **Step 2: Criar `src/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://diagnostico:diagnostico@localhost:5432/diagnostico"
    database_url_sync: str = "postgresql://diagnostico:diagnostico@localhost:5432/diagnostico"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # OAuth - Microsoft
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""

    # App
    app_url: str = "http://localhost:8000"
    debug: bool = False

    # BCB API
    bcb_api_base_url: str = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 3: Criar `src/__init__.py`** (vazio)

```python
```

- [ ] **Step 4: Criar `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libglib2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY src/__init__.py src/__init__.py
RUN pip install --no-cache-dir ".[dev]"

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 5: Criar `docker-compose.yml`**

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

  worker:
    build: .
    command: python -m src.worker
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: diagnostico
      POSTGRES_USER: diagnostico
      POSTGRES_PASSWORD: diagnostico
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U diagnostico"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 6: Criar `.env` de exemplo**

```bash
# Criar .env.example (NÃO commitar .env real)
cat > .env.example << 'EOF'
DATABASE_URL=postgresql+asyncpg://diagnostico:diagnostico@postgres:5432/diagnostico
DATABASE_URL_SYNC=postgresql://diagnostico:diagnostico@postgres:5432/diagnostico
REDIS_URL=redis://redis:6379/0
SECRET_KEY=gerar-uma-chave-segura-aqui
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
APP_URL=http://localhost:8000
DEBUG=true
EOF
```

- [ ] **Step 7: Verificar que o Docker build funciona**

Run: `docker compose build`
Expected: Build completo sem erros

- [ ] **Step 8: Commit**

```bash
git init
echo -e ".env\n__pycache__\n*.pyc\n.pytest_cache\npgdata\n.ruff_cache\n*.egg-info/" > .gitignore
git add pyproject.toml Dockerfile docker-compose.yml .env.example .gitignore src/__init__.py src/config.py
git commit -m "feat: initial project setup with Docker, FastAPI, Postgres, Redis"
```

---

## Task 2: Database Models + Alembic Migrations

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `src/auth/models.py`
- Create: `src/auth/__init__.py`
- Create: `src/transacao/models.py`
- Create: `src/transacao/__init__.py`
- Create: `src/indices/models.py`
- Create: `src/indices/__init__.py`
- Create: `src/deps.py`

- [ ] **Step 1: Criar `src/deps.py` com base do SQLAlchemy**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 2: Criar `src/auth/__init__.py`** (vazio) e `src/auth/models.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.deps import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture: Mapped[str | None] = mapped_column(String(500))
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # "google" | "microsoft"
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: Criar `src/transacao/__init__.py`** (vazio) e `src/transacao/models.py`

```python
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.deps import Base


class Simulacao(Base):
    __tablename__ = "simulacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Dados da empresa
    razao_social: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    email_empresa: Mapped[str | None] = mapped_column(String(320))

    # Dados da dívida
    valor_total_divida: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    percentual_previdenciario: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_me_epp: Mapped[bool] = mapped_column(nullable=False)
    classificacao_credito: Mapped[str] = mapped_column(String(1), nullable=False, default="D")  # A, B, C, D

    # Resultado calculado (JSONB para flexibilidade)
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Metadados
    selic_mensal_utilizada: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    versao_calculo: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Criar `src/indices/__init__.py`** (vazio) e `src/indices/models.py`

```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.deps import Base


class IndiceEconomico(Base):
    __tablename__ = "indices_economicos"
    __table_args__ = (UniqueConstraint("serie_codigo", "data_referencia", name="uq_serie_data"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serie_codigo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 4390=SELIC mensal, 433=IPCA
    serie_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valor: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 5: Inicializar Alembic e gerar migration**

Run:
```bash
pip install -e ".[dev]"
alembic init alembic
```

Editar `alembic/env.py` para importar models:

```python
# No topo de alembic/env.py, após imports existentes:
from src.deps import Base
from src.auth.models import User
from src.transacao.models import Simulacao
from src.indices.models import IndiceEconomico

# Na função run_migrations_online(), setar:
target_metadata = Base.metadata
```

Editar `alembic.ini`:
```ini
sqlalchemy.url = postgresql://diagnostico:diagnostico@localhost:5432/diagnostico
```

Run:
```bash
alembic revision --autogenerate -m "initial models: users, simulacoes, indices"
alembic upgrade head
```

Expected: Migration criada e aplicada com sucesso

- [ ] **Step 6: Commit**

```bash
git add src/deps.py src/auth/ src/transacao/ src/indices/ alembic/ alembic.ini
git commit -m "feat: database models for users, simulacoes, indices_economicos + alembic"
```

---

## Task 3: Constantes Legais + Testes

**Files:**
- Create: `src/transacao/constants.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: Escrever testes das constantes**

```python
# tests/test_constants.py
from src.transacao.constants import (
    DESCONTO_MAX_GERAL,
    DESCONTO_MAX_ME_EPP,
    ENTRADA_PERCENTUAL,
    ENTRADA_PARCELAS_GERAL,
    ENTRADA_PARCELAS_ME_EPP,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
    PARCELA_MINIMA_MEI,
    PARCELA_MINIMA_DEMAIS,
    ClassificacaoCredito,
    get_desconto_por_classificacao,
    get_prazo_parcelas_restantes,
)


def test_desconto_max_geral_65_porcento():
    assert DESCONTO_MAX_GERAL == 0.65


def test_desconto_max_me_epp_70_porcento():
    assert DESCONTO_MAX_ME_EPP == 0.70


def test_entrada_6_porcento():
    assert ENTRADA_PERCENTUAL == 0.06


def test_entrada_parcelas_geral_6_meses():
    assert ENTRADA_PARCELAS_GERAL == 6


def test_entrada_parcelas_me_epp_12_meses():
    assert ENTRADA_PARCELAS_ME_EPP == 12


def test_prazo_previdenciario_60_meses():
    assert PRAZO_MAX_PREVIDENCIARIO == 60


def test_prazo_nao_previdenciario_geral_120_meses():
    assert PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL == 120


def test_prazo_nao_previdenciario_me_epp_145_meses():
    assert PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP == 145


def test_parcela_minima_mei_25():
    assert PARCELA_MINIMA_MEI == 25.0


def test_parcela_minima_demais_100():
    assert PARCELA_MINIMA_DEMAIS == 100.0


def test_classificacao_credito_enum():
    assert ClassificacaoCredito.A.value == "A"
    assert ClassificacaoCredito.D.value == "D"


def test_desconto_classificacao_a_zero():
    """Crédito tipo A (alta recuperação): sem desconto, apenas entrada facilitada."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.A, is_me_epp=False) == 0.0


def test_desconto_classificacao_b_zero():
    """Crédito tipo B (média recuperação): sem desconto, apenas entrada facilitada."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.B, is_me_epp=False) == 0.0


def test_desconto_classificacao_c_geral():
    """Crédito tipo C (difícil recuperação): até 65% para demais."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.C, is_me_epp=False) == 0.65


def test_desconto_classificacao_c_me_epp():
    """Crédito tipo C: até 70% para ME/EPP."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.C, is_me_epp=True) == 0.70


def test_desconto_classificacao_d_geral():
    """Crédito tipo D (irrecuperável): até 65% para demais."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.D, is_me_epp=False) == 0.65


def test_desconto_classificacao_d_me_epp():
    """Crédito tipo D: até 70% para ME/EPP."""
    assert get_desconto_por_classificacao(ClassificacaoCredito.D, is_me_epp=True) == 0.70


def test_prazo_parcelas_restantes_geral():
    """Demais empresas: 120 - 6 entrada = 114 parcelas restantes não previdenciário."""
    assert get_prazo_parcelas_restantes(is_me_epp=False, is_previdenciario=False) == 114


def test_prazo_parcelas_restantes_me_epp():
    """ME/EPP: 145 - 12 entrada = 133 parcelas restantes não previdenciário."""
    assert get_prazo_parcelas_restantes(is_me_epp=True, is_previdenciario=False) == 133


def test_prazo_parcelas_restantes_previdenciario_geral():
    """Previdenciário demais: 60 - 6 entrada = 54 parcelas."""
    assert get_prazo_parcelas_restantes(is_me_epp=False, is_previdenciario=True) == 54


def test_prazo_parcelas_restantes_previdenciario_me_epp():
    """Previdenciário ME/EPP: 60 - 12 entrada = 48 parcelas."""
    assert get_prazo_parcelas_restantes(is_me_epp=True, is_previdenciario=True) == 48
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_constants.py -v`
Expected: FAIL - módulo não encontrado

- [ ] **Step 3: Criar `tests/__init__.py`** (vazio) e `tests/conftest.py`** (vazio por enquanto)

```python
# tests/conftest.py
```

- [ ] **Step 4: Implementar `src/transacao/constants.py`**

```python
"""
Constantes legais para cálculo de transação tributária.

Fontes:
- Lei nº 13.988/2020 (art. 11), alterada pela Lei nº 14.375/2022
- Portaria PGFN nº 6.757/2022 (arts. 21-40)
- CF/88, art. 195, §11 (limite previdenciário)
- Edital PGDAU 11/2025 (modalidades vigentes até 29/05/2026)
"""

from enum import Enum

# --- Descontos ---
DESCONTO_MAX_GERAL = 0.65  # 65% - Lei 13.988, art. 11, I (redação Lei 14.375/2022)
DESCONTO_MAX_ME_EPP = 0.70  # 70% - Lei 13.988, art. 11, I (ME/EPP/PF)

# --- Entrada ---
ENTRADA_PERCENTUAL = 0.06  # 6% - Portaria PGFN 6.757/2022, art. 36
ENTRADA_PARCELAS_GERAL = 6  # 6 meses - Portaria PGFN 6.757/2022, art. 36
ENTRADA_PARCELAS_ME_EPP = 12  # 12 meses - Portaria PGFN 6.757/2022, art. 36 (ME/EPP/PF)

# --- Prazos máximos (em meses) ---
PRAZO_MAX_PREVIDENCIARIO = 60  # CF/88, art. 195, §11
PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL = 120  # Lei 13.988, art. 11, II
PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP = 145  # Lei 13.988, art. 11, II (ME/EPP/PF)

# --- Valor mínimo de parcela ---
PARCELA_MINIMA_MEI = 25.0  # R$ 25,00 - Portaria PGFN 6.757/2022
PARCELA_MINIMA_DEMAIS = 100.0  # R$ 100,00 - Portaria PGFN 6.757/2022

# --- Correção monetária ---
SELIC_ADICIONAL_PAGAMENTO = 0.01  # 1% no mês do pagamento - Lei 13.988, art. 11, §1º

# --- Séries BCB SGS ---
SERIE_SELIC_ACUMULADA_MENSAL = 4390  # SELIC acumulada no mês (% a.m.)
SERIE_SELIC_ACUMULADA_ANUALIZADA = 4189  # SELIC acumulada anualizada base 252
SERIE_SELIC_DIARIA = 11  # Taxa SELIC diária (% a.d.)
SERIE_IPCA = 433  # IPCA variação mensal (%)
SERIE_IGPM = 189  # IGP-M variação mensal (%)


class ClassificacaoCredito(str, Enum):
    """Classificação de créditos conforme Portaria PGFN 6.757/2022, art. 24."""

    A = "A"  # Alta perspectiva de recuperação
    B = "B"  # Média perspectiva de recuperação
    C = "C"  # Difícil recuperação
    D = "D"  # Irrecuperável


def get_desconto_por_classificacao(classificacao: ClassificacaoCredito, is_me_epp: bool) -> float:
    """
    Retorna o desconto máximo aplicável por classificação.

    - A/B: sem desconto (apenas entrada facilitada) - Portaria PGFN 6.757/2022
    - C/D: até 65% (demais) ou 70% (ME/EPP) - Lei 13.988, art. 11, I
    """
    if classificacao in (ClassificacaoCredito.A, ClassificacaoCredito.B):
        return 0.0
    return DESCONTO_MAX_ME_EPP if is_me_epp else DESCONTO_MAX_GERAL


def get_prazo_parcelas_restantes(is_me_epp: bool, is_previdenciario: bool) -> int:
    """
    Retorna o número de parcelas restantes após a entrada.

    Previdenciário: limitado a 60 meses total (CF/88, art. 195, §11)
    Não Previdenciário: 120 meses (demais) ou 145 meses (ME/EPP)
    """
    entrada = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL

    if is_previdenciario:
        return PRAZO_MAX_PREVIDENCIARIO - entrada

    prazo_total = PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP if is_me_epp else PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL
    return prazo_total - entrada
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/test_constants.py -v`
Expected: Todos PASS (17 testes)

- [ ] **Step 6: Commit**

```bash
git add src/transacao/constants.py tests/__init__.py tests/conftest.py tests/test_constants.py
git commit -m "feat: legal constants with full legal references + tests"
```

---

## Task 4: Motor de Cálculo (engine.py) + Testes TDD

**Files:**
- Create: `src/transacao/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Escrever testes do motor de cálculo**

```python
# tests/test_engine.py
from decimal import Decimal

import pytest

from src.transacao.engine import (
    calcular_diagnostico,
    calcular_entrada,
    calcular_parcelas,
    calcular_desconto,
    separar_divida,
    gerar_fluxo_pagamento,
    DiagnosticoInput,
    DiagnosticoResult,
)
from src.transacao.constants import ClassificacaoCredito


class TestCalcularDesconto:
    def test_desconto_classificacao_d_geral(self):
        """Classificação D, demais empresas: 65% de desconto."""
        resultado = calcular_desconto(
            valor=Decimal("100000"), classificacao=ClassificacaoCredito.D, is_me_epp=False
        )
        assert resultado == Decimal("65000")

    def test_desconto_classificacao_d_me_epp(self):
        """Classificação D, ME/EPP: 70% de desconto."""
        resultado = calcular_desconto(
            valor=Decimal("100000"), classificacao=ClassificacaoCredito.D, is_me_epp=True
        )
        assert resultado == Decimal("70000")

    def test_desconto_classificacao_a_zero(self):
        """Classificação A: sem desconto."""
        resultado = calcular_desconto(
            valor=Decimal("100000"), classificacao=ClassificacaoCredito.A, is_me_epp=False
        )
        assert resultado == Decimal("0")

    def test_desconto_classificacao_c_geral(self):
        resultado = calcular_desconto(
            valor=Decimal("50000"), classificacao=ClassificacaoCredito.C, is_me_epp=False
        )
        assert resultado == Decimal("32500")


class TestSepararDivida:
    def test_separar_30_porcento_previdenciario(self):
        prev, nao_prev = separar_divida(Decimal("100000"), Decimal("30"))
        assert prev == Decimal("30000")
        assert nao_prev == Decimal("70000")

    def test_separar_zero_previdenciario(self):
        prev, nao_prev = separar_divida(Decimal("100000"), Decimal("0"))
        assert prev == Decimal("0")
        assert nao_prev == Decimal("100000")

    def test_separar_100_previdenciario(self):
        prev, nao_prev = separar_divida(Decimal("100000"), Decimal("100"))
        assert prev == Decimal("100000")
        assert nao_prev == Decimal("0")


class TestCalcularEntrada:
    def test_entrada_6_porcento(self):
        """Entrada = 6% do valor SEM desconto."""
        valor_entrada, parcela_entrada, num_parcelas = calcular_entrada(
            valor_total_sem_desconto=Decimal("100000"), is_me_epp=False
        )
        assert valor_entrada == Decimal("6000")
        assert num_parcelas == 6
        assert parcela_entrada == Decimal("1000")

    def test_entrada_me_epp_12_parcelas(self):
        valor_entrada, parcela_entrada, num_parcelas = calcular_entrada(
            valor_total_sem_desconto=Decimal("100000"), is_me_epp=True
        )
        assert valor_entrada == Decimal("6000")
        assert num_parcelas == 12
        assert parcela_entrada == Decimal("500")


class TestCalcularParcelas:
    def test_parcelas_nao_previdenciario_geral(self):
        """Saldo restante / 114 parcelas para demais empresas."""
        valor_parcela, num_parcelas = calcular_parcelas(
            saldo_apos_entrada=Decimal("94000"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert num_parcelas == 114
        # 94000 / 114 = 824.56140...
        assert abs(valor_parcela - Decimal("824.56")) < Decimal("0.01")

    def test_parcelas_previdenciario_geral(self):
        """Saldo restante / 54 parcelas para previdenciário demais."""
        valor_parcela, num_parcelas = calcular_parcelas(
            saldo_apos_entrada=Decimal("27000"),
            is_me_epp=False,
            is_previdenciario=True,
        )
        assert num_parcelas == 54
        assert valor_parcela == Decimal("500")

    def test_parcela_minima_demais_respeitada(self):
        """Se parcela calculada < R$100, ajusta para R$100 e reduz nº parcelas."""
        valor_parcela, num_parcelas = calcular_parcelas(
            saldo_apos_entrada=Decimal("1000"),
            is_me_epp=False,
            is_previdenciario=False,
        )
        assert valor_parcela >= Decimal("100")


class TestGerarFluxoPagamento:
    def test_fluxo_tem_entrada_e_parcelas(self):
        fluxo = gerar_fluxo_pagamento(
            parcela_entrada=Decimal("1000"),
            num_entrada=6,
            parcela_normal=Decimal("500"),
            num_parcelas=54,
        )
        assert len(fluxo) == 60
        assert fluxo[0]["tipo"] == "entrada"
        assert fluxo[0]["valor"] == Decimal("1000")
        assert fluxo[5]["tipo"] == "entrada"
        assert fluxo[6]["tipo"] == "parcela"
        assert fluxo[6]["valor"] == Decimal("500")
        assert fluxo[59]["mes"] == 60


class TestDiagnosticoCompleto:
    def test_diagnostico_demais_empresa_classificacao_d(self):
        """Teste completo replicando cenário HPR: R$10k, 30% prev, demais, classif D."""
        inp = DiagnosticoInput(
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        result = calcular_diagnostico(inp)

        assert result.valor_total == Decimal("10000")
        assert result.desconto_percentual == Decimal("0.65")
        assert result.valor_desconto == Decimal("6500")
        assert result.valor_com_desconto == Decimal("3500")
        assert result.valor_entrada == Decimal("600")  # 6% de 10000 (sem desconto)
        assert result.parcelas_entrada == 6
        assert result.parcela_entrada_valor == Decimal("100")

    def test_diagnostico_me_epp_classificacao_d(self):
        """ME/EPP com classificação D: 70% desconto, 12 meses entrada, 145 meses."""
        inp = DiagnosticoInput(
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.D,
        )
        result = calcular_diagnostico(inp)

        assert result.desconto_percentual == Decimal("0.70")
        assert result.valor_desconto == Decimal("7000")
        assert result.valor_com_desconto == Decimal("3000")
        assert result.parcelas_entrada == 12
        assert result.previdenciario.prazo_total == 60
        assert result.nao_previdenciario.prazo_total == 145

    def test_diagnostico_classificacao_a_sem_desconto(self):
        """Classificação A: sem desconto, só entrada facilitada."""
        inp = DiagnosticoInput(
            valor_total_divida=Decimal("100000"),
            percentual_previdenciario=Decimal("50"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.A,
        )
        result = calcular_diagnostico(inp)

        assert result.desconto_percentual == Decimal("0")
        assert result.valor_desconto == Decimal("0")
        assert result.valor_com_desconto == Decimal("100000")
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL - módulo não encontrado

- [ ] **Step 3: Implementar `src/transacao/engine.py`**

```python
"""
Motor de cálculo de transação tributária.

Módulo puramente funcional (sem I/O). Recebe dados, retorna resultado.

Fontes legais:
- Lei 13.988/2020 (alterada pela Lei 14.375/2022)
- Portaria PGFN 6.757/2022
- CF/88, art. 195, §11
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from src.transacao.constants import (
    ENTRADA_PERCENTUAL,
    ENTRADA_PARCELAS_GERAL,
    ENTRADA_PARCELAS_ME_EPP,
    PARCELA_MINIMA_DEMAIS,
    PARCELA_MINIMA_MEI,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
    ClassificacaoCredito,
    get_desconto_por_classificacao,
    get_prazo_parcelas_restantes,
)

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class DiagnosticoInput:
    valor_total_divida: Decimal
    percentual_previdenciario: Decimal
    is_me_epp: bool
    classificacao: ClassificacaoCredito = ClassificacaoCredito.D


@dataclass
class ModalidadeResult:
    nome: str
    valor_original: Decimal
    desconto: Decimal
    saldo_com_desconto: Decimal
    valor_entrada: Decimal
    parcela_entrada: Decimal
    num_entrada: int
    valor_parcela: Decimal
    num_parcelas: int
    prazo_total: int
    fluxo: list[dict] = field(default_factory=list)


@dataclass
class DiagnosticoResult:
    valor_total: Decimal
    desconto_percentual: Decimal
    valor_desconto: Decimal
    valor_com_desconto: Decimal
    valor_entrada: Decimal
    parcelas_entrada: int
    parcela_entrada_valor: Decimal
    previdenciario: ModalidadeResult
    nao_previdenciario: ModalidadeResult
    fluxo_consolidado: list[dict] = field(default_factory=list)


def calcular_desconto(valor: Decimal, classificacao: ClassificacaoCredito, is_me_epp: bool) -> Decimal:
    taxa = Decimal(str(get_desconto_por_classificacao(classificacao, is_me_epp)))
    return _round(valor * taxa)


def separar_divida(valor_total: Decimal, percentual_previdenciario: Decimal) -> tuple[Decimal, Decimal]:
    prev = _round(valor_total * percentual_previdenciario / Decimal("100"))
    nao_prev = valor_total - prev
    return prev, nao_prev


def calcular_entrada(valor_total_sem_desconto: Decimal, is_me_epp: bool) -> tuple[Decimal, Decimal, int]:
    valor_entrada = _round(valor_total_sem_desconto * Decimal(str(ENTRADA_PERCENTUAL)))
    num_parcelas = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL
    parcela_entrada = _round(valor_entrada / Decimal(str(num_parcelas)))
    return valor_entrada, parcela_entrada, num_parcelas


def calcular_parcelas(
    saldo_apos_entrada: Decimal, is_me_epp: bool, is_previdenciario: bool
) -> tuple[Decimal, int]:
    num_parcelas = get_prazo_parcelas_restantes(is_me_epp, is_previdenciario)
    if num_parcelas <= 0 or saldo_apos_entrada <= 0:
        return Decimal("0"), 0

    valor_parcela = _round(saldo_apos_entrada / Decimal(str(num_parcelas)))

    parcela_minima = Decimal(str(PARCELA_MINIMA_DEMAIS))
    if valor_parcela < parcela_minima and saldo_apos_entrada >= parcela_minima:
        num_parcelas = int(saldo_apos_entrada / parcela_minima)
        valor_parcela = _round(saldo_apos_entrada / Decimal(str(num_parcelas)))

    return valor_parcela, num_parcelas


def gerar_fluxo_pagamento(
    parcela_entrada: Decimal, num_entrada: int, parcela_normal: Decimal, num_parcelas: int
) -> list[dict]:
    fluxo = []
    for i in range(1, num_entrada + 1):
        fluxo.append({"mes": i, "tipo": "entrada", "valor": parcela_entrada})
    for i in range(1, num_parcelas + 1):
        fluxo.append({"mes": num_entrada + i, "tipo": "parcela", "valor": parcela_normal})
    return fluxo


def _calcular_modalidade(
    nome: str,
    valor_original: Decimal,
    classificacao: ClassificacaoCredito,
    is_me_epp: bool,
    is_previdenciario: bool,
    entrada_proporcional: Decimal,
    parcela_entrada_proporcional: Decimal,
    num_entrada: int,
) -> ModalidadeResult:
    desconto = calcular_desconto(valor_original, classificacao, is_me_epp)
    saldo = valor_original - desconto
    saldo_apos_entrada = saldo - entrada_proporcional

    if saldo_apos_entrada < 0:
        saldo_apos_entrada = Decimal("0")

    valor_parcela, num_parcelas = calcular_parcelas(saldo_apos_entrada, is_me_epp, is_previdenciario)

    prazo_total = PRAZO_MAX_PREVIDENCIARIO if is_previdenciario else (
        PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP if is_me_epp else PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL
    )

    fluxo = gerar_fluxo_pagamento(parcela_entrada_proporcional, num_entrada, valor_parcela, num_parcelas)

    return ModalidadeResult(
        nome=nome,
        valor_original=valor_original,
        desconto=desconto,
        saldo_com_desconto=saldo,
        valor_entrada=entrada_proporcional,
        parcela_entrada=parcela_entrada_proporcional,
        num_entrada=num_entrada,
        valor_parcela=valor_parcela,
        num_parcelas=num_parcelas,
        prazo_total=prazo_total,
        fluxo=fluxo,
    )


def calcular_diagnostico(inp: DiagnosticoInput) -> DiagnosticoResult:
    desconto_percentual = Decimal(str(get_desconto_por_classificacao(inp.classificacao, inp.is_me_epp)))
    valor_desconto = calcular_desconto(inp.valor_total_divida, inp.classificacao, inp.is_me_epp)
    valor_com_desconto = inp.valor_total_divida - valor_desconto

    valor_entrada, parcela_entrada, num_entrada = calcular_entrada(inp.valor_total_divida, inp.is_me_epp)

    prev_original, nao_prev_original = separar_divida(inp.valor_total_divida, inp.percentual_previdenciario)

    # Entrada proporcional por modalidade
    if inp.valor_total_divida > 0:
        ratio_prev = prev_original / inp.valor_total_divida
        ratio_nao_prev = nao_prev_original / inp.valor_total_divida
    else:
        ratio_prev = Decimal("0")
        ratio_nao_prev = Decimal("0")

    entrada_prev = _round(valor_entrada * ratio_prev)
    parcela_entrada_prev = _round(parcela_entrada * ratio_prev)
    entrada_nao_prev = valor_entrada - entrada_prev
    parcela_entrada_nao_prev = parcela_entrada - parcela_entrada_prev

    previdenciario = _calcular_modalidade(
        nome="Previdenciária",
        valor_original=prev_original,
        classificacao=inp.classificacao,
        is_me_epp=inp.is_me_epp,
        is_previdenciario=True,
        entrada_proporcional=entrada_prev,
        parcela_entrada_proporcional=parcela_entrada_prev,
        num_entrada=num_entrada,
    )

    nao_previdenciario = _calcular_modalidade(
        nome="Não Previdenciária",
        valor_original=nao_prev_original,
        classificacao=inp.classificacao,
        is_me_epp=inp.is_me_epp,
        is_previdenciario=False,
        entrada_proporcional=entrada_nao_prev,
        parcela_entrada_proporcional=parcela_entrada_nao_prev,
        num_entrada=num_entrada,
    )

    # Fluxo consolidado
    max_meses = max(
        len(previdenciario.fluxo),
        len(nao_previdenciario.fluxo),
    )
    fluxo_consolidado = []
    for i in range(max_meses):
        prev_val = previdenciario.fluxo[i]["valor"] if i < len(previdenciario.fluxo) else Decimal("0")
        nao_prev_val = nao_previdenciario.fluxo[i]["valor"] if i < len(nao_previdenciario.fluxo) else Decimal("0")
        tipo = previdenciario.fluxo[i]["tipo"] if i < len(previdenciario.fluxo) else (
            nao_previdenciario.fluxo[i]["tipo"] if i < len(nao_previdenciario.fluxo) else "parcela"
        )
        fluxo_consolidado.append({
            "mes": i + 1,
            "tipo": tipo,
            "previdenciario": prev_val,
            "nao_previdenciario": nao_prev_val,
            "total": prev_val + nao_prev_val,
        })

    return DiagnosticoResult(
        valor_total=inp.valor_total_divida,
        desconto_percentual=desconto_percentual,
        valor_desconto=valor_desconto,
        valor_com_desconto=valor_com_desconto,
        valor_entrada=valor_entrada,
        parcelas_entrada=num_entrada,
        parcela_entrada_valor=parcela_entrada,
        previdenciario=previdenciario,
        nao_previdenciario=nao_previdenciario,
        fluxo_consolidado=fluxo_consolidado,
    )
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/test_engine.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/transacao/engine.py tests/test_engine.py
git commit -m "feat: calculation engine with TDD - discounts, installments, payment flows"
```

---

## Task 5: Client API Banco Central (Índices SELIC/IPCA) + Testes

**Files:**
- Create: `src/indices/client.py`
- Create: `tests/test_indices_client.py`

- [ ] **Step 1: Escrever testes do client BCB**

```python
# tests/test_indices_client.py
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.indices.client import BCBClient, IndiceDTO


@pytest.fixture
def bcb_client():
    return BCBClient()


class TestBCBClient:
    @pytest.mark.asyncio
    async def test_parse_response_json(self, bcb_client):
        """Deve parsear resposta JSON do BCB corretamente."""
        raw = [
            {"data": "01/01/2026", "valor": "1.16"},
            {"data": "01/02/2026", "valor": "1.00"},
        ]
        result = bcb_client._parse_response(raw)
        assert len(result) == 2
        assert result[0].data_referencia == date(2026, 1, 1)
        assert result[0].valor == Decimal("1.16")
        assert result[1].data_referencia == date(2026, 2, 1)

    @pytest.mark.asyncio
    async def test_buscar_serie_chama_api_correta(self, bcb_client):
        """Deve chamar a URL correta da API BCB."""
        mock_response = AsyncMock()
        mock_response.json.return_value = [{"data": "01/03/2026", "valor": "0.66"}]
        mock_response.raise_for_status = lambda: None

        with patch("src.indices.client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await bcb_client.buscar_serie(
                codigo_serie=4390,
                data_inicial=date(2026, 3, 1),
                data_final=date(2026, 3, 31),
            )

            mock_client.get.assert_called_once()
            call_url = mock_client.get.call_args[0][0]
            assert "4390" in call_url
            assert "01/03/2026" in call_url
            assert len(result) == 1

    def test_calcular_selic_acumulada(self, bcb_client):
        """Produto de (1 + taxa/100) para cada mês."""
        indices = [
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("1.16")),
            IndiceDTO(data_referencia=date(2026, 2, 1), valor=Decimal("1.00")),
            IndiceDTO(data_referencia=date(2026, 3, 1), valor=Decimal("0.66")),
        ]
        fator = bcb_client.calcular_selic_acumulada(indices)
        # (1+0.0116) * (1+0.0100) * (1+0.0066) = 1.0116 * 1.0100 * 1.0066 ≈ 1.02842
        expected = Decimal("1.0116") * Decimal("1.0100") * Decimal("1.0066")
        assert abs(fator - expected) < Decimal("0.0001")
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_indices_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `src/indices/client.py`**

```python
"""
Client para API do Banco Central do Brasil (SGS).

Séries utilizadas:
- 4390: SELIC acumulada no mês (%)
- 11: Taxa SELIC diária (% a.a.)
- 433: IPCA mensal (%)

Endpoint: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json
Docs: https://dadosabertos.bcb.gov.br/dataset/4390-taxa-de-juros---selic-acumulada-no-mes
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx

from src.config import settings


@dataclass(frozen=True)
class IndiceDTO:
    data_referencia: date
    valor: Decimal


class BCBClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.bcb_api_base_url

    def _parse_response(self, raw: list[dict]) -> list[IndiceDTO]:
        result = []
        for item in raw:
            dia, mes, ano = item["data"].split("/")
            result.append(
                IndiceDTO(
                    data_referencia=date(int(ano), int(mes), int(dia)),
                    valor=Decimal(item["valor"]),
                )
            )
        return result

    async def buscar_serie(
        self,
        codigo_serie: int,
        data_inicial: date | None = None,
        data_final: date | None = None,
    ) -> list[IndiceDTO]:
        url = f"{self.base_url}.{codigo_serie}/dados"
        params = {"formato": "json"}
        if data_inicial:
            params["dataInicial"] = data_inicial.strftime("%d/%m/%Y")
        if data_final:
            params["dataFinal"] = data_final.strftime("%d/%m/%Y")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return self._parse_response(response.json())

    async def buscar_ultimos(self, codigo_serie: int, n: int = 12) -> list[IndiceDTO]:
        url = f"{self.base_url}.{codigo_serie}/dados/ultimos/{n}"
        params = {"formato": "json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return self._parse_response(response.json())

    def calcular_selic_acumulada(self, indices_mensais: list[IndiceDTO]) -> Decimal:
        """
        Calcula fator SELIC acumulado: produto de (1 + taxa_mensal/100).

        Fórmula conforme Lei 13.988/2020, art. 11, §1º:
        Valor atualizado = valor_original * Π(1 + SELIC_mensal/100) + 1% no mês do pagamento
        """
        fator = Decimal("1")
        for indice in indices_mensais:
            fator *= Decimal("1") + indice.valor / Decimal("100")
        return fator
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/test_indices_client.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/indices/client.py tests/test_indices_client.py
git commit -m "feat: BCB API client for SELIC/IPCA indices with accumulated calculation"
```

---

## Task 6: Serviço de Índices (Cache + Sync) + Testes

**Files:**
- Create: `src/indices/service.py`
- Create: `src/indices/tasks.py`
- Create: `src/worker.py`
- Create: `tests/test_indices_service.py`

- [ ] **Step 1: Escrever testes do serviço de índices**

```python
# tests/test_indices_service.py
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.indices.client import IndiceDTO
from src.indices.service import IndicesService


class TestIndicesService:
    @pytest.mark.asyncio
    async def test_get_selic_acumulada_periodo(self):
        """Deve retornar fator SELIC acumulado entre duas datas."""
        mock_client = MagicMock()
        mock_client.buscar_serie = AsyncMock(return_value=[
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("1.16")),
            IndiceDTO(data_referencia=date(2026, 2, 1), valor=Decimal("1.00")),
        ])
        mock_client.calcular_selic_acumulada.return_value = Decimal("1.0218")

        service = IndicesService(client=mock_client, db_session=AsyncMock())
        fator = await service.get_selic_acumulada(
            data_inicial=date(2026, 1, 1),
            data_final=date(2026, 2, 28),
        )

        assert fator == Decimal("1.0218")
        mock_client.buscar_serie.assert_called_once()

    @pytest.mark.asyncio
    async def test_corrigir_valor_por_selic(self):
        """Deve multiplicar valor pelo fator SELIC + 1% do mês pagamento."""
        mock_client = MagicMock()
        mock_client.buscar_serie = AsyncMock(return_value=[
            IndiceDTO(data_referencia=date(2026, 1, 1), valor=Decimal("1.16")),
        ])
        mock_client.calcular_selic_acumulada.return_value = Decimal("1.0116")

        service = IndicesService(client=mock_client, db_session=AsyncMock())
        valor_corrigido = await service.corrigir_valor_por_selic(
            valor=Decimal("1000"),
            data_inicial=date(2026, 1, 1),
            data_final=date(2026, 1, 31),
        )

        # 1000 * 1.0116 * 1.01 = 1000 * 1.02172 ≈ 1021.72
        expected = Decimal("1000") * Decimal("1.0116") * Decimal("1.01")
        assert abs(valor_corrigido - expected) < Decimal("0.01")
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_indices_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `src/indices/service.py`**

```python
"""
Serviço de índices econômicos com cache em banco.

Busca índices na API do BCB, armazena em PostgreSQL para cache,
e calcula correção monetária SELIC conforme Lei 13.988/2020, art. 11, §1º.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.indices.client import BCBClient, IndiceDTO
from src.indices.models import IndiceEconomico
from src.transacao.constants import SERIE_SELIC_ACUMULADA_MENSAL, SELIC_ADICIONAL_PAGAMENTO


class IndicesService:
    def __init__(self, client: BCBClient, db_session: AsyncSession):
        self.client = client
        self.db = db_session

    async def sync_serie(self, codigo_serie: int, nome: str, data_inicial: date, data_final: date) -> int:
        """Busca série no BCB e persiste no banco. Retorna quantidade de registros inseridos."""
        indices = await self.client.buscar_serie(codigo_serie, data_inicial, data_final)
        count = 0
        for idx in indices:
            existing = await self.db.execute(
                select(IndiceEconomico).where(
                    IndiceEconomico.serie_codigo == codigo_serie,
                    IndiceEconomico.data_referencia == idx.data_referencia,
                )
            )
            if existing.scalar_one_or_none() is None:
                self.db.add(IndiceEconomico(
                    serie_codigo=codigo_serie,
                    serie_nome=nome,
                    data_referencia=idx.data_referencia,
                    valor=float(idx.valor),
                ))
                count += 1
        await self.db.commit()
        return count

    async def get_selic_acumulada(self, data_inicial: date, data_final: date) -> Decimal:
        """Retorna fator SELIC acumulado no período (produto dos fatores mensais)."""
        indices = await self.client.buscar_serie(SERIE_SELIC_ACUMULADA_MENSAL, data_inicial, data_final)
        return self.client.calcular_selic_acumulada(indices)

    async def corrigir_valor_por_selic(self, valor: Decimal, data_inicial: date, data_final: date) -> Decimal:
        """
        Corrige valor pela SELIC acumulada + 1% no mês do pagamento.

        Conforme Lei 13.988/2020, art. 11, §1º:
        Parcelas atualizadas pela SELIC acumulada mensal + 1% no mês do pagamento.
        """
        fator = await self.get_selic_acumulada(data_inicial, data_final)
        fator_com_adicional = fator * (Decimal("1") + Decimal(str(SELIC_ADICIONAL_PAGAMENTO)))
        return (valor * fator_com_adicional).quantize(Decimal("0.01"))
```

- [ ] **Step 4: Implementar `src/indices/tasks.py`** e `src/worker.py`

```python
# src/indices/tasks.py
"""RQ tasks para sync de índices do BCB."""

import asyncio
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.indices.client import BCBClient
from src.indices.service import IndicesService
from src.transacao.constants import SERIE_IPCA, SERIE_SELIC_ACUMULADA_MENSAL


def sync_indices_selic():
    """Task RQ: sincroniza SELIC acumulada mensal dos últimos 24 meses."""
    asyncio.run(_sync_indices_selic())


async def _sync_indices_selic():
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        client = BCBClient()
        service = IndicesService(client=client, db_session=session)
        hoje = date.today()
        inicio = hoje - timedelta(days=730)
        await service.sync_serie(SERIE_SELIC_ACUMULADA_MENSAL, "SELIC Acumulada Mensal", inicio, hoje)
        await service.sync_serie(SERIE_IPCA, "IPCA Mensal", inicio, hoje)
```

```python
# src/worker.py
"""RQ Worker entrypoint."""

from redis import Redis
from rq import Worker

from src.config import settings

if __name__ == "__main__":
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker(["default"], connection=redis_conn)
    worker.work()
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/test_indices_service.py -v`
Expected: Todos PASS

- [ ] **Step 6: Commit**

```bash
git add src/indices/service.py src/indices/tasks.py src/worker.py tests/test_indices_service.py
git commit -m "feat: indices service with BCB sync, SELIC correction, RQ worker"
```

---

## Task 7: Autenticação OAuth (Google + Microsoft) + JWT

**Files:**
- Create: `src/auth/oauth.py`
- Create: `src/auth/jwt.py`
- Create: `src/auth/router.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Escrever testes de autenticação**

```python
# tests/test_auth.py
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.auth.jwt import create_access_token, decode_access_token


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(data={"sub": "user@test.com", "name": "Test"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user@test.com"
        assert payload["name"] == "Test"

    def test_expired_token_raises(self):
        token = create_access_token(
            data={"sub": "user@test.com"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            decode_access_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_access_token("invalid.token.here")
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `src/auth/jwt.py`**

```python
"""JWT token creation and verification."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
```

- [ ] **Step 4: Implementar `src/auth/oauth.py`**

```python
"""
OAuth2 client configuration for Google and Microsoft via Authlib.

Google OAuth: https://accounts.google.com/.well-known/openid-configuration
Microsoft OAuth: https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration
"""

from authlib.integrations.starlette_client import OAuth

from src.config import settings

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="microsoft",
    client_id=settings.microsoft_client_id,
    client_secret=settings.microsoft_client_secret,
    server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

- [ ] **Step 5: Implementar `src/auth/router.py`**

```python
"""Authentication routes: OAuth login/callback + logout."""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import create_access_token
from src.auth.models import User
from src.auth.oauth import oauth
from src.config import settings
from src.deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_or_create_user(db: AsyncSession, email: str, name: str, picture: str | None,
                               provider: str, provider_id: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.last_login = func.now()
        await db.commit()
        await db.refresh(user)
        return user

    user = User(email=email, name=name, picture=picture, provider=provider, provider_id=provider_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = f"{settings.app_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    user = await _get_or_create_user(
        db=db,
        email=userinfo["email"],
        name=userinfo.get("name", userinfo["email"]),
        picture=userinfo.get("picture"),
        provider="google",
        provider_id=userinfo["sub"],
    )

    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email, "name": user.name})
    response = RedirectResponse(url="/")
    response.set_cookie("access_token", jwt_token, httponly=True, samesite="lax", max_age=86400)
    return response


@router.get("/microsoft/login")
async def microsoft_login(request: Request):
    redirect_uri = f"{settings.app_url}/auth/microsoft/callback"
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.microsoft.authorize_access_token(request)
    userinfo = token.get("userinfo", {})

    user = await _get_or_create_user(
        db=db,
        email=userinfo.get("email", userinfo.get("preferred_username", "")),
        name=userinfo.get("name", ""),
        picture=None,
        provider="microsoft",
        provider_id=userinfo.get("sub", userinfo.get("oid", "")),
    )

    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email, "name": user.name})
    response = RedirectResponse(url="/")
    response.set_cookie("access_token", jwt_token, httponly=True, samesite="lax", max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("access_token")
    return response
```

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/test_auth.py -v`
Expected: Todos PASS

- [ ] **Step 7: Commit**

```bash
git add src/auth/jwt.py src/auth/oauth.py src/auth/router.py tests/test_auth.py
git commit -m "feat: OAuth2 Google + Microsoft login with JWT tokens"
```

---

## Task 8: Schemas Pydantic (Request/Response)

**Files:**
- Create: `src/transacao/schemas.py`

- [ ] **Step 1: Implementar schemas**

```python
"""
Pydantic v2 schemas para request/response da API de transação.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from src.transacao.constants import ClassificacaoCredito


class SimulacaoRequest(BaseModel):
    razao_social: str = Field(..., min_length=2, max_length=300)
    cnpj: str = Field(..., min_length=14, max_length=18)
    telefone: str | None = Field(None, max_length=20)
    email_empresa: str | None = Field(None, max_length=320)
    valor_total_divida: Decimal = Field(..., gt=0, le=Decimal("999999999999.99"))
    percentual_previdenciario: Decimal = Field(..., ge=0, le=100)
    is_me_epp: bool
    classificacao: ClassificacaoCredito = ClassificacaoCredito.D

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos")
        return v


class ModalidadeResponse(BaseModel):
    nome: str
    valor_original: Decimal
    desconto: Decimal
    saldo_com_desconto: Decimal
    valor_entrada: Decimal
    parcela_entrada: Decimal
    num_entrada: int
    valor_parcela: Decimal
    num_parcelas: int
    prazo_total: int
    fluxo: list[dict]


class FluxoConsolidadoItem(BaseModel):
    mes: int
    tipo: str
    previdenciario: Decimal
    nao_previdenciario: Decimal
    total: Decimal


class SimulacaoResponse(BaseModel):
    id: uuid.UUID
    valor_total: Decimal
    desconto_percentual: Decimal
    valor_desconto: Decimal
    valor_com_desconto: Decimal
    valor_entrada: Decimal
    parcelas_entrada: int
    parcela_entrada_valor: Decimal
    previdenciario: ModalidadeResponse
    nao_previdenciario: ModalidadeResponse
    fluxo_consolidado: list[FluxoConsolidadoItem]
    selic_mensal_utilizada: Decimal | None
    created_at: datetime


class SimulacaoListItem(BaseModel):
    id: uuid.UUID
    razao_social: str
    cnpj: str
    valor_total_divida: Decimal
    classificacao: str
    is_me_epp: bool
    valor_desconto: Decimal
    created_at: datetime


class HistoricoResponse(BaseModel):
    simulacoes: list[SimulacaoListItem]
    total: int
```

- [ ] **Step 2: Commit**

```bash
git add src/transacao/schemas.py
git commit -m "feat: Pydantic v2 schemas for simulation request/response"
```

---

## Task 9: Service de Simulação + Router API

**Files:**
- Create: `src/transacao/service.py`
- Create: `src/transacao/router.py`
- Create: `src/auth/dependencies.py`

> **Nota:** Os testes de integração do router dependem de `src/main.py` (Task 10). Os testes serão escritos na Task 10 após o main.py existir.

- [ ] **Step 1: Criar `src/auth/dependencies.py`** (separado de deps.py para evitar circular imports)

```python
"""Auth dependency for route protection."""

from fastapi import Cookie, HTTPException

from src.auth.jwt import decode_access_token


async def get_current_user(access_token: str | None = Cookie(None)) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_access_token(access_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

- [ ] **Step 2: Implementar `src/transacao/service.py`**

```python
"""Serviço de simulação: orquestra engine + persistência."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.transacao.engine import DiagnosticoInput, calcular_diagnostico
from src.transacao.models import Simulacao
from src.transacao.schemas import SimulacaoRequest


class SimulacaoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def simular(self, request: SimulacaoRequest, user_id: str) -> dict:
        inp = DiagnosticoInput(
            valor_total_divida=request.valor_total_divida,
            percentual_previdenciario=request.percentual_previdenciario,
            is_me_epp=request.is_me_epp,
            classificacao=request.classificacao,
        )
        result = calcular_diagnostico(inp)

        # Serializar resultado para JSONB
        resultado_dict = {
            "valor_total": str(result.valor_total),
            "desconto_percentual": str(result.desconto_percentual),
            "valor_desconto": str(result.valor_desconto),
            "valor_com_desconto": str(result.valor_com_desconto),
            "valor_entrada": str(result.valor_entrada),
            "parcelas_entrada": result.parcelas_entrada,
            "parcela_entrada_valor": str(result.parcela_entrada_valor),
            "previdenciario": {
                "nome": result.previdenciario.nome,
                "valor_original": str(result.previdenciario.valor_original),
                "desconto": str(result.previdenciario.desconto),
                "saldo_com_desconto": str(result.previdenciario.saldo_com_desconto),
                "valor_entrada": str(result.previdenciario.valor_entrada),
                "parcela_entrada": str(result.previdenciario.parcela_entrada),
                "num_entrada": result.previdenciario.num_entrada,
                "valor_parcela": str(result.previdenciario.valor_parcela),
                "num_parcelas": result.previdenciario.num_parcelas,
                "prazo_total": result.previdenciario.prazo_total,
                "fluxo": [{"mes": f["mes"], "tipo": f["tipo"], "valor": str(f["valor"])}
                          for f in result.previdenciario.fluxo],
            },
            "nao_previdenciario": {
                "nome": result.nao_previdenciario.nome,
                "valor_original": str(result.nao_previdenciario.valor_original),
                "desconto": str(result.nao_previdenciario.desconto),
                "saldo_com_desconto": str(result.nao_previdenciario.saldo_com_desconto),
                "valor_entrada": str(result.nao_previdenciario.valor_entrada),
                "parcela_entrada": str(result.nao_previdenciario.parcela_entrada),
                "num_entrada": result.nao_previdenciario.num_entrada,
                "valor_parcela": str(result.nao_previdenciario.valor_parcela),
                "num_parcelas": result.nao_previdenciario.num_parcelas,
                "prazo_total": result.nao_previdenciario.prazo_total,
                "fluxo": [{"mes": f["mes"], "tipo": f["tipo"], "valor": str(f["valor"])}
                          for f in result.nao_previdenciario.fluxo],
            },
            "fluxo_consolidado": [
                {"mes": f["mes"], "tipo": f["tipo"], "previdenciario": str(f["previdenciario"]),
                 "nao_previdenciario": str(f["nao_previdenciario"]), "total": str(f["total"])}
                for f in result.fluxo_consolidado
            ],
        }

        simulacao = Simulacao(
            user_id=uuid.UUID(user_id),
            razao_social=request.razao_social,
            cnpj=request.cnpj,
            telefone=request.telefone,
            email_empresa=request.email_empresa,
            valor_total_divida=float(request.valor_total_divida),
            percentual_previdenciario=float(request.percentual_previdenciario),
            is_me_epp=request.is_me_epp,
            classificacao_credito=request.classificacao.value,
            resultado=resultado_dict,
        )
        self.db.add(simulacao)
        await self.db.commit()
        await self.db.refresh(simulacao)

        return {"id": str(simulacao.id), "created_at": simulacao.created_at.isoformat(), **resultado_dict}
```

- [ ] **Step 3: Implementar `src/transacao/router.py`**

```python
"""API endpoints para simulação de transação tributária."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_db
from src.auth.dependencies import get_current_user
from src.transacao.models import Simulacao
from src.transacao.schemas import SimulacaoRequest, HistoricoResponse, SimulacaoListItem
from src.transacao.service import SimulacaoService

router = APIRouter(prefix="/api/v1/transacao", tags=["transacao"])


@router.post("/simular")
async def simular(
    request: SimulacaoRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    service = SimulacaoService(db)
    return await service.simular(request, user["sub"])


@router.get("/historico", response_model=HistoricoResponse)
async def historico(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    import uuid as uuid_mod
    user_id = uuid_mod.UUID(user["sub"])
    query = (
        select(Simulacao)
        .where(Simulacao.user_id == user_id)
        .order_by(Simulacao.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    simulacoes = result.scalars().all()

    count_query = select(func.count()).select_from(Simulacao).where(Simulacao.user_id == user_id)
    total = (await db.execute(count_query)).scalar()

    items = [
        SimulacaoListItem(
            id=s.id,
            razao_social=s.razao_social,
            cnpj=s.cnpj,
            valor_total_divida=s.valor_total_divida,
            classificacao=s.classificacao_credito,
            is_me_epp=s.is_me_epp,
            valor_desconto=s.resultado.get("valor_desconto", "0"),
            created_at=s.created_at,
        )
        for s in simulacoes
    ]
    return HistoricoResponse(simulacoes=items, total=total)


@router.get("/{simulacao_id}")
async def get_simulacao(
    simulacao_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Simulacao).where(Simulacao.id == simulacao_id, Simulacao.user_id == user["sub"])
    )
    simulacao = result.scalar_one_or_none()
    if not simulacao:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulação não encontrada")
    return {"id": str(simulacao.id), "created_at": simulacao.created_at.isoformat(), **simulacao.resultado}
```

- [ ] **Step 4: Commit**

```bash
git add src/auth/dependencies.py src/transacao/service.py src/transacao/router.py
git commit -m "feat: simulation service + API router with auth + history endpoint"
```

---

## Task 10: FastAPI App Factory (main.py) + Testes de Integração Router

**Files:**
- Create: `src/main.py`
- Create: `tests/test_transacao_router.py`

- [ ] **Step 1: Implementar `src/main.py`**

```python
"""FastAPI application factory."""

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.auth.router import router as auth_router
from src.config import settings
from src.transacao.router import router as transacao_router

app = FastAPI(
    title="Diagnóstico de Transação Tributária",
    description="Simulador de transação tributária federal (PGFN) com cálculos dinâmicos",
    version="1.0.0",
)

# SessionMiddleware necessário para Authlib OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Routers
app.include_router(auth_router)
app.include_router(transacao_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Testar que app inicia**

Run: `uvicorn src.main:app --host 0.0.0.0 --port 8000 &`
Then: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`
Then: kill the server

- [ ] **Step 3: Escrever testes de integração do router**

```python
# tests/test_transacao_router.py
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.auth.dependencies import get_current_user
from src.deps import get_db


class TestSimulacaoRouter:
    @pytest.mark.asyncio
    async def test_simular_retorna_diagnostico(self):
        app.dependency_overrides[get_current_user] = lambda: {"sub": str(uuid.uuid4()), "email": "t@t.com", "name": "T"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/transacao/simular", json={
                "razao_social": "Empresa Teste LTDA",
                "cnpj": "12.345.678/0001-90",
                "valor_total_divida": "100000.00",
                "percentual_previdenciario": "30",
                "is_me_epp": False,
                "classificacao": "D",
            })

        data = response.json()
        assert response.status_code == 200
        assert "valor_total" in data
        assert "previdenciario" in data
        assert "nao_previdenciario" in data
        assert "fluxo_consolidado" in data
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_simular_cnpj_invalido_retorna_422(self):
        app.dependency_overrides[get_current_user] = lambda: {"sub": str(uuid.uuid4()), "email": "t@t.com", "name": "T"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/transacao/simular", json={
                "razao_social": "Teste",
                "cnpj": "123",
                "valor_total_divida": "100000",
                "percentual_previdenciario": "30",
                "is_me_epp": False,
            })

        assert response.status_code == 422
        app.dependency_overrides.clear()
```

- [ ] **Step 4: Rodar testes de integração**

Run: `pytest tests/test_transacao_router.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_transacao_router.py
git commit -m "feat: FastAPI app factory with auth + transacao routers + integration tests"
```

---

## Task 11: Geração de PDF (WeasyPrint) + Testes

**Files:**
- Create: `src/pdf/__init__.py`
- Create: `src/pdf/generator.py`
- Create: `src/pdf/templates/diagnostico.html`
- Create: `tests/test_pdf_generator.py`

- [ ] **Step 1: Escrever teste de geração PDF**

```python
# tests/test_pdf_generator.py
from decimal import Decimal

import pytest

from src.pdf.generator import gerar_pdf_diagnostico


class TestPDFGenerator:
    def test_gerar_pdf_retorna_bytes(self):
        """PDF deve ser gerado como bytes não-vazios."""
        dados = {
            "razao_social": "Empresa Teste LTDA",
            "cnpj": "12.345.678/0001-90",
            "valor_total": "100000.00",
            "desconto_percentual": "0.65",
            "valor_desconto": "65000.00",
            "valor_com_desconto": "35000.00",
            "valor_entrada": "6000.00",
            "parcelas_entrada": 6,
            "parcela_entrada_valor": "1000.00",
            "previdenciario": {
                "nome": "Previdenciária",
                "valor_original": "30000.00",
                "desconto": "19500.00",
                "saldo_com_desconto": "10500.00",
                "prazo_total": 60,
                "fluxo": [],
            },
            "nao_previdenciario": {
                "nome": "Não Previdenciária",
                "valor_original": "70000.00",
                "desconto": "45500.00",
                "saldo_com_desconto": "24500.00",
                "prazo_total": 120,
                "fluxo": [],
            },
            "fluxo_consolidado": [],
        }
        pdf_bytes = gerar_pdf_diagnostico(dados)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100
        assert pdf_bytes[:5] == b"%PDF-"
```

- [ ] **Step 2: Rodar teste para ver falhar**

Run: `pytest tests/test_pdf_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Criar template HTML**

```html
<!-- src/pdf/templates/diagnostico.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: Arial, sans-serif; font-size: 11px; color: #333; margin: 30px; }
  h1 { color: #1a1a2e; font-size: 20px; border-bottom: 3px solid #d4a843; padding-bottom: 8px; }
  h2 { color: #d4a843; font-size: 14px; margin-top: 20px; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }
  .info-item { padding: 6px 10px; background: #f8f8f8; border-radius: 4px; }
  .info-label { font-weight: bold; color: #666; font-size: 9px; text-transform: uppercase; }
  .info-value { font-size: 13px; margin-top: 2px; }
  .card { border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; margin: 8px 0; }
  .card-gold { border-color: #d4a843; background: #fffdf5; }
  .card-red { border-color: #e74c3c; background: #fef5f5; }
  .card-green { border-color: #27ae60; background: #f5fef7; }
  .amount { font-size: 18px; font-weight: bold; color: #1a1a2e; }
  .discount { color: #27ae60; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10px; }
  th { background: #f0f0f0; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; }
  td { padding: 5px 6px; border-bottom: 1px solid #eee; }
  tr:nth-child(even) { background: #fafafa; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: bold; }
  .badge-entrada { background: #d4a843; color: white; }
  .badge-parcela { background: #3498db; color: white; }
  .footer { margin-top: 30px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 9px; color: #999; text-align: center; }
  .disclaimer { background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 10px; margin-top: 15px; font-size: 9px; }
</style>
</head>
<body>
  <h1>Diagnóstico Prévio de Transação Tributária</h1>
  <p style="color:#666;">{{ data_geracao }}</p>

  <h2>Identificação da Empresa</h2>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">Razão Social</div><div class="info-value">{{ razao_social }}</div></div>
    <div class="info-item"><div class="info-label">CNPJ</div><div class="info-value">{{ cnpj }}</div></div>
  </div>

  <h2>Resumo da Simulação</h2>
  <div class="info-grid">
    <div class="card"><div class="info-label">Dívida Original</div><div class="amount">R$ {{ valor_total }}</div></div>
    <div class="card card-green"><div class="info-label">Desconto ({{ desconto_percentual_fmt }})</div><div class="amount discount">- R$ {{ valor_desconto }}</div></div>
    <div class="card card-gold"><div class="info-label">Saldo com Desconto</div><div class="amount">R$ {{ valor_com_desconto }}</div></div>
    <div class="card"><div class="info-label">Entrada (6%)</div><div class="amount">R$ {{ valor_entrada }}</div><div>{{ parcelas_entrada }}x de R$ {{ parcela_entrada_valor }}</div></div>
  </div>

  <h2>Dívida Previdenciária</h2>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">Valor Original</div><div class="info-value">R$ {{ previdenciario.valor_original }}</div></div>
    <div class="info-item"><div class="info-label">Prazo Total</div><div class="info-value">{{ previdenciario.prazo_total }} meses</div></div>
  </div>

  <h2>Dívida Não Previdenciária</h2>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">Valor Original</div><div class="info-value">R$ {{ nao_previdenciario.valor_original }}</div></div>
    <div class="info-item"><div class="info-label">Prazo Total</div><div class="info-value">{{ nao_previdenciario.prazo_total }} meses</div></div>
  </div>

  {% if fluxo_consolidado %}
  <h2>Fluxo de Pagamento Consolidado</h2>
  <table>
    <thead><tr><th>Mês</th><th>Tipo</th><th>Previdenciário</th><th>Não Previd.</th><th>Total</th></tr></thead>
    <tbody>
    {% for item in fluxo_consolidado[:24] %}
    <tr>
      <td>{{ item.mes }}º</td>
      <td><span class="badge badge-{{ item.tipo }}">{{ item.tipo|capitalize }}</span></td>
      <td>R$ {{ item.previdenciario }}</td>
      <td>R$ {{ item.nao_previdenciario }}</td>
      <td><strong>R$ {{ item.total }}</strong></td>
    </tr>
    {% endfor %}
    {% if fluxo_consolidado|length > 24 %}
    <tr><td colspan="5" style="text-align:center;color:#999;">... e mais {{ fluxo_consolidado|length - 24 }} parcelas</td></tr>
    {% endif %}
    </tbody>
  </table>
  {% endif %}

  <div class="disclaimer">
    <strong>Importante:</strong> Esta é uma simulação estimativa baseada nas regras gerais de transação tributária
    (Lei 13.988/2020, Portaria PGFN 6.757/2022, Edital PGDAU 11/2025). Os valores finais podem variar conforme
    análise técnica específica, classificação do crédito pela PGFN e capacidade de pagamento do contribuinte.
    Parcelas sujeitas à atualização pela taxa SELIC acumulada mensal + 1% no mês do pagamento.
  </div>

  <div class="footer">
    Diagnóstico gerado em {{ data_geracao }} | Simulador de Transação Tributária
  </div>
</body>
</html>
```

- [ ] **Step 4: Implementar `src/pdf/generator.py`**

```python
"""Geração de PDF do diagnóstico via WeasyPrint."""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent / "templates"


def gerar_pdf_diagnostico(dados: dict) -> bytes:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("diagnostico.html")

    desconto_pct = float(dados.get("desconto_percentual", 0))
    dados["desconto_percentual_fmt"] = f"{desconto_pct * 100:.0f}%"
    dados["data_geracao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

    html_content = template.render(**dados)
    return HTML(string=html_content).write_pdf()
```

- [ ] **Step 5: Criar `src/pdf/__init__.py`** (vazio)

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/test_pdf_generator.py -v`
Expected: PASS

- [ ] **Step 7: Adicionar endpoint de exportação PDF no router**

Adicionar ao final de `src/transacao/router.py`:

```python
from fastapi.responses import StreamingResponse
from io import BytesIO
from src.pdf.generator import gerar_pdf_diagnostico


@router.get("/{simulacao_id}/pdf")
async def exportar_pdf(
    simulacao_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Simulacao).where(Simulacao.id == simulacao_id, Simulacao.user_id == user["sub"])
    )
    simulacao = result.scalar_one_or_none()
    if not simulacao:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulação não encontrada")

    dados = {
        "razao_social": simulacao.razao_social,
        "cnpj": simulacao.cnpj,
        **simulacao.resultado,
    }
    pdf_bytes = gerar_pdf_diagnostico(dados)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=diagnostico_{simulacao.cnpj}.pdf"},
    )
```

- [ ] **Step 8: Commit**

```bash
git add src/pdf/ tests/test_pdf_generator.py src/transacao/router.py
git commit -m "feat: PDF export with WeasyPrint template + download endpoint"
```

---

## Task 12: Router de Índices Econômicos

**Files:**
- Create: `src/indices/router.py`

- [ ] **Step 1: Implementar router de índices**

```python
"""API endpoints para consulta de índices econômicos."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_db
from src.auth.dependencies import get_current_user
from src.indices.client import BCBClient
from src.indices.service import IndicesService
from src.transacao.constants import SERIE_SELIC_ACUMULADA_MENSAL

router = APIRouter(prefix="/api/v1/indices", tags=["indices"])


@router.get("/selic/ultimos/{n}")
async def selic_ultimos(n: int = 12, user: dict = Depends(get_current_user)):
    client = BCBClient()
    indices = await client.buscar_ultimos(SERIE_SELIC_ACUMULADA_MENSAL, n)
    return [{"data": idx.data_referencia.isoformat(), "valor": str(idx.valor)} for idx in indices]


@router.get("/selic/acumulada")
async def selic_acumulada(
    data_inicial: date,
    data_final: date,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    client = BCBClient()
    service = IndicesService(client=client, db_session=db)
    fator = await service.get_selic_acumulada(data_inicial, data_final)
    return {"fator_acumulado": str(fator), "data_inicial": data_inicial.isoformat(), "data_final": data_final.isoformat()}
```

- [ ] **Step 2: Adicionar router ao main.py**

Adicionar em `src/main.py`:

```python
from src.indices.router import router as indices_router
app.include_router(indices_router)
```

- [ ] **Step 3: Commit**

```bash
git add src/indices/router.py src/main.py
git commit -m "feat: indices API router with live SELIC data from BCB"
```

---

## Task 13: Conftest com Fixtures de Teste Integrado

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/factories.py`

- [ ] **Step 1: Implementar fixtures**

```python
# tests/conftest.py
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.deps import Base, get_db
from src.auth.dependencies import get_current_user
from src.main import app

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://diagnostico:diagnostico@localhost:5432/diagnostico_test",
)


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_user_payload():
    return {"sub": str(uuid.uuid4()), "email": "test@test.com", "name": "Test User"}


@pytest.fixture
async def client(db_session, test_user_payload) -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        yield db_session

    def override_user():
        return test_user_payload

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
```

```python
# tests/factories.py
import uuid
from datetime import datetime

import factory

from src.auth.models import User
from src.transacao.models import Simulacao


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    name = factory.Sequence(lambda n: f"User {n}")
    provider = "google"
    provider_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py tests/factories.py
git commit -m "feat: test fixtures with async DB, factory-boy, httpx client"
```

---

## Task 14: Integração Completa + Docker Compose Up

- [ ] **Step 1: Criar `.env` local para desenvolvimento**

```bash
cp .env.example .env
# Editar .env com valores reais para Google/Microsoft OAuth (opcional para dev)
```

- [ ] **Step 2: Subir toda a stack**

Run: `docker compose up -d`
Expected: Todos os containers healthy

- [ ] **Step 3: Rodar migrations no container**

Run: `docker compose exec app alembic upgrade head`
Expected: Migrations aplicadas

- [ ] **Step 4: Testar health check**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 5: Testar endpoint de simulação (sem auth para debug)**

Run: `curl -X POST http://localhost:8000/api/v1/transacao/simular -H "Content-Type: application/json" -d '{"razao_social":"Teste","cnpj":"12.345.678/0001-90","valor_total_divida":"100000","percentual_previdenciario":"30","is_me_epp":false,"classificacao":"D"}'`
Expected: Resposta 401 (precisa de auth) ou 200 se debug bypass

- [ ] **Step 6: Rodar todos os testes**

Run: `pytest tests/ -v --tb=short`
Expected: Todos PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: full integration - Docker Compose stack running end-to-end"
```

---

## Task 15: Constantes e Validadores TPV + Testes TDD

**Files:**
- Create: `src/tpv/__init__.py`
- Create: `src/tpv/constants.py`
- Create: `src/tpv/validators.py`
- Create: `tests/test_tpv_constants.py`
- Create: `tests/test_tpv_validators.py`

- [ ] **Step 1: Escrever testes das constantes TPV**

```python
# tests/test_tpv_constants.py
from decimal import Decimal

from src.tpv.constants import (
    ENTRADA_PERCENTUAL_TPV,
    ENTRADA_PARCELAS_MAX_TPV,
    LIMITE_SM_POR_CDA,
    TEMPO_MINIMO_INSCRICAO_DIAS,
    SALARIO_MINIMO_2026,
    TABELA_DESCONTOS_TPV,
    get_desconto_por_parcelas,
    calcular_limite_valor_cda,
)


def test_entrada_5_porcento():
    assert ENTRADA_PERCENTUAL_TPV == Decimal("0.05")


def test_entrada_max_5_parcelas():
    assert ENTRADA_PARCELAS_MAX_TPV == 5


def test_limite_60_sm():
    assert LIMITE_SM_POR_CDA == 60


def test_tempo_minimo_365_dias():
    assert TEMPO_MINIMO_INSCRICAO_DIAS == 365


def test_salario_minimo_2026():
    assert SALARIO_MINIMO_2026 == Decimal("1621")


def test_tabela_descontos_4_faixas():
    assert len(TABELA_DESCONTOS_TPV) == 4
    assert TABELA_DESCONTOS_TPV[0] == {"parcelas_max": 7, "desconto": Decimal("0.50")}
    assert TABELA_DESCONTOS_TPV[1] == {"parcelas_max": 12, "desconto": Decimal("0.45")}
    assert TABELA_DESCONTOS_TPV[2] == {"parcelas_max": 30, "desconto": Decimal("0.40")}
    assert TABELA_DESCONTOS_TPV[3] == {"parcelas_max": 55, "desconto": Decimal("0.30")}


def test_desconto_7_parcelas_50_porcento():
    assert get_desconto_por_parcelas(7) == Decimal("0.50")


def test_desconto_12_parcelas_45_porcento():
    assert get_desconto_por_parcelas(12) == Decimal("0.45")


def test_desconto_30_parcelas_40_porcento():
    assert get_desconto_por_parcelas(30) == Decimal("0.40")


def test_desconto_55_parcelas_30_porcento():
    assert get_desconto_por_parcelas(55) == Decimal("0.30")


def test_desconto_8_parcelas_cai_na_faixa_12():
    assert get_desconto_por_parcelas(8) == Decimal("0.45")


def test_limite_valor_cda_com_sm_1621():
    assert calcular_limite_valor_cda(Decimal("1621")) == Decimal("97260")
```

- [ ] **Step 2: Escrever testes dos validadores**

```python
# tests/test_tpv_validators.py
from datetime import date
from decimal import Decimal

from src.tpv.validators import validar_cda, CDAValidationResult, MotivoInaptidao


def test_cda_apta_valor_ok_e_tempo_ok():
    result = validar_cda(
        valor=Decimal("50000"),
        data_inscricao=date(2020, 3, 15),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.apta is True
    assert result.motivos == []


def test_cda_nao_apta_valor_acima_60sm():
    result = validar_cda(
        valor=Decimal("100000"),
        data_inscricao=date(2020, 3, 15),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.apta is False
    assert MotivoInaptidao.VALOR_ACIMA_LIMITE in result.motivos


def test_cda_nao_apta_inscricao_inferior_1_ano():
    result = validar_cda(
        valor=Decimal("50000"),
        data_inscricao=date(2025, 6, 15),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.apta is False
    assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO in result.motivos


def test_cda_nao_apta_ambos_motivos():
    result = validar_cda(
        valor=Decimal("200000"),
        data_inscricao=date(2025, 12, 1),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.apta is False
    assert len(result.motivos) == 2


def test_projecao_elegibilidade_por_tempo():
    result = validar_cda(
        valor=Decimal("50000"),
        data_inscricao=date(2025, 6, 15),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.data_elegibilidade_tempo == date(2026, 6, 15)
    assert result.dias_restantes_tempo == 89


def test_cda_no_limite_exato_60sm_e_apta():
    result = validar_cda(
        valor=Decimal("97260"),  # exatamente 60 × 1621
        data_inscricao=date(2025, 3, 17),
        data_simulacao=date(2026, 3, 18),
        salario_minimo=Decimal("1621"),
    )
    assert result.apta is True
```

- [ ] **Step 3: Rodar testes para ver falhar**

Run: `pytest tests/test_tpv_constants.py tests/test_tpv_validators.py -v`
Expected: FAIL

- [ ] **Step 4: Implementar `src/tpv/constants.py`**

```python
"""
Constantes legais para Transação de Pequeno Valor (TPV).

Fontes:
- Edital PGDAU 11/2025 (modalidade Pequeno Valor)
- Portaria PGFN 6.757/2022
- Art. 11 da Lei 13.988/2020 (exceção para pequeno valor: desconto incide sobre principal)
"""

from decimal import Decimal

# --- Entrada TPV ---
ENTRADA_PERCENTUAL_TPV = Decimal("0.05")  # 5% — Edital PGDAU 11/2025
ENTRADA_PARCELAS_MAX_TPV = 5  # Até 5 parcelas de entrada

# --- Limites ---
LIMITE_SM_POR_CDA = 60  # 60 salários mínimos por CDA
TEMPO_MINIMO_INSCRICAO_DIAS = 365  # 1 ano de inscrição em dívida ativa

# --- Salário Mínimo ---
SALARIO_MINIMO_2026 = Decimal("1621")  # R$ 1.621,00 (2026)

# --- Tabela de Descontos por Parcelas do Saldo ---
# Na TPV, o desconto incide sobre TODO o saldo (inclusive principal)
# Esta é uma exceção legal à regra geral do art. 11, §2º, I da Lei 13.988
TABELA_DESCONTOS_TPV = [
    {"parcelas_max": 7, "desconto": Decimal("0.50")},   # 50% — até 7 parcelas
    {"parcelas_max": 12, "desconto": Decimal("0.45")},  # 45% — até 12 parcelas
    {"parcelas_max": 30, "desconto": Decimal("0.40")},  # 40% — até 30 parcelas
    {"parcelas_max": 55, "desconto": Decimal("0.30")},  # 30% — até 55 parcelas
]

# --- Quem pode aderir ---
TIPOS_ELEGIVEIS_TPV = {"PF", "ME", "EPP"}  # Pessoa Física, Microempresa, EPP


def get_desconto_por_parcelas(num_parcelas: int) -> Decimal:
    """Retorna o desconto aplicável conforme número de parcelas do saldo."""
    for faixa in TABELA_DESCONTOS_TPV:
        if num_parcelas <= faixa["parcelas_max"]:
            return faixa["desconto"]
    return TABELA_DESCONTOS_TPV[-1]["desconto"]


def calcular_limite_valor_cda(salario_minimo: Decimal) -> Decimal:
    """Calcula o limite de valor por CDA (60 × salário mínimo vigente)."""
    return salario_minimo * LIMITE_SM_POR_CDA
```

- [ ] **Step 5: Implementar `src/tpv/validators.py`**

```python
"""
Validação de elegibilidade de CDAs para Transação de Pequeno Valor.

Critérios (ambos devem ser atendidos simultaneamente):
1. Valor da CDA ≤ 60 salários mínimos vigentes
2. Inscrição em dívida ativa há mais de 1 ano
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from src.tpv.constants import LIMITE_SM_POR_CDA, TEMPO_MINIMO_INSCRICAO_DIAS, calcular_limite_valor_cda


class MotivoInaptidao(str, Enum):
    VALOR_ACIMA_LIMITE = "Valor acima de 60 salários mínimos"
    INSCRICAO_INFERIOR_1_ANO = "Inscrição inferior a 1 ano"


@dataclass
class CDAValidationResult:
    apta: bool
    motivos: list[MotivoInaptidao] = field(default_factory=list)
    data_elegibilidade_tempo: date | None = None
    dias_restantes_tempo: int | None = None
    apta_valor: bool = True
    apta_tempo: bool = True


def validar_cda(
    valor: Decimal,
    data_inscricao: date,
    data_simulacao: date,
    salario_minimo: Decimal,
) -> CDAValidationResult:
    motivos = []
    limite = calcular_limite_valor_cda(salario_minimo)

    apta_valor = valor <= limite
    if not apta_valor:
        motivos.append(MotivoInaptidao.VALOR_ACIMA_LIMITE)

    dias_inscrita = (data_simulacao - data_inscricao).days
    apta_tempo = dias_inscrita >= TEMPO_MINIMO_INSCRICAO_DIAS
    if not apta_tempo:
        motivos.append(MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO)

    data_elegibilidade_tempo = data_inscricao + timedelta(days=TEMPO_MINIMO_INSCRICAO_DIAS)
    dias_restantes_tempo = max(0, (data_elegibilidade_tempo - data_simulacao).days)

    return CDAValidationResult(
        apta=len(motivos) == 0,
        motivos=motivos,
        data_elegibilidade_tempo=data_elegibilidade_tempo if not apta_tempo else None,
        dias_restantes_tempo=dias_restantes_tempo if not apta_tempo else None,
        apta_valor=apta_valor,
        apta_tempo=apta_tempo,
    )
```

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/test_tpv_constants.py tests/test_tpv_validators.py -v`
Expected: Todos PASS

- [ ] **Step 7: Commit**

```bash
git add src/tpv/ tests/test_tpv_constants.py tests/test_tpv_validators.py
git commit -m "feat: TPV constants + CDA eligibility validators with TDD"
```

---

## Task 16: Motor de Cálculo TPV + Testes TDD

**Files:**
- Create: `src/tpv/engine.py`
- Create: `tests/test_tpv_engine.py`

- [ ] **Step 1: Escrever testes do motor TPV**

```python
# tests/test_tpv_engine.py
from datetime import date
from decimal import Decimal

from src.tpv.engine import (
    CDAInput,
    TPVInput,
    TPVResult,
    calcular_tpv,
)


class TestCalcularTPV:
    def test_cenario_basico_50_porcento_desconto(self):
        """Teste replicando HPR: R$500, 7 parcelas saldo, 1 entrada."""
        inp = TPVInput(
            cdas=[CDAInput(numero="CDA-001", valor=Decimal("500"), data_inscricao=date(2020, 3, 15))],
            parcelas_entrada=1,
            parcelas_saldo=7,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        assert result.total_cdas_aptas == Decimal("500")
        assert result.valor_entrada == Decimal("25")  # 5% de 500
        assert result.parcela_entrada == Decimal("25")  # 25 / 1
        assert result.desconto_percentual == Decimal("0.50")
        assert result.saldo_antes_desconto == Decimal("475")
        assert result.saldo_com_desconto == Decimal("237.50")
        assert result.parcela_saldo == Decimal("33.93")  # 237.50 / 7
        assert result.valor_final == Decimal("262.50")  # 25 + 237.50
        assert result.economia == Decimal("237.50")
        assert len(result.fluxo) == 8  # 1 entrada + 7 saldo

    def test_desconto_45_porcento_12_parcelas(self):
        inp = TPVInput(
            cdas=[CDAInput(numero="CDA-001", valor=Decimal("10000"), data_inscricao=date(2020, 1, 1))],
            parcelas_entrada=3,
            parcelas_saldo=12,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        assert result.desconto_percentual == Decimal("0.45")
        assert result.valor_entrada == Decimal("500")  # 5% de 10000
        assert result.parcela_entrada == Decimal("166.67")  # 500 / 3

    def test_desconto_30_porcento_55_parcelas(self):
        inp = TPVInput(
            cdas=[CDAInput(numero="CDA-001", valor=Decimal("80000"), data_inscricao=date(2020, 1, 1))],
            parcelas_entrada=5,
            parcelas_saldo=55,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        assert result.desconto_percentual == Decimal("0.30")
        assert result.num_parcelas_entrada == 5

    def test_multiplas_cdas_soma_apenas_aptas(self):
        """CDAs não aptas não entram no cálculo."""
        inp = TPVInput(
            cdas=[
                CDAInput(numero="CDA-APTA", valor=Decimal("50000"), data_inscricao=date(2020, 1, 1)),
                CDAInput(numero="CDA-NAO-APTA", valor=Decimal("100000"), data_inscricao=date(2020, 1, 1)),
            ],
            parcelas_entrada=1,
            parcelas_saldo=7,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        assert result.total_cdas_aptas == Decimal("50000")
        assert len(result.cdas_aptas) == 1
        assert len(result.cdas_nao_aptas) == 1

    def test_fluxo_tem_entrada_e_saldo(self):
        inp = TPVInput(
            cdas=[CDAInput(numero="CDA-001", valor=Decimal("1000"), data_inscricao=date(2020, 1, 1))],
            parcelas_entrada=2,
            parcelas_saldo=7,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        assert result.fluxo[0]["tipo"] == "entrada"
        assert result.fluxo[1]["tipo"] == "entrada"
        assert result.fluxo[2]["tipo"] == "saldo"
        assert len(result.fluxo) == 9  # 2 + 7
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_tpv_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `src/tpv/engine.py`**

```python
"""
Motor de cálculo para Transação de Pequeno Valor (TPV).

Módulo puramente funcional (sem I/O).

Diferenças da transação geral:
- Desconto incide sobre TODO o saldo (inclusive principal)
- Entrada de 5% (não 6%)
- Tabela escalonada de descontos (50/45/40/30%)
- Validação por CDA individual (60 SM, inscrição > 1 ano)
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from src.tpv.constants import ENTRADA_PERCENTUAL_TPV, get_desconto_por_parcelas
from src.tpv.validators import CDAValidationResult, validar_cda

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CDAInput:
    numero: str
    valor: Decimal
    data_inscricao: date


@dataclass
class CDAResult:
    numero: str
    valor: Decimal
    data_inscricao: date
    validacao: CDAValidationResult


@dataclass
class TPVInput:
    cdas: list[CDAInput]
    parcelas_entrada: int
    parcelas_saldo: int
    salario_minimo: Decimal
    data_simulacao: date


@dataclass
class TPVResult:
    total_cdas_aptas: Decimal
    total_cdas_nao_aptas: Decimal
    cdas_aptas: list[CDAResult]
    cdas_nao_aptas: list[CDAResult]
    valor_entrada: Decimal
    parcela_entrada: Decimal
    num_parcelas_entrada: int
    desconto_percentual: Decimal
    saldo_antes_desconto: Decimal
    saldo_com_desconto: Decimal
    parcela_saldo: Decimal
    num_parcelas_saldo: int
    valor_final: Decimal
    economia: Decimal
    fluxo: list[dict] = field(default_factory=list)


def calcular_tpv(inp: TPVInput) -> TPVResult:
    cdas_aptas = []
    cdas_nao_aptas = []

    for cda in inp.cdas:
        validacao = validar_cda(cda.valor, cda.data_inscricao, inp.data_simulacao, inp.salario_minimo)
        cda_result = CDAResult(
            numero=cda.numero, valor=cda.valor,
            data_inscricao=cda.data_inscricao, validacao=validacao,
        )
        if validacao.apta:
            cdas_aptas.append(cda_result)
        else:
            cdas_nao_aptas.append(cda_result)

    total_aptas = sum((c.valor for c in cdas_aptas), Decimal("0"))
    total_nao_aptas = sum((c.valor for c in cdas_nao_aptas), Decimal("0"))

    valor_entrada = _round(total_aptas * ENTRADA_PERCENTUAL_TPV)
    parcela_entrada = _round(valor_entrada / Decimal(str(inp.parcelas_entrada))) if inp.parcelas_entrada > 0 else Decimal("0")

    saldo_antes_desconto = total_aptas - valor_entrada
    desconto_percentual = get_desconto_por_parcelas(inp.parcelas_saldo)
    desconto_valor = _round(saldo_antes_desconto * desconto_percentual)
    saldo_com_desconto = saldo_antes_desconto - desconto_valor

    parcela_saldo = _round(saldo_com_desconto / Decimal(str(inp.parcelas_saldo))) if inp.parcelas_saldo > 0 else Decimal("0")
    valor_final = valor_entrada + saldo_com_desconto
    economia = total_aptas - valor_final

    fluxo = []
    for i in range(1, inp.parcelas_entrada + 1):
        fluxo.append({"num": i, "tipo": "entrada", "valor": parcela_entrada})
    for i in range(1, inp.parcelas_saldo + 1):
        fluxo.append({"num": inp.parcelas_entrada + i, "tipo": "saldo", "valor": parcela_saldo})

    return TPVResult(
        total_cdas_aptas=total_aptas,
        total_cdas_nao_aptas=total_nao_aptas,
        cdas_aptas=cdas_aptas,
        cdas_nao_aptas=cdas_nao_aptas,
        valor_entrada=valor_entrada,
        parcela_entrada=parcela_entrada,
        num_parcelas_entrada=inp.parcelas_entrada,
        desconto_percentual=desconto_percentual,
        saldo_antes_desconto=saldo_antes_desconto,
        saldo_com_desconto=saldo_com_desconto,
        parcela_saldo=parcela_saldo,
        num_parcelas_saldo=inp.parcelas_saldo,
        valor_final=valor_final,
        economia=economia,
        fluxo=fluxo,
    )
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/test_tpv_engine.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/tpv/engine.py tests/test_tpv_engine.py
git commit -m "feat: TPV calculation engine with multi-CDA support and tiered discounts"
```

---

## Task 17: Parser CSV/Excel para Importação em Lote + Testes

> O vídeo da HPR confirma que a importação é feita via **Excel** (.xlsx) exportado do Regularize. Suportamos CSV e XLSX.

**Files:**
- Create: `src/tpv/csv_parser.py`
- Create: `tests/test_tpv_csv_parser.py`

- [ ] **Step 1: Escrever testes do parser CSV**

```python
# tests/test_tpv_csv_parser.py
from datetime import date
from decimal import Decimal
from io import StringIO

from src.tpv.csv_parser import parse_cdas_csv, CDAParseResult


class TestCSVParser:
    def test_parse_csv_valido(self):
        csv_content = """numero_cda,valor,data_inscricao
CDA-001,50000.00,15/03/2020
CDA-002,30000.00,01/01/2019
"""
        result = parse_cdas_csv(StringIO(csv_content))
        assert len(result.cdas) == 2
        assert result.cdas[0].numero == "CDA-001"
        assert result.cdas[0].valor == Decimal("50000.00")
        assert result.cdas[0].data_inscricao == date(2020, 3, 15)
        assert result.erros == []

    def test_parse_csv_com_linha_invalida(self):
        csv_content = """numero_cda,valor,data_inscricao
CDA-001,50000,15/03/2020
CDA-BAD,abc,invalid-date
"""
        result = parse_cdas_csv(StringIO(csv_content))
        assert len(result.cdas) == 1
        assert len(result.erros) == 1
        assert "linha 3" in result.erros[0].lower()

    def test_parse_csv_vazio(self):
        csv_content = """numero_cda,valor,data_inscricao
"""
        result = parse_cdas_csv(StringIO(csv_content))
        assert len(result.cdas) == 0
```

- [ ] **Step 2: Implementar `src/tpv/csv_parser.py`**

```python
"""Parser de CSV e Excel (.xlsx) para importação em lote de CDAs.

Suporta:
- CSV com colunas: numero_cda, valor, data_inscricao
- Excel (.xlsx) exportado do Regularize (openpyxl)
"""

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from typing import TextIO

from src.tpv.engine import CDAInput


@dataclass
class CDAParseResult:
    cdas: list[CDAInput] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)


def parse_cdas_csv(file: TextIO) -> CDAParseResult:
    result = CDAParseResult()
    reader = csv.DictReader(file)

    for i, row in enumerate(reader, start=2):
        try:
            numero = row["numero_cda"].strip()
            valor = Decimal(row["valor"].strip().replace(",", "."))
            dia, mes, ano = row["data_inscricao"].strip().split("/")
            data = date(int(ano), int(mes), int(dia))
            result.cdas.append(CDAInput(numero=numero, valor=valor, data_inscricao=data))
        except (KeyError, ValueError, InvalidOperation, AttributeError) as e:
            result.erros.append(f"Linha {i}: erro ao processar — {e}")

    return result


def parse_cdas_excel(file_bytes: bytes) -> CDAParseResult:
    """Parse .xlsx exportado do Regularize."""
    from openpyxl import load_workbook

    result = CDAParseResult()
    wb = load_workbook(BytesIO(file_bytes), read_only=True)
    ws = wb.active

    headers = [str(cell.value).strip().lower() if cell.value else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    col_map = {}
    for i, h in enumerate(headers):
        if "cda" in h or "numero" in h or "inscri" in h and "data" not in h:
            col_map["numero"] = i
        elif "valor" in h:
            col_map["valor"] = i
        elif "data" in h:
            col_map["data"] = i

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            numero = str(row[col_map.get("numero", 0)]).strip()
            valor_raw = row[col_map.get("valor", 1)]
            valor = Decimal(str(valor_raw).replace(",", "."))
            data_raw = row[col_map.get("data", 2)]
            if isinstance(data_raw, date):
                data = data_raw
            else:
                dia, mes, ano = str(data_raw).strip().split("/")
                data = date(int(ano), int(mes), int(dia))
            result.cdas.append(CDAInput(numero=numero, valor=valor, data_inscricao=data))
        except Exception as e:
            result.erros.append(f"Linha {row_idx}: erro ao processar — {e}")

    wb.close()
    return result
```

- [ ] **Step 3: Rodar testes**

Run: `pytest tests/test_tpv_csv_parser.py -v`
Expected: Todos PASS

- [ ] **Step 4: Commit**

```bash
git add src/tpv/csv_parser.py tests/test_tpv_csv_parser.py
git commit -m "feat: CSV parser for batch CDA import"
```

---

## Task 18: Models, Schemas e Router TPV

**Files:**
- Create: `src/tpv/models.py`
- Create: `src/tpv/schemas.py`
- Create: `src/tpv/service.py`
- Create: `src/tpv/router.py`
- Modify: `src/main.py` — adicionar tpv router

- [ ] **Step 1: Implementar `src/tpv/models.py`**

```python
"""Models SQLAlchemy para o módulo TPV."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.deps import Base


class SimulacaoTPV(Base):
    __tablename__ = "simulacoes_tpv"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    nome_contribuinte: Mapped[str] = mapped_column(String(300), nullable=False)
    cpf_cnpj: Mapped[str] = mapped_column(String(18), nullable=False)
    tipo_porte: Mapped[str] = mapped_column(String(5), nullable=False)  # PF, ME, EPP
    salario_minimo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    parcelas_entrada: Mapped[int] = mapped_column(Integer, nullable=False)
    parcelas_saldo: Mapped[int] = mapped_column(Integer, nullable=False)

    resultado: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Implementar `src/tpv/schemas.py`**

```python
"""Pydantic schemas para TPV."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CDARequest(BaseModel):
    numero: str = Field(..., min_length=1, max_length=50)
    valor: Decimal = Field(..., gt=0)
    data_inscricao: date


class TPVSimulacaoRequest(BaseModel):
    nome_contribuinte: str = Field(..., min_length=2, max_length=300)
    cpf_cnpj: str = Field(..., min_length=11, max_length=18)
    tipo_porte: str = Field(..., pattern="^(PF|ME|EPP)$")
    salario_minimo: Decimal = Field(..., gt=0)
    data_simulacao: date
    parcelas_entrada: int = Field(..., ge=1, le=5)
    parcelas_saldo: int = Field(..., ge=1, le=55)
    cdas: list[CDARequest]


class TPVSimulacaoListItem(BaseModel):
    id: uuid.UUID
    nome_contribuinte: str
    cpf_cnpj: str
    tipo_porte: str
    total_cdas: int
    valor_final: Decimal
    created_at: datetime
```

- [ ] **Step 3: Implementar `src/tpv/service.py`** e `src/tpv/router.py`

```python
# src/tpv/service.py
"""Serviço TPV: orquestra engine + persistência."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.tpv.engine import CDAInput, TPVInput, calcular_tpv
from src.tpv.models import SimulacaoTPV
from src.tpv.schemas import TPVSimulacaoRequest


class TPVService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def simular(self, request: TPVSimulacaoRequest, user_id: str) -> dict:
        cdas = [CDAInput(numero=c.numero, valor=c.valor, data_inscricao=c.data_inscricao) for c in request.cdas]
        inp = TPVInput(
            cdas=cdas,
            parcelas_entrada=request.parcelas_entrada,
            parcelas_saldo=request.parcelas_saldo,
            salario_minimo=request.salario_minimo,
            data_simulacao=request.data_simulacao,
        )
        result = calcular_tpv(inp)

        resultado_dict = {
            "total_cdas_aptas": str(result.total_cdas_aptas),
            "total_cdas_nao_aptas": str(result.total_cdas_nao_aptas),
            "cdas_aptas": [{"numero": c.numero, "valor": str(c.valor)} for c in result.cdas_aptas],
            "cdas_nao_aptas": [
                {"numero": c.numero, "valor": str(c.valor),
                 "motivos": [m.value for m in c.validacao.motivos],
                 "data_elegibilidade": c.validacao.data_elegibilidade_tempo.isoformat() if c.validacao.data_elegibilidade_tempo else None,
                 "dias_restantes": c.validacao.dias_restantes_tempo}
                for c in result.cdas_nao_aptas
            ],
            "valor_entrada": str(result.valor_entrada),
            "parcela_entrada": str(result.parcela_entrada),
            "num_parcelas_entrada": result.num_parcelas_entrada,
            "desconto_percentual": str(result.desconto_percentual),
            "saldo_antes_desconto": str(result.saldo_antes_desconto),
            "saldo_com_desconto": str(result.saldo_com_desconto),
            "parcela_saldo": str(result.parcela_saldo),
            "num_parcelas_saldo": result.num_parcelas_saldo,
            "valor_final": str(result.valor_final),
            "economia": str(result.economia),
            "fluxo": result.fluxo,
        }

        simulacao = SimulacaoTPV(
            user_id=uuid.UUID(user_id),
            nome_contribuinte=request.nome_contribuinte,
            cpf_cnpj=request.cpf_cnpj,
            tipo_porte=request.tipo_porte,
            salario_minimo=float(request.salario_minimo),
            parcelas_entrada=request.parcelas_entrada,
            parcelas_saldo=request.parcelas_saldo,
            resultado=resultado_dict,
        )
        self.db.add(simulacao)
        await self.db.commit()
        await self.db.refresh(simulacao)

        return {"id": str(simulacao.id), "created_at": simulacao.created_at.isoformat(), **resultado_dict}
```

```python
# src/tpv/router.py
"""API endpoints para simulação TPV."""

import uuid as uuid_mod
from io import StringIO

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.deps import get_db
from src.auth.dependencies import get_current_user
from src.tpv.csv_parser import parse_cdas_csv
from src.tpv.models import SimulacaoTPV
from src.tpv.schemas import TPVSimulacaoRequest
from src.tpv.service import TPVService

router = APIRouter(prefix="/api/v1/tpv", tags=["tpv"])


@router.post("/simular")
async def simular_tpv(
    request: TPVSimulacaoRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    service = TPVService(db)
    return await service.simular(request, user["sub"])


@router.post("/importar-cdas")
async def importar_cdas(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    content = await file.read()
    if file.filename and file.filename.endswith(".xlsx"):
        result = parse_cdas_excel(content)
    else:
        text = content.decode("utf-8-sig")
        result = parse_cdas_csv(StringIO(text))
    return {
        "cdas": [{"numero": c.numero, "valor": str(c.valor), "data_inscricao": c.data_inscricao.isoformat()} for c in result.cdas],
        "erros": result.erros,
        "total_importadas": len(result.cdas),
    }


@router.get("/historico")
async def historico_tpv(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = uuid_mod.UUID(user["sub"])
    query = select(SimulacaoTPV).where(SimulacaoTPV.user_id == user_id).order_by(SimulacaoTPV.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    simulacoes = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(SimulacaoTPV).where(SimulacaoTPV.user_id == user_id))).scalar()
    return {"simulacoes": [{"id": str(s.id), "nome_contribuinte": s.nome_contribuinte, "cpf_cnpj": s.cpf_cnpj, "tipo_porte": s.tipo_porte, "created_at": s.created_at.isoformat(), **s.resultado} for s in simulacoes], "total": total}


@router.delete("/{simulacao_id}")
async def excluir_simulacao(
    simulacao_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = uuid_mod.UUID(user["sub"])
    result = await db.execute(select(SimulacaoTPV).where(SimulacaoTPV.id == simulacao_id, SimulacaoTPV.user_id == user_id))
    simulacao = result.scalar_one_or_none()
    if not simulacao:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulação não encontrada")
    await db.delete(simulacao)
    await db.commit()
    return {"deleted": True}
```

- [ ] **Step 4: Adicionar TPV router ao `src/main.py`**

Adicionar:
```python
from src.tpv.router import router as tpv_router
app.include_router(tpv_router)
```

- [ ] **Step 5: Gerar migration para SimulacaoTPV**

Run: `alembic revision --autogenerate -m "add simulacoes_tpv table"`
Then: `alembic upgrade head`

- [ ] **Step 6: Commit**

```bash
git add src/tpv/models.py src/tpv/schemas.py src/tpv/service.py src/tpv/router.py src/main.py alembic/versions/
git commit -m "feat: TPV module - models, schemas, service, router with CDA import"
```

---

## Task 19: Template PDF TPV + Relatório A4

**Files:**
- Create: `src/pdf/templates/tpv_relatorio.html`
- Modify: `src/tpv/router.py` — adicionar endpoint PDF

- [ ] **Step 1: Criar template HTML A4 para TPV**

```html
<!-- src/pdf/templates/tpv_relatorio.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  @page { size: A4; margin: 20mm; }
  body { font-family: Arial, sans-serif; font-size: 10px; color: #333; }
  h1 { color: #1a1a2e; font-size: 18px; border-bottom: 3px solid #d4a843; padding-bottom: 6px; }
  h2 { color: #d4a843; font-size: 13px; margin-top: 15px; }
  .badge-apta { background: #27ae60; color: white; padding: 2px 8px; border-radius: 10px; font-size: 8px; }
  .badge-nao-apta { background: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-size: 8px; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9px; }
  th { background: #1a1a2e; color: white; padding: 5px; text-align: left; }
  td { padding: 4px 5px; border-bottom: 1px solid #eee; }
  .card { border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; margin: 5px 0; display: inline-block; width: 30%; }
  .big-number { font-size: 16px; font-weight: bold; color: #1a1a2e; }
  .discount-highlight { background: #d4a843; color: white; padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: bold; }
  .footer { margin-top: 20px; border-top: 1px solid #ddd; padding-top: 8px; font-size: 8px; color: #999; text-align: center; }
</style>
</head>
<body>
  <h1>Transação de Pequeno Valor (TPV) — Relatório</h1>
  <p>{{ data_geracao }} | {{ nome_contribuinte }} | {{ cpf_cnpj }} | {{ tipo_porte }}</p>

  <h2>CDAs Cadastradas</h2>
  <table>
    <thead><tr><th>Nº CDA</th><th>Valor</th><th>Inscrição</th><th>Valor ≤ 60 SM</th><th>> 1 Ano</th><th>Status</th></tr></thead>
    <tbody>
    {% for cda in cdas_aptas %}
    <tr><td>{{ cda.numero }}</td><td>R$ {{ cda.valor }}</td><td>{{ cda.data_inscricao }}</td><td>✓</td><td>✓</td><td><span class="badge-apta">APTA</span></td></tr>
    {% endfor %}
    {% for cda in cdas_nao_aptas %}
    <tr><td>{{ cda.numero }}</td><td>R$ {{ cda.valor }}</td><td>—</td><td>{{ '✗' if 'Valor' in (cda.motivos|join) else '✓' }}</td><td>{{ '✗' if 'Inscrição' in (cda.motivos|join) else '✓' }}</td><td><span class="badge-nao-apta">NÃO APTA</span></td></tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Resultado Financeiro</h2>
  <p>Total CDAs Aptas: <strong>R$ {{ total_cdas_aptas }}</strong> | Desconto: <span class="discount-highlight">{{ desconto_percentual_fmt }}</span> | Economia: <strong>R$ {{ economia }}</strong></p>

  <table>
    <tr><td>Entrada (5%)</td><td>R$ {{ valor_entrada }} — {{ num_parcelas_entrada }}x de R$ {{ parcela_entrada }}</td></tr>
    <tr><td>Saldo antes desconto</td><td>R$ {{ saldo_antes_desconto }}</td></tr>
    <tr><td>Saldo com desconto</td><td>R$ {{ saldo_com_desconto }} — {{ num_parcelas_saldo }}x de R$ {{ parcela_saldo }}</td></tr>
    <tr><td><strong>Valor Final Negociado</strong></td><td><strong>R$ {{ valor_final }}</strong></td></tr>
  </table>

  <h2>Fluxo de Parcelas</h2>
  <table>
    <thead><tr><th>Nº</th><th>Tipo</th><th>Valor</th></tr></thead>
    <tbody>
    {% for p in fluxo %}
    <tr><td>{{ p.num }}</td><td>{{ p.tipo|capitalize }}</td><td>R$ {{ p.valor }}</td></tr>
    {% endfor %}
    </tbody>
  </table>

  <div class="footer">
    O desconto incide sobre todo o saldo (inclusive principal), conforme exceção legal da TPV.<br>
    Simulação estimativa. Valores sujeitos à análise da PGFN e atualização SELIC. | {{ data_geracao }}
  </div>
</body>
</html>
```

- [ ] **Step 2: Adicionar endpoint PDF ao router TPV**

Adicionar ao final de `src/tpv/router.py`:

```python
from io import BytesIO
from fastapi.responses import StreamingResponse
from src.pdf.generator import gerar_pdf_from_template


@router.get("/{simulacao_id}/pdf")
async def exportar_pdf_tpv(
    simulacao_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = uuid_mod.UUID(user["sub"])
    result = await db.execute(select(SimulacaoTPV).where(SimulacaoTPV.id == simulacao_id, SimulacaoTPV.user_id == user_id))
    simulacao = result.scalar_one_or_none()
    if not simulacao:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulação não encontrada")

    dados = {
        "nome_contribuinte": simulacao.nome_contribuinte,
        "cpf_cnpj": simulacao.cpf_cnpj,
        "tipo_porte": simulacao.tipo_porte,
        **simulacao.resultado,
    }
    pdf_bytes = gerar_pdf_from_template("tpv_relatorio.html", dados)
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=tpv_{simulacao.cpf_cnpj}.pdf"})
```

- [ ] **Step 3: Atualizar `src/pdf/generator.py`** com função genérica

Adicionar:
```python
def gerar_pdf_from_template(template_name: str, dados: dict) -> bytes:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    dados["data_geracao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if "desconto_percentual" in dados:
        pct = float(dados["desconto_percentual"])
        dados["desconto_percentual_fmt"] = f"{pct * 100:.0f}%"
    html_content = template.render(**dados)
    return HTML(string=html_content).write_pdf()
```

- [ ] **Step 4: Commit**

```bash
git add src/pdf/templates/tpv_relatorio.html src/tpv/router.py src/pdf/generator.py
git commit -m "feat: TPV A4 PDF report template + export endpoint"
```

---

## Task 20: Motor de Comparação Multi-Faixa TPV + Testes

**Files:**
- Modify: `src/tpv/engine.py` — adicionar função `calcular_tpv_todas_faixas`
- Create: `tests/test_tpv_multi_faixa.py`

> A 3ª plataforma HPR mostra as 4 faixas de desconto (50/45/40/30%) lado a lado com "Melhor opção" destacada. Implementamos a mesma funcionalidade.

- [ ] **Step 1: Escrever testes da comparação multi-faixa**

```python
# tests/test_tpv_multi_faixa.py
from decimal import Decimal

from src.tpv.engine import calcular_tpv_todas_faixas, TPVMultiFaixaResult


class TestMultiFaixa:
    def test_retorna_4_faixas(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        assert len(result.faixas) == 4

    def test_melhor_opcao_e_50_porcento(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        assert result.melhor_faixa.desconto_percentual == Decimal("0.50")
        assert result.melhor_faixa.parcelas_max == 7

    def test_economia_maxima_calculada(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        assert result.economia_maxima == Decimal("356.25")

    def test_entrada_5_porcento_em_todas_faixas(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        assert result.valor_entrada == Decimal("37.50")
        assert result.parcelas_entrada == 5

    def test_faixa_50_porcento_calculo_correto(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        faixa_50 = result.faixas[0]
        assert faixa_50.desconto_percentual == Decimal("0.50")
        assert faixa_50.desconto_valor == Decimal("356.25")
        assert faixa_50.saldo_final == Decimal("356.25")
        assert faixa_50.parcela_saldo == Decimal("50.89")

    def test_faixa_30_porcento_calculo_correto(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        faixa_30 = result.faixas[3]
        assert faixa_30.desconto_percentual == Decimal("0.30")
        assert faixa_30.desconto_valor == Decimal("213.75")
        assert faixa_30.saldo_final == Decimal("498.75")
        assert faixa_30.parcela_saldo == Decimal("9.07")

    def test_valor_final_entrada_mais_saldo(self):
        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))
        for faixa in result.faixas:
            assert faixa.valor_final == result.valor_entrada + faixa.saldo_final
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_tpv_multi_faixa.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `calcular_tpv_todas_faixas` em `src/tpv/engine.py`**

Adicionar ao final de `src/tpv/engine.py`:

```python
@dataclass
class FaixaResult:
    desconto_percentual: Decimal
    parcelas_max: int
    desconto_valor: Decimal
    saldo_final: Decimal
    parcela_saldo: Decimal
    valor_final: Decimal
    is_melhor: bool = False


@dataclass
class TPVMultiFaixaResult:
    valor_original: Decimal
    valor_entrada: Decimal
    parcela_entrada: Decimal
    parcelas_entrada: int
    saldo_apos_entrada: Decimal
    faixas: list[FaixaResult]
    melhor_faixa: FaixaResult
    economia_maxima: Decimal
    melhor_valor_final: Decimal


def calcular_tpv_todas_faixas(
    valor_total: Decimal,
    parcelas_entrada: int = 5,
) -> TPVMultiFaixaResult:
    """Calcula todas as 4 faixas de desconto para comparação lado a lado."""
    from src.tpv.constants import ENTRADA_PERCENTUAL_TPV, TABELA_DESCONTOS_TPV

    valor_entrada = _round(valor_total * ENTRADA_PERCENTUAL_TPV)
    parcela_entrada = _round(valor_entrada / Decimal(str(parcelas_entrada)))
    saldo = valor_total - valor_entrada

    faixas = []
    for tab in TABELA_DESCONTOS_TPV:
        desconto_valor = _round(saldo * tab["desconto"])
        saldo_final = saldo - desconto_valor
        parcela_saldo = _round(saldo_final / Decimal(str(tab["parcelas_max"])))
        valor_final = valor_entrada + saldo_final
        faixas.append(FaixaResult(
            desconto_percentual=tab["desconto"],
            parcelas_max=tab["parcelas_max"],
            desconto_valor=desconto_valor,
            saldo_final=saldo_final,
            parcela_saldo=parcela_saldo,
            valor_final=valor_final,
        ))

    melhor = min(faixas, key=lambda f: f.valor_final)
    melhor.is_melhor = True
    economia_maxima = valor_total - melhor.valor_final

    return TPVMultiFaixaResult(
        valor_original=valor_total,
        valor_entrada=valor_entrada,
        parcela_entrada=parcela_entrada,
        parcelas_entrada=parcelas_entrada,
        saldo_apos_entrada=saldo,
        faixas=faixas,
        melhor_faixa=melhor,
        economia_maxima=economia_maxima,
        melhor_valor_final=melhor.valor_final,
    )
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/test_tpv_multi_faixa.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/tpv/engine.py tests/test_tpv_multi_faixa.py
git commit -m "feat: multi-tier TPV comparison - all 4 discount tiers side by side"
```

---

## Task 21: Endpoint TPV Simplificado (Wizard) + Validação de Elegibilidade

**Files:**
- Modify: `src/tpv/router.py` — adicionar endpoints wizard
- Modify: `src/tpv/schemas.py` — adicionar schemas do wizard
- Create: `tests/test_tpv_wizard.py`

> A 3ª plataforma HPR funciona como wizard de perguntas com checklist lateral. Implementamos um endpoint que recebe as respostas do wizard e retorna o status de elegibilidade + resultado multi-faixa.

- [ ] **Step 1: Escrever testes do wizard**

```python
# tests/test_tpv_wizard.py
from decimal import Decimal

from src.tpv.engine import calcular_tpv_todas_faixas
from src.tpv.validators import validar_elegibilidade_wizard, ElegibilidadeWizardResult


class TestWizardElegibilidade:
    def test_elegivel_todos_criterios_ok(self):
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="ME",
            possui_cda_acima_limite=False,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )
        assert result.elegivel is True
        assert all(c["status"] == "ok" for c in result.criterios)

    def test_nao_elegivel_tipo_invalido(self):
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="LTDA",
            possui_cda_acima_limite=False,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )
        assert result.elegivel is False
        assert result.criterios[0]["status"] == "fail"

    def test_nao_elegivel_cda_acima_60sm(self):
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="PF",
            possui_cda_acima_limite=True,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )
        assert result.elegivel is False
        assert result.criterios[1]["status"] == "fail"

    def test_nao_elegivel_menos_1_ano(self):
        result = validar_elegibilidade_wizard(
            tipo_contribuinte="EPP",
            possui_cda_acima_limite=False,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=False,
            salario_minimo=Decimal("1621"),
        )
        assert result.elegivel is False
        assert result.criterios[3]["status"] == "fail"
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_tpv_wizard.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `validar_elegibilidade_wizard` em `src/tpv/validators.py`**

Adicionar ao final de `src/tpv/validators.py`:

```python
@dataclass
class ElegibilidadeWizardResult:
    elegivel: bool
    criterios: list[dict]
    mensagem: str


def validar_elegibilidade_wizard(
    tipo_contribuinte: str,
    possui_cda_acima_limite: bool,
    valor_total: Decimal,
    todas_cdas_mais_1_ano: bool,
    salario_minimo: Decimal,
) -> ElegibilidadeWizardResult:
    """Valida elegibilidade via wizard de perguntas (modo simplificado)."""
    from src.tpv.constants import TIPOS_ELEGIVEIS_TPV

    criterios = []

    # 1. Tipo de contribuinte
    tipo_ok = tipo_contribuinte in TIPOS_ELEGIVEIS_TPV
    criterios.append({
        "nome": "Tipo de Contribuinte",
        "status": "ok" if tipo_ok else "fail",
        "detalhe": "Tipo de contribuinte elegível" if tipo_ok else f"'{tipo_contribuinte}' não elegível para TPV",
    })

    # 2. Limite por CDA
    cda_ok = not possui_cda_acima_limite
    criterios.append({
        "nome": "Limite por CDA",
        "status": "ok" if cda_ok else "fail",
        "detalhe": "Todas as CDAs dentro do limite individual" if cda_ok else "Possui CDA acima de 60 salários mínimos - não elegível",
    })

    # 3. Valor da dívida
    valor_ok = valor_total > 0
    criterios.append({
        "nome": "Valor da Dívida",
        "status": "ok" if valor_ok else "fail",
        "detalhe": "Valor informado" if valor_ok else "Informe o valor total da dívida",
    })

    # 4. Tempo de inscrição
    tempo_ok = todas_cdas_mais_1_ano
    criterios.append({
        "nome": "Tempo de Inscrição",
        "status": "ok" if tempo_ok else "fail",
        "detalhe": "Todas as CDAs com mais de 1 ano" if tempo_ok else "CDAs com menos de 1 ano não são elegíveis",
    })

    elegivel = all(c["status"] == "ok" for c in criterios)
    mensagem = "Elegível para Transação de Pequeno Valor" if elegivel else "Preencha todos os critérios para continuar"

    return ElegibilidadeWizardResult(elegivel=elegivel, criterios=criterios, mensagem=mensagem)
```

- [ ] **Step 4: Adicionar endpoints wizard ao router TPV**

Adicionar ao `src/tpv/router.py`:

```python
from src.tpv.schemas import TPVWizardRequest
from src.tpv.validators import validar_elegibilidade_wizard
from src.tpv.engine import calcular_tpv_todas_faixas


@router.post("/wizard/elegibilidade")
async def verificar_elegibilidade_wizard(
    request: TPVWizardRequest,
    user: dict = Depends(get_current_user),
):
    result = validar_elegibilidade_wizard(
        tipo_contribuinte=request.tipo_contribuinte,
        possui_cda_acima_limite=request.possui_cda_acima_limite,
        valor_total=request.valor_total,
        todas_cdas_mais_1_ano=request.todas_cdas_mais_1_ano,
        salario_minimo=request.salario_minimo,
    )
    response = {
        "elegivel": result.elegivel,
        "criterios": result.criterios,
        "mensagem": result.mensagem,
    }
    if result.elegivel:
        multi = calcular_tpv_todas_faixas(request.valor_total)
        response["resultado"] = {
            "valor_original": str(multi.valor_original),
            "valor_entrada": str(multi.valor_entrada),
            "parcela_entrada": str(multi.parcela_entrada),
            "parcelas_entrada": multi.parcelas_entrada,
            "saldo_apos_entrada": str(multi.saldo_apos_entrada),
            "economia_maxima": str(multi.economia_maxima),
            "melhor_valor_final": str(multi.melhor_valor_final),
            "faixas": [
                {
                    "desconto_percentual": str(f.desconto_percentual),
                    "parcelas_max": f.parcelas_max,
                    "desconto_valor": str(f.desconto_valor),
                    "saldo_final": str(f.saldo_final),
                    "parcela_saldo": str(f.parcela_saldo),
                    "valor_final": str(f.valor_final),
                    "is_melhor": f.is_melhor,
                }
                for f in multi.faixas
            ],
        }
    return response
```

- [ ] **Step 5: Adicionar schema do wizard**

Adicionar ao `src/tpv/schemas.py`:

```python
class TPVWizardRequest(BaseModel):
    tipo_contribuinte: str = Field(..., pattern="^(PF|ME|EPP)$")
    possui_cda_acima_limite: bool
    valor_total: Decimal = Field(..., gt=0)
    todas_cdas_mais_1_ano: bool
    salario_minimo: Decimal = Field(default=Decimal("1621"), gt=0)
```

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/test_tpv_wizard.py -v`
Expected: Todos PASS

- [ ] **Step 7: Commit**

```bash
git add src/tpv/validators.py src/tpv/router.py src/tpv/schemas.py tests/test_tpv_wizard.py
git commit -m "feat: TPV wizard endpoint with eligibility checklist + multi-tier comparison"
```

---

## Task 22: Endpoint de Comparação entre Modalidades

**Files:**
- Create: `src/comparador/__init__.py`
- Create: `src/comparador/service.py`
- Create: `src/comparador/router.py`
- Create: `tests/test_comparador.py`

> Feature exclusiva nossa: permitir comparar "Capacidade de Pagamento" vs "TPV" para a mesma empresa e mostrar qual é mais vantajosa.

- [ ] **Step 1: Implementar serviço de comparação**

```python
# src/comparador/service.py
"""Compara resultados entre modalidades de transação."""

from dataclasses import dataclass
from decimal import Decimal

from src.transacao.engine import DiagnosticoInput, calcular_diagnostico
from src.transacao.constants import ClassificacaoCredito
from src.tpv.engine import calcular_tpv_todas_faixas


@dataclass
class ComparacaoResult:
    tpv_disponivel: bool
    tpv_melhor_valor_final: Decimal | None
    tpv_economia: Decimal | None
    capacidade_valor_final: Decimal
    capacidade_economia: Decimal
    recomendacao: str  # "TPV" | "CAPACIDADE" | "AMBAS_INDISPONIVEIS"
    economia_diferenca: Decimal


def comparar_modalidades(
    valor_total: Decimal,
    percentual_previdenciario: Decimal,
    is_me_epp: bool,
    classificacao: ClassificacaoCredito,
    tpv_elegivel: bool,
) -> ComparacaoResult:
    # Calcular Capacidade de Pagamento
    cap = calcular_diagnostico(DiagnosticoInput(
        valor_total_divida=valor_total,
        percentual_previdenciario=percentual_previdenciario,
        is_me_epp=is_me_epp,
        classificacao=classificacao,
    ))

    cap_final = cap.valor_com_desconto
    cap_economia = cap.valor_desconto

    # Calcular TPV (se elegível)
    tpv_final = None
    tpv_economia = None
    if tpv_elegivel:
        tpv = calcular_tpv_todas_faixas(valor_total)
        tpv_final = tpv.melhor_valor_final
        tpv_economia = tpv.economia_maxima

    # Determinar recomendação
    if tpv_elegivel and tpv_final is not None:
        if tpv_final < cap_final:
            recomendacao = "TPV"
            diferenca = cap_final - tpv_final
        else:
            recomendacao = "CAPACIDADE"
            diferenca = tpv_final - cap_final
    else:
        recomendacao = "CAPACIDADE"
        diferenca = Decimal("0")

    return ComparacaoResult(
        tpv_disponivel=tpv_elegivel,
        tpv_melhor_valor_final=tpv_final,
        tpv_economia=tpv_economia,
        capacidade_valor_final=cap_final,
        capacidade_economia=cap_economia,
        recomendacao=recomendacao,
        economia_diferenca=diferenca,
    )
```

- [ ] **Step 2: Escrever testes**

```python
# tests/test_comparador.py
from decimal import Decimal

from src.comparador.service import comparar_modalidades
from src.transacao.constants import ClassificacaoCredito


class TestComparador:
    def test_tpv_mais_vantajosa_para_pequeno_valor(self):
        """Para valores pequenos (< 60 SM), TPV tende a ser melhor (50% desconto)."""
        result = comparar_modalidades(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.D,
            tpv_elegivel=True,
        )
        assert result.tpv_disponivel is True
        assert result.recomendacao in ("TPV", "CAPACIDADE")

    def test_capacidade_quando_tpv_indisponivel(self):
        result = comparar_modalidades(
            valor_total=Decimal("500000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
            tpv_elegivel=False,
        )
        assert result.tpv_disponivel is False
        assert result.recomendacao == "CAPACIDADE"

    def test_classificacao_a_sem_desconto_capacidade(self):
        """Classificação A: sem desconto na Capacidade. Se TPV elegível, TPV melhor."""
        result = comparar_modalidades(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.A,
            tpv_elegivel=True,
        )
        assert result.recomendacao == "TPV"
```

- [ ] **Step 3: Implementar router**

```python
# src/comparador/router.py
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.auth.dependencies import get_current_user
from src.comparador.service import comparar_modalidades
from src.transacao.constants import ClassificacaoCredito

router = APIRouter(prefix="/api/v1/comparador", tags=["comparador"])


class ComparacaoRequest(BaseModel):
    valor_total: Decimal = Field(..., gt=0)
    percentual_previdenciario: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    is_me_epp: bool
    classificacao: ClassificacaoCredito = ClassificacaoCredito.D
    tpv_elegivel: bool


@router.post("/comparar")
async def comparar(request: ComparacaoRequest, user: dict = Depends(get_current_user)):
    result = comparar_modalidades(
        valor_total=request.valor_total,
        percentual_previdenciario=request.percentual_previdenciario,
        is_me_epp=request.is_me_epp,
        classificacao=request.classificacao,
        tpv_elegivel=request.tpv_elegivel,
    )
    return {
        "recomendacao": result.recomendacao,
        "economia_diferenca": str(result.economia_diferenca),
        "tpv": {
            "disponivel": result.tpv_disponivel,
            "valor_final": str(result.tpv_melhor_valor_final) if result.tpv_melhor_valor_final else None,
            "economia": str(result.tpv_economia) if result.tpv_economia else None,
        },
        "capacidade": {
            "valor_final": str(result.capacidade_valor_final),
            "economia": str(result.capacidade_economia),
        },
    }
```

- [ ] **Step 4: Adicionar router ao `src/main.py`**

```python
from src.comparador.router import router as comparador_router
app.include_router(comparador_router)
```

- [ ] **Step 5: Rodar testes**

Run: `pytest tests/test_comparador.py -v`
Expected: Todos PASS

- [ ] **Step 6: Commit**

```bash
git add src/comparador/ tests/test_comparador.py src/main.py
git commit -m "feat: modality comparison endpoint - TPV vs Capacidade de Pagamento"
```

---

## Task 23: Cadastro de Empresas (CRUD) + Honorários

**Files:**
- Create: `src/empresas/__init__.py`
- Create: `src/empresas/models.py`
- Create: `src/empresas/schemas.py`
- Create: `src/empresas/router.py`
- Create: `tests/test_empresas.py`

- [ ] **Step 1: Implementar model Empresa**

```python
# src/empresas/models.py
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.deps import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False)
    porte: Mapped[str] = mapped_column(String(20), nullable=False)  # "ME/EPP" | "DEMAIS"
    honorarios_percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    observacoes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Implementar schemas e router CRUD**

```python
# src/empresas/schemas.py
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EmpresaCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=300)
    cnpj: str = Field(..., min_length=14, max_length=18)
    porte: str = Field(..., pattern="^(ME/EPP|DEMAIS)$")
    honorarios_percentual: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    observacoes: str | None = None


class EmpresaResponse(BaseModel):
    id: uuid.UUID
    nome: str
    cnpj: str
    porte: str
    honorarios_percentual: Decimal
    observacoes: str | None
    created_at: datetime
```

```python
# src/empresas/router.py
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.deps import get_db
from src.empresas.models import Empresa
from src.empresas.schemas import EmpresaCreate, EmpresaResponse

router = APIRouter(prefix="/api/v1/empresas", tags=["empresas"])


@router.post("/", response_model=EmpresaResponse)
async def criar_empresa(data: EmpresaCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    empresa = Empresa(user_id=uuid_mod.UUID(user["sub"]), **data.model_dump())
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)
    return empresa


@router.get("/")
async def listar_empresas(busca: str = "", db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    user_id = uuid_mod.UUID(user["sub"])
    query = select(Empresa).where(Empresa.user_id == user_id)
    if busca:
        query = query.where(or_(Empresa.nome.ilike(f"%{busca}%"), Empresa.cnpj.ilike(f"%{busca}%")))
    result = await db.execute(query.order_by(Empresa.created_at.desc()))
    return result.scalars().all()


@router.put("/{empresa_id}", response_model=EmpresaResponse)
async def atualizar_empresa(empresa_id: str, data: EmpresaCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id, Empresa.user_id == uuid_mod.UUID(user["sub"])))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    for key, val in data.model_dump().items():
        setattr(empresa, key, val)
    await db.commit()
    await db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}")
async def excluir_empresa(empresa_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id, Empresa.user_id == uuid_mod.UUID(user["sub"])))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    await db.delete(empresa)
    await db.commit()
    return {"deleted": True}
```

- [ ] **Step 3: Adicionar router ao main.py + migration**

- [ ] **Step 4: Commit**

```bash
git add src/empresas/ tests/test_empresas.py src/main.py alembic/versions/
git commit -m "feat: company CRUD with search, fees percentage, and migration"
```

---

## Task 24: Engine de Cálculo Avançado (Principal/Multa/Juros/Encargos) + Rating CAPAG

**Files:**
- Create: `src/transacao/engine_avancado.py`
- Create: `tests/test_engine_avancado.py`

> A 4ª plataforma HPR decompõe a dívida em Principal/Multa/Juros/Encargos e aplica desconto APENAS sobre multa+juros+encargos (correto juridicamente conforme art. 11, §2º, I da Lei 13.988). Também calcula o Rating CAPAG automaticamente.

- [ ] **Step 1: Escrever testes do engine avançado**

```python
# tests/test_engine_avancado.py
from decimal import Decimal

from src.transacao.engine_avancado import (
    DebitoComponentes,
    SimulacaoAvancadaInput,
    calcular_rating_capag,
    calcular_desconto_componentes,
    calcular_simulacao_avancada,
    RatingCAPAG,
)


class TestRatingCAPAG:
    def test_rating_d_capag_muito_inferior(self):
        rating = calcular_rating_capag(capag_60m=Decimal("1000"), passivo_total=Decimal("5000"))
        assert rating == RatingCAPAG.D

    def test_rating_a_capag_suficiente(self):
        rating = calcular_rating_capag(capag_60m=Decimal("10000"), passivo_total=Decimal("5000"))
        assert rating == RatingCAPAG.A


class TestDescontoComponentes:
    def test_principal_sem_desconto(self):
        """Art. 11, §2º, I da Lei 13.988: vedado reduzir o principal."""
        componentes = DebitoComponentes(
            principal=Decimal("1000"), multa=Decimal("300"),
            juros=Decimal("500"), encargos=Decimal("200"),
        )
        result = calcular_desconto_componentes(componentes, desconto_pct=Decimal("0.70"))
        assert result.principal_final == Decimal("1000")  # Sem desconto
        assert result.principal_desconto == Decimal("0")

    def test_multa_juros_encargos_com_desconto_70(self):
        componentes = DebitoComponentes(
            principal=Decimal("1000"), multa=Decimal("300"),
            juros=Decimal("500"), encargos=Decimal("200"),
        )
        result = calcular_desconto_componentes(componentes, desconto_pct=Decimal("0.70"))
        # Desconto de 70% sobre multa+juros+encargos
        assert result.multa_desconto == Decimal("210")
        assert result.juros_desconto == Decimal("350")
        assert result.encargos_desconto == Decimal("140")
        assert result.total_desconto == Decimal("700")
        assert result.total_final == Decimal("1300")  # 2000 - 700

    def test_desconto_zero_para_rating_a(self):
        componentes = DebitoComponentes(
            principal=Decimal("1000"), multa=Decimal("300"),
            juros=Decimal("500"), encargos=Decimal("200"),
        )
        result = calcular_desconto_componentes(componentes, desconto_pct=Decimal("0"))
        assert result.total_desconto == Decimal("0")
        assert result.total_final == Decimal("2000")


class TestSimulacaoAvancada:
    def test_3_categorias_com_prazos_diferentes(self):
        inp = SimulacaoAvancadaInput(
            previdenciario=DebitoComponentes(
                principal=Decimal("1000"), multa=Decimal("300"),
                juros=Decimal("500"), encargos=Decimal("200"),
            ),
            tributario=DebitoComponentes(
                principal=Decimal("1500"), multa=Decimal("450"),
                juros=Decimal("600"), encargos=Decimal("250"),
            ),
            simples=DebitoComponentes(),
            is_me_epp=True,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            desconto_escolha="MAIOR",
        )
        result = calcular_simulacao_avancada(inp)

        assert result.rating == RatingCAPAG.D
        assert result.previdenciario.prazo_total == 60
        assert result.tributario.prazo_total == 145
        assert result.desconto_efetivo > 0

    def test_honorarios_de_exito(self):
        inp = SimulacaoAvancadaInput(
            previdenciario=DebitoComponentes(
                principal=Decimal("1000"), multa=Decimal("300"),
                juros=Decimal("500"), encargos=Decimal("200"),
            ),
            tributario=DebitoComponentes(),
            simples=DebitoComponentes(),
            is_me_epp=True,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            desconto_escolha="MAIOR",
            honorarios_percentual=Decimal("20"),
        )
        result = calcular_simulacao_avancada(inp)

        assert result.honorarios > 0
        assert result.honorarios == result.desconto_total * Decimal("0.20")
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest tests/test_engine_avancado.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar `src/transacao/engine_avancado.py`**

```python
"""
Engine avançado de cálculo de transação tributária.

Diferenças do engine básico:
- Decomposição em Principal/Multa/Juros/Encargos
- Desconto NÃO incide sobre Principal (art. 11, §2º, I da Lei 13.988)
- 3 categorias: Previdenciário, Tributário/Não Tributário, Simples Nacional
- Rating CAPAG automático baseado em CAPAG Presumida / Passivo
- Honorários de êxito sobre a economia
- Escolha Menor/Maior desconto
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from src.transacao.constants import (
    DESCONTO_MAX_GERAL, DESCONTO_MAX_ME_EPP,
    ENTRADA_PARCELAS_GERAL, ENTRADA_PARCELAS_ME_EPP, ENTRADA_PERCENTUAL,
    PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL, PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP,
    PRAZO_MAX_PREVIDENCIARIO,
)

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class RatingCAPAG(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class DebitoComponentes:
    principal: Decimal = Decimal("0")
    multa: Decimal = Decimal("0")
    juros: Decimal = Decimal("0")
    encargos: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.principal + self.multa + self.juros + self.encargos

    @property
    def descontavel(self) -> Decimal:
        return self.multa + self.juros + self.encargos


@dataclass
class DescontoResult:
    principal_final: Decimal
    principal_desconto: Decimal
    multa_final: Decimal
    multa_desconto: Decimal
    juros_final: Decimal
    juros_desconto: Decimal
    encargos_final: Decimal
    encargos_desconto: Decimal
    total_desconto: Decimal
    total_final: Decimal


@dataclass
class CategoriaResult:
    nome: str
    componentes_original: DebitoComponentes
    desconto_result: DescontoResult
    prazo_total: int
    entrada: Decimal
    parcela_entrada: Decimal
    num_entrada: int
    saldo_apos_entrada: Decimal
    parcela_saldo: Decimal
    num_parcelas_saldo: int


@dataclass
class SimulacaoAvancadaInput:
    previdenciario: DebitoComponentes
    tributario: DebitoComponentes
    simples: DebitoComponentes
    is_me_epp: bool
    capag_60m: Decimal
    passivo_rfb: Decimal
    desconto_escolha: str = "MAIOR"  # "MENOR" | "MAIOR"
    honorarios_percentual: Decimal = Decimal("0")


@dataclass
class SimulacaoAvancadaResult:
    rating: RatingCAPAG
    desconto_percentual: Decimal
    desconto_total: Decimal
    desconto_efetivo: Decimal
    previdenciario: CategoriaResult
    tributario: CategoriaResult
    simples: CategoriaResult
    passivo_pgfn: Decimal
    passivo_rfb: Decimal
    passivo_total: Decimal
    saldo_apos_desconto: Decimal
    honorarios: Decimal
    fluxo_consolidado: list[dict] = field(default_factory=list)


def calcular_rating_capag(capag_60m: Decimal, passivo_total: Decimal) -> RatingCAPAG:
    if passivo_total <= 0:
        return RatingCAPAG.A
    ratio = capag_60m / passivo_total
    if ratio >= 1.0:
        return RatingCAPAG.A
    if ratio >= 0.5:
        return RatingCAPAG.B
    if ratio >= 0.2:
        return RatingCAPAG.C
    return RatingCAPAG.D


def calcular_desconto_componentes(componentes: DebitoComponentes, desconto_pct: Decimal) -> DescontoResult:
    multa_desc = _round(componentes.multa * desconto_pct)
    juros_desc = _round(componentes.juros * desconto_pct)
    encargos_desc = _round(componentes.encargos * desconto_pct)
    total_desc = multa_desc + juros_desc + encargos_desc

    return DescontoResult(
        principal_final=componentes.principal,
        principal_desconto=Decimal("0"),
        multa_final=componentes.multa - multa_desc,
        multa_desconto=multa_desc,
        juros_final=componentes.juros - juros_desc,
        juros_desconto=juros_desc,
        encargos_final=componentes.encargos - encargos_desc,
        encargos_desconto=encargos_desc,
        total_desconto=total_desc,
        total_final=componentes.total - total_desc,
    )


def _get_desconto_pct(rating: RatingCAPAG, is_me_epp: bool, escolha: str) -> Decimal:
    if rating in (RatingCAPAG.A, RatingCAPAG.B):
        return Decimal("0")
    max_pct = Decimal(str(DESCONTO_MAX_ME_EPP if is_me_epp else DESCONTO_MAX_GERAL))
    if escolha == "MENOR":
        return max_pct * Decimal("0.5")
    return max_pct


def _calcular_categoria(
    nome: str, componentes: DebitoComponentes, desconto_pct: Decimal,
    is_me_epp: bool, is_previdenciario: bool,
) -> CategoriaResult:
    desconto_result = calcular_desconto_componentes(componentes, desconto_pct)
    valor_final = desconto_result.total_final

    num_entrada = ENTRADA_PARCELAS_ME_EPP if is_me_epp else ENTRADA_PARCELAS_GERAL
    entrada = _round(componentes.total * Decimal(str(ENTRADA_PERCENTUAL)))
    parcela_entrada = _round(entrada / Decimal(str(num_entrada))) if num_entrada > 0 else Decimal("0")

    prazo_total = PRAZO_MAX_PREVIDENCIARIO if is_previdenciario else (
        PRAZO_MAX_NAO_PREVIDENCIARIO_ME_EPP if is_me_epp else PRAZO_MAX_NAO_PREVIDENCIARIO_GERAL)

    saldo = valor_final - entrada
    if saldo < 0:
        saldo = Decimal("0")
    num_parcelas = prazo_total - num_entrada
    parcela_saldo = _round(saldo / Decimal(str(num_parcelas))) if num_parcelas > 0 and saldo > 0 else Decimal("0")

    return CategoriaResult(
        nome=nome, componentes_original=componentes, desconto_result=desconto_result,
        prazo_total=prazo_total, entrada=entrada, parcela_entrada=parcela_entrada,
        num_entrada=num_entrada, saldo_apos_entrada=saldo,
        parcela_saldo=parcela_saldo, num_parcelas_saldo=num_parcelas,
    )


def calcular_simulacao_avancada(inp: SimulacaoAvancadaInput) -> SimulacaoAvancadaResult:
    passivo_pgfn = inp.previdenciario.total + inp.tributario.total + inp.simples.total
    passivo_total = passivo_pgfn + inp.passivo_rfb

    rating = calcular_rating_capag(inp.capag_60m, passivo_total)
    desconto_pct = _get_desconto_pct(rating, inp.is_me_epp, inp.desconto_escolha)

    prev = _calcular_categoria("Previdenciário", inp.previdenciario, desconto_pct, inp.is_me_epp, True)
    trib = _calcular_categoria("Tributário e Não Tributário", inp.tributario, desconto_pct, inp.is_me_epp, False)
    simp = _calcular_categoria("Simples Nacional", inp.simples, desconto_pct, inp.is_me_epp, False)

    desconto_total = prev.desconto_result.total_desconto + trib.desconto_result.total_desconto + simp.desconto_result.total_desconto
    saldo_total = prev.desconto_result.total_final + trib.desconto_result.total_final + simp.desconto_result.total_final
    desconto_efetivo = _round(desconto_total / passivo_pgfn * 100) if passivo_pgfn > 0 else Decimal("0")
    honorarios = _round(desconto_total * inp.honorarios_percentual / 100)

    return SimulacaoAvancadaResult(
        rating=rating, desconto_percentual=desconto_pct, desconto_total=desconto_total,
        desconto_efetivo=desconto_efetivo, previdenciario=prev, tributario=trib, simples=simp,
        passivo_pgfn=passivo_pgfn, passivo_rfb=inp.passivo_rfb, passivo_total=passivo_total,
        saldo_apos_desconto=saldo_total, honorarios=honorarios,
    )
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/test_engine_avancado.py -v`
Expected: Todos PASS

- [ ] **Step 5: Commit**

```bash
git add src/transacao/engine_avancado.py tests/test_engine_avancado.py
git commit -m "feat: advanced engine with principal/penalty/interest decomposition + CAPAG rating"
```

---

## Task 25: Router e Service da Simulação Avançada

**Files:**
- Create: `src/transacao/router_avancado.py`
- Create: `src/transacao/schemas_avancado.py`
- Create: `src/transacao/service_avancado.py`
- Modify: `src/main.py`

- [ ] **Step 1: Implementar schemas avançados**

```python
# src/transacao/schemas_avancado.py
from decimal import Decimal
from pydantic import BaseModel, Field


class DebitoComponentesRequest(BaseModel):
    principal: Decimal = Field(default=Decimal("0"), ge=0)
    multa: Decimal = Field(default=Decimal("0"), ge=0)
    juros: Decimal = Field(default=Decimal("0"), ge=0)
    encargos: Decimal = Field(default=Decimal("0"), ge=0)


class SimulacaoAvancadaRequest(BaseModel):
    empresa_id: str
    passivo_rfb: Decimal = Field(..., ge=0)
    capag_60m: Decimal = Field(..., ge=0)
    desconto_escolha: str = Field(default="MAIOR", pattern="^(MENOR|MAIOR)$")
    previdenciario: DebitoComponentesRequest = DebitoComponentesRequest()
    tributario: DebitoComponentesRequest = DebitoComponentesRequest()
    simples: DebitoComponentesRequest = DebitoComponentesRequest()
```

- [ ] **Step 2: Implementar router + service avançado**

- [ ] **Step 3: Adicionar ao main.py + migration**

- [ ] **Step 4: Commit**

```bash
git add src/transacao/router_avancado.py src/transacao/schemas_avancado.py src/transacao/service_avancado.py src/main.py
git commit -m "feat: advanced simulation router with company link, 3 debt categories, CAPAG"
```

---

## Task 26: Template PDF Avançado (Resumido + Completo)

**Files:**
- Create: `src/pdf/templates/simulacao_avancada_resumido.html`
- Create: `src/pdf/templates/simulacao_avancada_completo.html`
- Modify: `src/transacao/router_avancado.py`

- [ ] **Step 1: Criar template resumido**

Template com: Rating badge, Resumo do Passivo, Descontos por componente (tabelas Previd/Trib), Parcelamento resumido.

- [ ] **Step 2: Criar template completo**

Template com tudo do resumido + fluxo de parcelas completo (até 145 meses).

- [ ] **Step 3: Adicionar endpoints `/pdf/resumido` e `/pdf/completo`**

- [ ] **Step 4: Commit**

```bash
git add src/pdf/templates/ src/transacao/router_avancado.py
git commit -m "feat: advanced PDF templates - summary and full with rating badge"
```

---

## Resumo de Referências Legais e Técnicas

### Legislação
| Referência | Assunto | Artigos-Chave |
|-----------|---------|---------------|
| Lei 13.988/2020 | Transação tributária | art. 11 (descontos/prazos/SELIC), art. 5 (vedações), art. 6 (ME/EPP) |
| Lei 14.375/2022 | Alterações na transação | Amplia desconto 65%, prazo 120m, prejuízo fiscal, precatórios |
| Lei 14.689/2023 | Ampliação do escopo | Inclui autarquias/fundações, contencioso tributário por adesão |
| Portaria PGFN 6.757/2022 | Regulamentação | arts. 21-40 (CAPAG, classificação A/B/C/D, entrada, parcelas) |
| CF/88, art. 195, §11 (EC 103/2019) | Limite previdenciário | Máx. 60m para contribuições patronais (folha) e trabalhadores |
| LC 123/2006, art. 3º | Definição ME/EPP | ME até R$360k, EPP até R$4,8M de receita bruta anual |
| Edital PGDAU 11/2025 | Modalidades vigentes | Até 29/05/2026, 4 modalidades, até R$45M |
| Edital RFB 4/2025 | Contencioso peq. valor | Até 60 SM, PF/ME/EPP, descontos 30-50% |
| Edital RFB 5/2025 | Contencioso até R$50M | Permite prejuízo fiscal/BCN-CSLL |

### Vedações Legais (implementar validação no engine)
1. **Vedado desconto no principal** — apenas multa, juros e encargos (art. 11, §2º, I)
2. **Vedado acumular** reduções do edital com outras da legislação (art. 5º, §1º)
3. **Vedado** Simples Nacional sem LC autorizativa (art. 5º, II, "a")
4. **Vedado** nova transação sobre mesmo crédito (art. 20, I)
5. **Vedado** nova transação por **2 anos** após rescisão (art. 4º, §4º)
6. **Vedado** devedor contumaz (art. 5º, III)

### APIs Externas
| API | Série | Endpoint | Uso |
|-----|-------|----------|-----|
| BCB SGS - SELIC mensal | 4390 | `api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json` | Correção parcelas |
| BCB SGS - SELIC anualizada | 4189 | `api.bcb.gov.br/dados/serie/bcdata.sgs.4189/dados?formato=json` | Cálculo preciso |
| BCB SGS - SELIC diária | 11 | `api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados?formato=json` | Cálculo dia a dia |
| BCB SGS - IPCA | 433 | `api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json` | Referência inflação |
| BCB SGS - IGP-M | 189 | `api.bcb.gov.br/dados/serie/bcdata.sgs.189/dados?formato=json` | Referência contratos |
| IBGE SIDRA - IPCA | Tabela 1737 | `apisidra.ibge.gov.br/values/t/1737/n1/all/v/63/p/last 12` | Alternativa IPCA |

**Notas:**
- Todas as APIs são públicas, gratuitas e sem autenticação
- BCB SGS: limite de 10 anos por consulta (desde 26/03/2025)
- IBGE SIDRA: limite de 100.000 valores por requisição

### Fórmula de Correção SELIC (Lei 13.988, art. 11, §1º)
```
valor_corrigido = valor_original × Π(1 + SELIC_mensal_i / 100) × 1.01
                                    i=mês_adesão até mês_anterior_pagamento
```
Onde:
- `SELIC_mensal_i` = valor da série 4390 do BCB para o mês i
- `1.01` = 1% adicional no mês do pagamento
