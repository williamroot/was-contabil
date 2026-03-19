# WAS Contabil

Plataforma web para diagnostico e simulacao de transacao tributaria federal (PGFN).

Desenvolvida para escritorios de contabilidade e advocacia tributaria que atuam na negociacao de dividas federais.

---

## O que faz

Simula cenarios de transacao tributaria com base na legislacao vigente (Lei 13.988/2020, Portaria PGFN 6.757/2022, Edital PGDAU 11/2025), gerando relatorios com total transparencia dos calculos e referencias legais em cada passo.

### Modulos

| Modulo | Descricao |
|--------|-----------|
| **Simulacao por Capacidade de Pagamento** | Decomposicao Principal/Multa/Juros/Encargos, rating CAPAG automatico (A/B/C/D), 3 categorias de debitos (Previdenciario, Tributario, Simples Nacional), honorarios de exito |
| **Simulador TPV Avancado** | Transacao de Pequeno Valor com validacao por CDA individual (limite 60 SM, inscricao > 1 ano), importacao CSV/Excel, dashboard de elegibilidade futura |
| **Diagnostico TPV Simplificado** | Wizard de perguntas com checklist de elegibilidade em tempo real e comparacao das 4 faixas de desconto (50/45/40/30%) lado a lado |
| **Comparador de Modalidades** | Compara TPV vs Capacidade de Pagamento e recomenda a opcao mais vantajosa |
| **Indices Economicos** | Busca SELIC e IPCA em tempo real via API do Banco Central (SGS) para correcao monetaria |
| **Cadastro de Empresas** | CRUD com busca, honorarios de exito, isolamento multi-tenant por organizacao |
| **Exportacao PDF** | Relatorios em A4 (resumido e completo) via WeasyPrint com rating, tabelas P/M/J/E e fluxo de parcelas |

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12, Django 5.2 LTS, Django REST Framework 3.16 |
| Banco de dados | PostgreSQL 17 |
| Cache/Queue | Redis 7, django-rq 4.0 |
| Autenticacao | django-allauth 65.x (OAuth Google + Microsoft) |
| Frontend MVP | Django templates, Tailwind CSS 3, HTMX 2, Alpine.js 3 |
| PDF | WeasyPrint 68.x, django-weasyprint 2.4 |
| Importacao | openpyxl 3.1 (Excel), csv (CSV) |
| Testes | pytest, pytest-django, factory-boy, coverage |
| Qualidade | Black, isort, flake8, pre-commit |
| Infra | Docker, docker-compose |

---

## Inicio rapido

### Pre-requisitos

- Docker e docker-compose
- Python 3.12+ (para desenvolvimento local)

### Subir com Docker

```bash
# Clonar o repositorio
git clone <repo-url> was-contabil
cd was-contabil

# Copiar variaveis de ambiente
cp .env.example .env

# Subir os servicos
docker compose up -d

# Rodar migrations
docker compose exec app python manage.py migrate

# Criar superuser
docker compose exec app python manage.py createsuperuser
```

### Desenvolvimento local

```bash
# Instalar dependencias
pip install -r requirements/dev.txt

# Subir PostgreSQL e Redis
docker compose up -d postgres redis

# Copiar e editar .env
cp .env.example .env

# Migrations
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py migrate

# Criar superuser e organizacao
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.core.models import Organization, Membership
User = get_user_model()
user = User.objects.create_superuser(username='admin', email='admin@test.com', password='admin123')
org = Organization.objects.create(name='Meu Escritorio', slug='meu-escritorio')
Membership.objects.create(user=user, organization=org, is_owner=True)
"

# Rodar servidor
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py runserver

# Acessar: http://localhost:8000
```

### Rodar testes

```bash
# Todos os testes
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest

# Com cobertura
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest --cov=apps --cov-report=term-missing

# Testes de compatibilidade HPR
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest tests/test_compatibilidade_hpr.py -v
```

### Formatacao e linting

```bash
# Formatar codigo
black .
isort .

# Verificar
flake8 apps/ config/

# Pre-commit (instalar uma vez)
pre-commit install
```

---

## Arquitetura

```
View (HTTP) --> Serializer (validacao) --> Service (orquestracao) --> Engine (calculo puro)
                                                |
                                          Model (persistencia)
```

| Camada | Responsabilidade | Regra |
|--------|-----------------|-------|
| **View** | Receber HTTP, delegar, responder | Fina — sem logica de negocio |
| **Serializer** | Validar input, serializar output | DRF serializers com validacao rigorosa |
| **Service** | Orquestrar engine + persistencia | Unico ponto de acesso a logica |
| **Engine** | Calculo puro, sem I/O, sem Django | Python puro, Decimal, dataclasses |
| **Model** | Schema do banco, managers | UUID PK, multi-tenant FK |
| **Constants** | Constantes legais com referencias | Cada valor com artigo/lei citado |

### Multi-tenant

Cada dado pertence a uma organizacao (escritorio). Isolamento via FK `organization_id` em todos os models de negocio, com middleware que seta `request.organization` automaticamente.

```
Superuser --> Convida dono do escritorio (email)
                --> Dono cria conta + Organizacao
                      --> Dono convida membros
                            --> Membro cria conta na mesma org
```

### Transparencia dos calculos

Cada resultado de simulacao inclui `calculo_detalhes` com passo a passo:

```json
{
  "passo": 1,
  "descricao": "Desconto de 70% sobre multa+juros+encargos",
  "formula": "Multa R$ 300,00 x 70% = R$ 210,00",
  "referencia_legal": "Lei 13.988/2020, art. 11, par.2, II + par.3 (ME/EPP)"
}
```

---

## Base legal

| Legislacao | Assunto |
|-----------|---------|
| Lei 13.988/2020 | Transacao tributaria federal |
| Lei 14.375/2022 | Ampliacao de descontos e prazos |
| Portaria PGFN 6.757/2022 | Regulamentacao CAPAG, classificacao A/B/C/D |
| CF/88, art. 195, par.11 | Limite 60 meses para previdenciario |
| LC 123/2006 | Definicao ME/EPP |
| Edital PGDAU 11/2025 | Modalidades vigentes ate 29/05/2026 |

### Regras implementadas

- Desconto maximo: 65% (geral) / 70% (ME/EPP/PF)
- **Principal NUNCA tem desconto** (art. 11, par.2, I)
- Prazo previdenciario: maximo 60 meses (limite constitucional)
- Prazo nao previdenciario: 120 meses (geral) / 145 meses (ME/EPP)
- Entrada: 6% em 6 parcelas (geral) / 12 parcelas (ME/EPP)
- TPV: entrada 5%, descontos 50/45/40/30% conforme parcelas, limite 60 SM por CDA
- Correcao SELIC: valor x produto(1 + SELIC_mensal/100) x 1.01
- Rating CAPAG: A (>= 2x), B (>= 1x), C (>= 0.5x), D (< 0.5x)

### Metodos de calculo do desconto

O usuario pode escolher entre dois metodos:

| Metodo | Descricao | Quando usar |
|--------|-----------|-------------|
| **CAPAG** (padrao) | Desconta 94% de M+J+E (preserva 6% entrada) | Compativel com HPR, maximiza desconto |
| **PERCENTUAL** | Aplica % fixo sobre cada componente | Mais conservador e transparente |

---

## APIs

A API REST esta preparada para integracao com frontend Vue.js ou qualquer outro framework.

### Endpoints principais

```
POST   /api/v1/transacao/simular/basico/       Simulacao diagnostico previo
POST   /api/v1/transacao/simular/avancado/      Simulacao CAPAG com P/M/J/E
GET    /api/v1/transacao/historico/              Historico de simulacoes
GET    /api/v1/transacao/<uuid>/                 Detalhe de simulacao

POST   /api/v1/tpv/simular/                     Simulacao TPV por CDA
POST   /api/v1/tpv/wizard/                      Wizard elegibilidade + 4 faixas
POST   /api/v1/tpv/importar/                    Importar CDAs (CSV/Excel)
GET    /api/v1/tpv/historico/                    Historico TPV

POST   /api/v1/comparador/comparar/             Comparar TPV vs Capacidade

GET    /api/v1/indices/selic/ultimos/            Ultimos N indices SELIC
GET    /api/v1/indices/selic/acumulada/          SELIC acumulada entre datas

GET    /api/v1/empresas/                         Listar empresas (com busca)
POST   /api/v1/empresas/                         Criar empresa
PUT    /api/v1/empresas/<uuid>/                  Atualizar empresa
DELETE /api/v1/empresas/<uuid>/                  Excluir empresa

GET    /pdf/diagnostico/<uuid>/                  PDF diagnostico
GET    /pdf/simulacao-avancada/<uuid>/           PDF avancado (?modo=resumido|completo)
GET    /pdf/tpv/<uuid>/                          PDF TPV
```

### Autenticacao

Autenticacao via sessao (SessionAuthentication). Login com email/senha ou OAuth (Google/Microsoft).

Rate limiting: 20 req/min (anonimo), 120 req/min (autenticado).

---

## Testes

```
532 testes | 99% cobertura | 5.9s
```

| Categoria | Testes | O que cobre |
|-----------|--------|-------------|
| Engine transacao | 143 | Calculo basico, avancado, CAPAG, edge cases |
| Engine TPV | 67 | Multi-CDA, faixas, wizard, validadores, edge cases |
| Serializers | 83 | Validacao input (CNPJ, ranges, tipos) |
| Views/API | 37 | Endpoints, multi-tenant, auth |
| Models | 36 | UUID, unique constraints, managers |
| PDF | 38 | Geracao, filtros, templates, views |
| Importadores | 20 | CSV, Excel, formato BR, ISO dates |
| Indices | 32 | Client BCB, service, sync, views |
| Comparador | 14 | Service, edge cases, serializers |
| Core | 23 | Org, membership, middleware, mixins, views |
| Compatibilidade HPR | 17 | Valores exatos das 4 plataformas HPR |
| Empresas | 25 | CRUD, multi-tenant, serializers, models |

### Testes de compatibilidade

Os testes em `tests/test_compatibilidade_hpr.py` reproduzem simulacoes feitas nas plataformas HPR reais (verificadas via browser em 17-18/03/2026) e garantem que nosso motor produz resultados identicos:

- Plataforma 1: Diagnostico previo (R$10k, 30% prev)
- Plataforma 2: TPV Simulator (CDA R$500, 50% desconto, 89 dias elegibilidade)
- Plataforma 3: PGFN Debt Solve (R$750, 4 faixas exatas)
- Plataforma 4: Meta Simulacao (CAPAG Sitio Verde, Rating D, P/M/J/E com 70%)

---

## Seguranca

- Sessao maxima 24 horas (SESSION_COOKIE_AGE=86400)
- Cookies: httponly, secure, samesite=Lax
- HSTS com preload (1 ano)
- CSRF ativo em todas as requisicoes
- Rate limiting (DRF throttling)
- Isolamento multi-tenant via FK + middleware
- UUIDs em todos os PKs (sem IDs sequenciais)
- Browsable API desabilitada em producao
- django-rq dashboard protegido com staff_member_required
- Password validators completos (4 validators)
- Validacao de empresa_id contra organizacao

---

## Estrutura do projeto

```
was_contabil/
  config/                    Settings Django (base/local/test/production)
  apps/
    core/                    Multi-tenant (Organization, Membership, Invitation)
    empresas/                Cadastro de empresas (CRUD + honorarios)
    transacao/               Simulacao Capacidade de Pagamento (basico + avancado)
    tpv/                     Transacao de Pequeno Valor (CDAs + wizard)
    indices/                 Indices economicos (SELIC/IPCA via BCB)
    comparador/              Comparacao entre modalidades
    pdf/                     Geracao PDF (WeasyPrint)
  templates/                 Django templates (Tailwind + HTMX)
  static/                    CSS e JS
  tests/                     Testes de compatibilidade HPR
  requirements/              Dependencias (base/dev/prod)
```

---

## Licenca

Software proprietario. Uso exclusivo autorizado.
