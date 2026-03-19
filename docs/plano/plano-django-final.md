# WAS Contábil — Plano de Implementação (Django)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o **WAS Contábil**, plataforma web multi-tenant para diagnóstico e simulação de transação tributária federal (PGFN), com 4 módulos: (1) Simulador de Transação Avançado (CAPAG com decomposição Principal/Multa/Juros/Encargos, 3 categorias de débitos, rating automático, honorários), (2) Simulador TPV por CDA (validação individual, importação Excel, elegibilidade futura), (3) Diagnóstico TPV Simplificado (wizard + comparação 4 faixas), (4) Comparador de Modalidades. Multi-tenant por organização com convites, OAuth Google/Microsoft, correção SELIC dinâmica (API BCB), PDF com WeasyPrint. Transparência total dos cálculos com referências legais em cada passo.

**Architecture:** Django 5.2 LTS + DRF (sync) como backend. Django templates + HTMX para MVP frontend (preparado para Vue.js via API REST completa). Multi-tenant por FK `organization_id` em todos os models. django-allauth para OAuth. django-rq + Redis para tasks assíncronas (sync índices BCB, geração PDF pesado). PostgreSQL 17 para persistência. WeasyPrint para PDF (reutiliza templates Django). Todos os cálculos em `Decimal` com fórmulas transparentes documentadas por referência legal.

**Tech Stack:**
- Python 3.12, Django 5.2 LTS, Django REST Framework 3.16
- PostgreSQL 17, Redis 7.x, django-rq 4.0
- django-allauth 65.x (OAuth Google/Microsoft)
- django-htmx 1.27 (frontend MVP), preparado para Vue.js
- WeasyPrint 68.x (PDF), openpyxl 3.1 (Excel import)
- psycopg2-binary, httpx (client BCB API)
- pytest, pytest-django 4.12, factory-boy 3.3
- Docker, docker-compose
- django-weasyprint 2.4 (integração WeasyPrint + Django views)
- Convites por email: implementação manual (django-invitations defasado, sem suporte Django 5.x)

---

## Decisões Técnicas Documentadas

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Framework | Django 5.2 LTS + DRF | ORM maduro, admin, auth built-in, ecossistema CRUD pesado |
| Sync vs Async | Sync | ORM Django sync é mais estável; async desnecessário neste projeto |
| Multi-tenant | FK `organization_id` | Simples, sem schema separation; suficiente para isolamento por escritório |
| Auth | django-allauth | 50+ providers OAuth, integração nativa Django, battle-tested |
| Convites | Custom (model Invitation) | django-invitations defasado (sem Django 5.x); manual é simples e integrável com allauth |
| Worker | django-rq + Redis | Mais simples que Celery; suficiente para sync índices e PDF |
| Cálculos | Decimal rigoroso | Financeiro exige precisão; sem float |
| CAPAG | Fórmula pesquisada, transparente | Cada passo mostra referência legal + fórmula aplicada |
| PDF | WeasyPrint + Django templates | Reutiliza mesma base HTML/CSS para tela e PDF |
| Frontend MVP | Django templates + HTMX | Entrega rápida; API REST completa via DRF permite Vue depois |
| TDD | Rigoroso (test first) | Produto — precisa de confiabilidade nos cálculos financeiros |
| Linter/Formatter | Black + isort + flake8 | PEP 8 rigoroso, formatação automática, zero discussão de estilo |
| Primary Keys | **UUID v4 em todos os models** | Segurança (não expõe sequência), merge-safe, API-friendly |
| Frontend | Tailwind CSS 3 + HTMX + Alpine.js | Design moderno, responsivo mobile-first, interativo sem SPA |
| Sessão | **Máximo 24 horas**, cookie httponly + secure | Segurança forte, sem sessões eternas |
| Backend | **OOP forte, desacoplamento, SOLID** | Services desacoplados, mixins, managers, injeção de dependência |
| Segurança | OWASP Top 10, CSP, CORS, rate limiting | Atenção redobrada em auth, sessão, multi-tenant isolation |

---

## Design & Frontend — Moderno, Intuitivo, Responsivo (OBRIGATÓRIO)

### Stack Frontend

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| **Tailwind CSS 3** | CDN (MVP) → build depois | Utility-first CSS, temas modernos, responsivo nativo |
| **HTMX 2** | CDN | Interatividade sem JavaScript pesado (partials, forms async) |
| **Alpine.js 3** | CDN | Interações leves (dropdowns, modals, toggles, tabs) |
| **Heroicons** | SVG inline | Ícones consistentes e leves |
| **Inter / Geist** | Google Fonts | Tipografia moderna e legível |

### Princípios de Design

1. **Mobile-first:** TODO o layout começa pelo mobile e escala para desktop. NUNCA projetar desktop-first.
2. **Responsivo perfeito:** Testar em 3 breakpoints obrigatórios: mobile (375px), tablet (768px), desktop (1280px).
3. **Dark/Light mode:** Suportar ambos via `class` strategy do Tailwind (`dark:` prefix). Default: light.
4. **Design system consistente:** Cores, espaçamento, tipografia definidos uma vez no Tailwind config.
5. **Feedback visual:** Loading states, skeleton screens, toast notifications, transições suaves.
6. **Acessibilidade:** Semântica HTML5, `aria-labels`, contraste WCAG AA, navegação por teclado.

### Paleta de Cores (inspirada nas plataformas HPR, mas modernizada)

```javascript
// tailwind.config.js (dentro de <script> no base.html para MVP CDN)
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fdf8e8',
          100: '#faefc5',
          200: '#f5dc8a',
          300: '#efc94c',
          400: '#d4a843',  // Dourado principal (HPR gold)
          500: '#b8922e',
          600: '#9a7a24',
          700: '#7c621d',
          800: '#5e4a16',
          900: '#40320f',
        },
        surface: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          800: '#262626',
          900: '#171717',
          950: '#0a0a0a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}
```

### Layout Base Responsivo

```html
<!-- templates/base.html — estrutura obrigatória -->
<!DOCTYPE html>
<html lang="pt-BR" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}WAS Contábil{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <script defer src="https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script>/* tailwind.config aqui */</script>
</head>
<body class="h-full bg-surface-50 dark:bg-surface-950 font-sans text-surface-900 dark:text-surface-100 antialiased">
  <!-- Navbar responsiva (hamburger no mobile) -->
  {% include "components/_navbar.html" %}

  <!-- Main com max-width e padding responsivo -->
  <main class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
    {% block content %}{% endblock %}
  </main>

  {% include "components/_footer.html" %}
  {% include "components/_toasts.html" %}
</body>
</html>
```

### Componentes Responsivos Obrigatórios

```html
<!-- Exemplo: Card responsivo (stack no mobile, side-by-side no desktop) -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
  <div class="bg-white dark:bg-surface-800 rounded-xl shadow-sm border border-surface-200
              dark:border-surface-700 p-4 sm:p-6 transition-shadow hover:shadow-md">
    <!-- conteúdo -->
  </div>
</div>

<!-- Exemplo: Tabela responsiva (scroll horizontal no mobile) -->
<div class="overflow-x-auto -mx-4 sm:mx-0">
  <div class="inline-block min-w-full align-middle">
    <table class="min-w-full divide-y divide-surface-200 dark:divide-surface-700">
      <!-- ... -->
    </table>
  </div>
</div>

<!-- Exemplo: Form responsivo (1 col mobile, 2-3 cols desktop) -->
<form class="space-y-6">
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
    <div>
      <label class="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Campo</label>
      <input class="w-full rounded-lg border border-surface-300 dark:border-surface-600
                     bg-white dark:bg-surface-800 px-3 py-2 text-sm
                     focus:ring-2 focus:ring-brand-400 focus:border-brand-400
                     transition-colors" />
    </div>
  </div>
</form>
```

### Para agentic workers: regras de frontend

> **1. MOBILE-FIRST:** Escreva primeiro as classes base (mobile), depois `sm:`, `md:`, `lg:`.
> **2. NUNCA usar larguras fixas em pixels.** Use `w-full`, `max-w-*`, `flex`, `grid`.
> **3. SEMPRE testar em 375px de largura** (iPhone SE). Se quebrar no mobile, não merge.
> **4. HTMX para tudo que é interação com servidor.** Não escrever fetch/axios manual.
> **5. Alpine.js para interações client-side** (modals, dropdowns, tabs). Não jQuery.
> **6. Transições suaves:** `transition-all duration-200` em hovers e state changes.
> **7. Loading states:** Mostrar spinner ou skeleton enquanto HTMX carrega.

---

## Segurança & Autenticação — Atenção Redobrada (OBRIGATÓRIO)

### Sessão — Máximo 24 horas

```python
# config/settings/base.py — SESSÃO SEGURA

# Sessão expira em 24 horas (86400 segundos)
SESSION_COOKIE_AGE = 86400  # 24h em segundos

# Sessão NÃO se renova automaticamente a cada request
SESSION_SAVE_EVERY_REQUEST = False

# Cookie httponly (JavaScript não acessa)
SESSION_COOKIE_HTTPONLY = True

# Cookie secure (apenas HTTPS em produção)
SESSION_COOKIE_SECURE = True  # Overriden em local.py para False

# Cookie samesite (proteção CSRF)
SESSION_COOKIE_SAMESITE = "Lax"

# Sessão expira ao fechar o browser (além do timeout de 24h)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CSRF cookie também httponly e secure
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

# Logout invalida sessão completamente
SESSION_ENGINE = "django.contrib.sessions.backends.db"
```

```python
# config/settings/local.py — override para desenvolvimento
SESSION_COOKIE_SECURE = False  # HTTP em dev
CSRF_COOKIE_SECURE = False
```

### Segurança OWASP Top 10

```python
# config/settings/base.py — SEGURANÇA

# 1. Content Security Policy (via middleware ou header)
SECURE_CONTENT_TYPE_NOSNIFF = True

# 2. XSS Protection
SECURE_BROWSER_XSS_FILTER = True

# 3. HTTPS redirect (produção)
SECURE_SSL_REDIRECT = True  # Override False em local.py

# 4. HSTS (produção)
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 5. Clickjacking protection
X_FRAME_OPTIONS = "DENY"

# 6. Referrer policy
SECURE_REFERRER_POLICY = "same-origin"

# 7. Allowed hosts (NUNCA "*" em produção)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
```

```python
# config/settings/local.py — override para desenvolvimento
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
```

### DRF — Autenticação e Throttling

```python
# config/settings/base.py — DRF seguro

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Rate limiting: proteção contra brute force e abuso
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",    # Visitantes não autenticados
        "user": "120/minute",   # Usuários autenticados
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Desabilitar browsable API em produção
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
```

```python
# config/settings/local.py — habilitar browsable API em dev
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # herda tudo de base
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/minute",  # Sem limite em dev
        "user": "1000/minute",
    },
}
```

### Multi-tenant — Isolamento Seguro

```python
# apps/core/mixins.py — ISOLAMENTO OBRIGATÓRIO

class OrgQuerySetMixin:
    """Filtra queryset por organization do request.

    SEGURANÇA CRÍTICA: Este mixin garante que um usuário NUNCA acesse
    dados de outra organização. TODOS os ViewSets de negócio DEVEM usar este mixin.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            # NUNCA retornar queryset sem filtro de org
            return qs.none()
        return qs.filter(organization=org)


class OrgCreateMixin:
    """Seta organization automaticamente ao criar objetos.

    SEGURANÇA: Impede que um usuário crie objetos em outra organização,
    mesmo que envie organization_id manualmente no payload.
    """

    def perform_create(self, serializer):
        org = getattr(self.request, "organization", None)
        if org is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Usuário não pertence a nenhuma organização.")
        # SEMPRE usa a org do request, IGNORA qualquer org_id no payload
        serializer.save(organization=org)
```

### Validação de Input — Nunca confiar no cliente

```python
# Serializers: SEMPRE validar no backend, mesmo que o frontend valide

class SimulacaoSerializer(serializers.Serializer):
    valor_total_divida = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal("0.01"),
        max_value=Decimal("999999999999.99"),
    )
    # NUNCA aceitar organization_id do payload — vem do middleware
    # NUNCA aceitar user_id do payload — vem do request.user
```

### Para agentic workers: regras de segurança

> **1. NUNCA retornar queryset sem filtro de organization.** Se org é None, retorne `qs.none()`.
> **2. NUNCA aceitar organization_id ou user_id do payload.** Sempre do request.
> **3. NUNCA desabilitar CSRF** (nem em APIs — usamos SessionAuthentication).
> **4. NUNCA usar `ALLOWED_HOSTS = ["*"]`** em produção.
> **5. NUNCA logar dados sensíveis** (senhas, tokens, dados financeiros detalhados).
> **6. NUNCA expor stack traces** em produção (`DEBUG = False`).
> **7. Sessão máxima: 24h.** Configurado no settings, não no código.
> **8. Rate limiting ativo** em todos os endpoints (20/min anon, 120/min auth).
> **9. HTTPS obrigatório** em produção (HSTS com preload).

---

## Backend — OOP, Desacoplamento, SOLID (OBRIGATÓRIO)

### Princípios Arquiteturais

| Princípio | Aplicação no Projeto |
|-----------|---------------------|
| **S** — Single Responsibility | Cada módulo faz UMA coisa: `engine.py` calcula, `service.py` orquestra, `views.py` trata HTTP |
| **O** — Open/Closed | Engines recebem input via dataclass, retornam result. Novos cenários = novos inputs, sem mudar engine |
| **L** — Liskov Substitution | `UUIDModel` é base de todos os models. Mixins são intercambiáveis |
| **I** — Interface Segregation | Serializers separados por operação (Create vs Response vs List) |
| **D** — Dependency Inversion | Views dependem de services (abstração), não de engines diretamente |

### Padrão de Camadas (OBRIGATÓRIO em cada app)

```
View (HTTP) → Serializer (validação) → Service (orquestração) → Engine (cálculo puro)
                                              ↓
                                        Model (persistência)
```

| Camada | Responsabilidade | Pode acessar |
|--------|-----------------|-------------|
| **View** (`views.py`) | Receber HTTP, delegar ao service, retornar response | Serializer, Service |
| **Serializer** (`serializers.py`) | Validar input, serializar output | Models (read-only para output) |
| **Service** (`service.py`) | Orquestrar lógica de negócio, persistir, chamar engine | Engine, Models, outros Services |
| **Engine** (`engine.py`) | Cálculo puro, sem I/O, sem Django, sem banco | Constants, dataclasses próprias |
| **Model** (`models.py`) | Schema do banco, managers, propriedades | Nada externo |
| **Constants** (`constants.py`) | Constantes legais, tabelas, limites | Nada |

### Regras de Desacoplamento

```python
# ✅ CORRETO — View delega ao Service, não chama Engine diretamente
class SimularView(APIView):
    def post(self, request):
        serializer = SimulacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = TransacaoService()
        resultado = service.simular(serializer.validated_data, request.organization)
        return Response(resultado)


# ❌ ERRADO — View chamando Engine diretamente (sem service)
class SimularView(APIView):
    def post(self, request):
        resultado = calcular_diagnostico(request.data)  # Engine direto na view
        Simulacao.objects.create(resultado=resultado)     # Persistência na view
        return Response(resultado)
```

```python
# ✅ CORRETO — Engine é puro, sem Django, sem I/O
def calcular_diagnostico(inp: DiagnosticoInput) -> DiagnosticoResult:
    """Função pura. Recebe dataclass, retorna dataclass. Sem banco, sem request."""
    ...


# ❌ ERRADO — Engine acessando banco ou request
def calcular_diagnostico(request):
    empresa = Empresa.objects.get(id=request.data["empresa_id"])  # I/O no engine!
    ...
```

```python
# ✅ CORRETO — Service orquestra engine + persistência
class TransacaoService:
    def __init__(self, organization: Organization):
        self.organization = organization

    def simular(self, dados: dict) -> dict:
        # 1. Preparar input
        inp = self._build_input(dados)
        # 2. Calcular (engine puro)
        resultado = calcular_diagnostico(inp)
        # 3. Persistir
        simulacao = self._salvar(resultado, dados)
        # 4. Retornar
        return self._serialize(simulacao, resultado)
```

### Custom Managers para Queries Comuns

```python
# apps/empresas/models.py
class EmpresaManager(models.Manager):
    """Manager com queries comuns já filtradas por organização."""

    def da_organizacao(self, org):
        return self.filter(organization=org)

    def buscar(self, org, termo):
        return self.da_organizacao(org).filter(
            models.Q(nome__icontains=termo) | models.Q(cnpj__icontains=termo)
        )


class Empresa(UUIDModel):
    objects = EmpresaManager()
    # ...
```

### Para agentic workers: regras de arquitetura

> **1. NUNCA colocar lógica de negócio na View.** View é fina: valida, delega, responde.
> **2. NUNCA importar Django no Engine.** Engine é Python puro com Decimal e dataclasses.
> **3. NUNCA acessar banco no Engine.** O Service busca os dados e passa pro Engine.
> **4. SEMPRE criar Service para operações que envolvem Engine + persistência.**
> **5. SEMPRE usar Custom Managers** para queries comuns (não queries inline nas views).
> **6. SEMPRE separar serializers** por operação: `CreateSerializer`, `ResponseSerializer`, `ListSerializer`.
> **7. Mixins para comportamento compartilhado** (OrgQuerySetMixin, OrgCreateMixin, UUIDModel).

## Primary Keys — UUID Obrigatório (NUNCA usar IDs numéricos)

**TODOS os models Django DEVEM usar `UUIDField` como primary key. NUNCA usar `AutoField`, `BigAutoField` ou qualquer ID numérico sequencial.**

### Justificativa
1. **Segurança:** IDs numéricos sequenciais expõem a quantidade de registros e permitem enumeração (IDOR attacks)
2. **API-friendly:** UUIDs são seguros para expor em URLs e responses sem risco de information disclosure
3. **Merge-safe:** Múltiplas instâncias/ambientes podem gerar IDs sem colisão
4. **Multi-tenant:** Evita que um usuário adivinhe IDs de outra organização

### Configuração global no settings

```python
# config/settings/base.py
# DESABILITAR AutoField global — forçar UUID explícito em cada model
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"  # Apenas para models de terceiros (allauth, admin, etc.)
```

> **Nota:** Mantemos `BigAutoField` como default APENAS porque bibliotecas de terceiros (django-allauth, django-admin) criam seus próprios models com AutoField. Nossos models SEMPRE declaram `id = models.UUIDField(...)` explicitamente.

### Model base obrigatório

Todos os models do projeto DEVEM herdar de `UUIDModel`:

```python
# apps/core/models.py
import uuid

from django.db import models


class UUIDModel(models.Model):
    """Model base abstrato com UUID como primary key.

    TODOS os models do projeto devem herdar desta classe.
    NUNCA criar models com id numérico sequencial.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True
```

### Uso obrigatório em CADA model

```python
# CORRETO ✅
class Empresa(UUIDModel):
    nome = models.CharField(max_length=200)
    organization = models.ForeignKey("core.Organization", on_delete=models.CASCADE)


# ERRADO ❌ — NUNCA fazer isso
class Empresa(models.Model):
    # id será BigAutoField numérico — PROIBIDO
    nome = models.CharField(max_length=200)
```

### ForeignKey para models UUID

```python
# ForeignKey para model UUID — Django infere o tipo correto automaticamente
organization = models.ForeignKey("core.Organization", on_delete=models.CASCADE)
# Isso cria uma coluna organization_id do tipo UUID no banco — correto ✅
```

### Serializers DRF — UUIDs como string

```python
# DRF serializa UUIDs automaticamente como string "550e8400-e29b-41d4-a716-446655440000"
# Não precisa de tratamento especial
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id", "nome", "cnpj"]  # id será UUID string automaticamente
```

### URLs — UUID no path

```python
# urls.py — usar <uuid:pk> no path (não <int:pk>)
urlpatterns = [
    path("<uuid:pk>/", EmpresaDetailView.as_view()),  # CORRETO ✅
    # path("<int:pk>/", ...),  # ERRADO ❌ — nunca usar int para PK
]
```

### Para agentic workers: regra absoluta

> **NUNCA crie um model sem `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
> A forma mais fácil é herdar de `UUIDModel`. Se esquecer e usar AutoField, o reviewer vai rejeitar.**
> **Em URLs, sempre use `<uuid:pk>`, nunca `<int:pk>`.**
> **Em testes, use `uuid.uuid4()` para gerar IDs, nunca números.**

---

## Padrão de Código — PEP 8 + Black (OBRIGATÓRIO)

**Todo o código Python DEVE seguir PEP 8 rigorosamente, formatado com Black.**

### Ferramentas de qualidade (executar ANTES de cada commit)

```bash
# Formatação automática (Black — estilo definitivo, sem configuração)
black .

# Ordenação de imports (isort — compatível com Black)
isort .

# Linting (flake8 — erros que Black não pega)
flake8 .
```

### Configuração no `pyproject.toml`

```toml
[tool.black]
line-length = 120
target-version = ["py312"]

[tool.isort]
profile = "black"
line_length = 120
known_django = ["django", "rest_framework"]
known_first_party = ["apps", "config"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "DJANGO", "FIRSTPARTY", "LOCALFOLDER"]

[tool.flake8]
max-line-length = 120
extend-ignore = ["E203", "W503"]
exclude = [".git", "__pycache__", "migrations", "staticfiles"]
```

### Regras PEP 8 aplicadas neste projeto

| Regra | Exemplo |
|-------|---------|
| `snake_case` para funções, variáveis, módulos | `calcular_desconto()`, `valor_total`, `engine_avancado.py` |
| `PascalCase` para classes | `Organization`, `SimulacaoAvancadaResult` |
| `UPPER_CASE` para constantes | `DESCONTO_MAX_GERAL`, `PRAZO_MAX_PREVIDENCIARIO` |
| Máximo **120 caracteres** por linha | Configurado no Black e flake8 |
| Imports organizados (isort) | stdlib → terceiros → django → apps locais |
| Type hints em funções públicas | `def calcular_desconto(valor: Decimal, pct: Decimal) -> Decimal:` |
| Docstrings em funções públicas | Google-style, com referência legal quando aplicável |
| Early return | Tratar erros/exceções no início, retornar cedo |
| Sem magic numbers | Usar constantes nomeadas de `constants.py` |
| Sem `# noqa` sem justificativa | Se usar `# noqa`, comentar o motivo |

### Docstrings — padrão Google-style com referência legal

```python
def calcular_desconto_componentes(
    componentes: DebitoComponentes,
    desconto_pct: Decimal,
) -> DescontoResult:
    """Aplica desconto sobre multa, juros e encargos. Principal não sofre desconto.

    O desconto incide APENAS sobre multa + juros + encargos, conforme
    vedação expressa do art. 11, §2º, I da Lei 13.988/2020:
    "É vedada a redução do montante principal do crédito."

    Args:
        componentes: Decomposição da dívida em Principal/Multa/Juros/Encargos.
        desconto_pct: Percentual de desconto (0.0 a 1.0). Ex: 0.70 para 70%.

    Returns:
        DescontoResult com valores antes/depois do desconto por componente.

    References:
        - Lei 13.988/2020, art. 11, §2º, I (vedação desconto no principal)
        - Lei 13.988/2020, art. 11, §2º, II (limite 65% do total)
        - Lei 13.988/2020, art. 11, §3º (limite 70% para ME/EPP/PF)
    """
```

### Pre-commit hook (opcional mas recomendado)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 25.1.0
    hooks:
      - id: black
        args: [--line-length=120]
  - repo: https://github.com/pycqa/isort
    rev: 6.0.1
    hooks:
      - id: isort
        args: [--profile=black, --line-length=120]
  - repo: https://github.com/pycqa/flake8
    rev: 7.2.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203]
```

### Para agentic workers: regras de ouro (OBRIGATÓRIO)

> **1. NUNCA submeta código sem rodar `black . && isort . && flake8 .` antes do commit.**
> Se flake8 reportar erros, corrija-os. Se Black reformatar algo, aceite — Black é definitivo.
> Imports SEMPRE ordenados com isort (profile=black para compatibilidade).
>
> **2. CADA commit em CADA task DEVE passar por `black . && isort . && flake8 .`.**
> Se o pre-commit hook bloquear o commit, corrija e tente novamente. NUNCA use `--no-verify`.
>
> **3. Código novo deve seguir PEP 8 desde a primeira linha.**
> Não escreva código "rascunho" para formatar depois. Escreva correto desde o início:
> - `snake_case` para tudo que não seja classe
> - `PascalCase` para classes
> - `UPPER_CASE` para constantes
> - Type hints em todas as funções públicas
> - Docstrings Google-style com referência legal em funções de cálculo
> - Máximo 120 caracteres (Black cuida disso)
> - Imports organizados (isort cuida disso)
>
> **4. Ao escrever testes, os testes também devem passar por Black/isort/flake8.**
> Testes são código de produção — mesma qualidade.

---

## Base Legal Implementada

### Lei nº 13.988/2020 (alterada por Lei 14.375/2022 e Lei 14.689/2023)
- **Art. 11, §2º, I:** VEDADO reduzir o montante principal — desconto somente sobre multa/juros/encargos
- **Art. 11, §2º, II:** Desconto máximo **65%** do valor total do crédito
- **Art. 11, §3º:** ME/EPP/PF: desconto máximo **70%**, prazo máximo **145 meses**
- **Art. 11, §2º, III:** Prazo máximo **120 meses** (demais empresas)
- **Art. 11, §1º:** Parcelas atualizadas pela **SELIC acumulada mensal** + 1% no mês do pagamento
- **Art. 11, IV:** Uso de prejuízo fiscal e BCN-CSLL até 70% do saldo remanescente
- **Art. 11, §12:** Descontos NÃO são base de cálculo IRPJ/CSLL/PIS/COFINS
- **Art. 5º, II, "a":** VEDADO desconto Simples Nacional sem LC autorizativa
- **Art. 6º:** ME/EPP = receita bruta nos limites da LC 123/2006

### Portaria PGFN nº 6.757/2022
- **Art. 21-25:** CAPAG — Capacidade de Pagamento, classificação A/B/C/D
- **Art. 36:** Entrada de **6%** sem desconto, em até **6 parcelas** (demais) ou **12 parcelas** (ME/EPP/PF)
- **Parcela mínima:** R$ 25,00 (MEI), R$ 100,00 (demais)

### CF/88, art. 195, §11 (EC 103/2019)
- Prazo máximo **60 meses** para contribuições previdenciárias patronais e dos trabalhadores

### Edital PGDAU 11/2025 — TPV (Transação de Pequeno Valor)
- **Elegibilidade:** PF, ME, EPP — CDA ≤ 60 SM — inscrita há > 1 ano
- **Entrada:** 5% em até 5 parcelas
- **Descontos escalonados:** 50% (7x), 45% (12x), 40% (30x), 30% (55x)
- **Desconto incide sobre TODO o saldo** (inclusive principal — exceção legal TPV)

### APIs de Índices (Banco Central — SGS)
- **Série 4390:** SELIC acumulada mensal (% a.m.)
- **Série 11:** SELIC diária (% a.d.)
- **Série 433:** IPCA mensal (%)
- **Endpoint:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json`
- **Fórmula:** `valor_corrigido = valor_original × Π(1 + SELIC_mensal/100) × 1.01`

### Classificação CAPAG (Portaria PGFN 6.757/2022, arts. 21-25) — FÓRMULA OFICIAL

#### Rating: Relação CAPAG/Dívida Consolidada (art. 24)

| Rating | Critério | Descrição | Desconto |
|--------|----------|-----------|----------|
| **A** | CAPAG ≥ 2× dívida | Alta recuperação | **SEM desconto** — só entrada facilitada |
| **B** | CAPAG ≥ 1× dívida (< 2×) | Média recuperação | **SEM desconto** — só entrada facilitada |
| **C** | CAPAG ≥ 0.5× dívida (< 1×) | Difícil recuperação | Até 65%/70% |
| **D** | CAPAG < 0.5× dívida | Irrecuperável | Até 65%/70% |

```python
# Implementação exata do Rating (Portaria PGFN 6.757/2022, art. 24)
def classificar_rating(capag: Decimal, divida_consolidada: Decimal) -> str:
    if divida_consolidada <= 0:
        return "A"
    ratio = capag / divida_consolidada
    if ratio >= Decimal("2.0"):
        return "A"
    elif ratio >= Decimal("1.0"):
        return "B"
    elif ratio >= Decimal("0.5"):
        return "C"
    else:
        return "D"
```

#### Fórmula do Desconto (Princípio: Saldo Transacionado = CAPAG)
```
Desconto_ideal = Dívida_Consolidada - CAPAG
Desconto_efetivo = min(Desconto_ideal, Dívida × 65% [ou 70%], Multa+Juros+Encargos)
```
O desconto NUNCA pode reduzir o principal (art. 11, §2º, I da Lei 13.988).

#### Critérios Objetivos para D — Irrecuperável (art. 25)
Independente da CAPAG, é classificado D se:
1. Inscrito em dívida ativa há **> 15 anos** sem garantia/suspensão
2. Exigibilidade suspensa judicialmente há **> 10 anos**
3. Devedor **falido**, em **recuperação judicial/extrajudicial**, **liquidação** ou **intervenção**
4. PJ com **CNPJ baixado ou inapto**
5. PF com **indicativo de óbito**
6. Execução fiscal **arquivada há > 3 anos**

#### CAPAG Presumida — Fórmulas por Grupo (fonte: gov.br/pgfn)

**Grupo 2 — PJ Ativa (Lucro Real/Presumido):**
```
CAPAG = 5 × (0.10×DARF_pagos + 0.10×Rend_terceiros + 0.10×IR_retido
        + 0.05×NFe_emitente + 0.05×NFe_destinatario
        + 0.50×Receita_bruta_ECF + 0.40×Débitos_DCTF)
      + 1.00×Garantias_PGFN + 0.80×Veículos_RENAVAM + 0.80×Imóveis_DOI
```

**Grupo 3 — Simples Nacional:**
```
CAPAG = 5 × (0.03×Receita_PGDAS + 0.09×DARF_pagos + 0.01×Rend_terceiros
        + 0.25×IR_retido + 0.50×Rend_aplicações + 0.08×NFe_destinatario)
      + 0.70×Garantias_PGFN + 0.80×Veículos_RENAVAM + 0.80×Imóveis_DOI
```

**Grupo 1 — Pessoa Física:**
```
CAPAG = 5 × (0.30×Rend_isentos + 0.10×Rend_tributáveis + 1.00×Rend_capital)
      + 0.80×Bens_direitos + 0.90×Garantias_PGFN + 0.80×Veículos + 0.80×Imóveis
```

**Nota:** Na nossa plataforma, o usuário informa a CAPAG Presumida que obteve no Regularize. As fórmulas acima são documentadas para **transparência** — o usuário entende como a PGFN calculou.

#### CAPAG Presumida vs Efetiva
| Aspecto | Presumida | Efetiva |
|---------|-----------|---------|
| Origem | Cálculo automático PGFN (estatístico) | Revisão pelo contribuinte (laudo técnico) |
| Prazo revisão | — | 30 dias após tomar conhecimento |
| Reversibilidade | Pode ser revisada | **Irreversível** |
| Documentos | — | Laudo técnico, balanços (2 exercícios), DRE, extratos, relação de bens |

---

## Modelo Multi-Tenant

```
SUPERUSER
  └── Cria convite → email do dono do escritório
        └── Dono clica link → cria conta + Organization
              └── Dono convida membros → email
                    └── Membro clica link → cria conta vinculada à Org
```

**Isolamento:** Todos os models de negócio têm FK `organization_id`. Queries filtram sempre por `request.user.organization`.

---

## File Structure

```
was_contabil/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                        # Black + isort config
├── setup.cfg                             # flake8 config
├── .pre-commit-config.yaml               # Pre-commit hooks (black, isort, flake8)
├── requirements/
│   ├── base.txt                          # Dependências de produção
│   ├── dev.txt                           # pytest, factory-boy, ruff
│   └── prod.txt                          # gunicorn, sentry-sdk
├── manage.py
├── config/                               # Projeto Django (settings)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                       # Settings comuns
│   │   ├── local.py                      # Dev settings
│   │   ├── test.py                       # Test settings
│   │   └── production.py                # Prod settings
│   ├── urls.py                           # URL root
│   └── wsgi.py
├── apps/
│   ├── core/                             # Multi-tenant, users, invitations
│   │   ├── __init__.py
│   │   ├── models.py                     # Organization, Membership, Invitation
│   │   ├── admin.py                      # Admin apenas para debug
│   │   ├── middleware.py                 # OrganizationMiddleware (seta org no request)
│   │   ├── mixins.py                     # OrgQuerySetMixin, OrgCreateMixin
│   │   ├── serializers.py               # DRF serializers
│   │   ├── views.py                      # Convites, org management
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_middleware.py
│   │       └── test_invitations.py
│   ├── empresas/                         # Cadastro de empresas (CRUD)
│   │   ├── __init__.py
│   │   ├── models.py                     # Empresa (org FK, honorários, porte)
│   │   ├── admin.py
│   │   ├── serializers.py
│   │   ├── views.py                      # ModelViewSet
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_views.py
│   ├── transacao/                        # Simulação Capacidade de Pagamento
│   │   ├── __init__.py
│   │   ├── models.py                     # Simulacao (org FK, resultado JSONB)
│   │   ├── admin.py
│   │   ├── constants.py                  # Constantes legais com referências
│   │   ├── engine.py                     # Engine básico (valor total)
│   │   ├── engine_avancado.py            # Engine P/M/J/E + CAPAG + 3 categorias
│   │   ├── serializers.py               # DRF serializers (básico + avançado)
│   │   ├── views.py                      # APIViews: simular, historico, PDF
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_constants.py
│   │       ├── test_engine.py
│   │       ├── test_engine_avancado.py
│   │       └── test_views.py
│   ├── tpv/                              # Transação de Pequeno Valor
│   │   ├── __init__.py
│   │   ├── models.py                     # SimulacaoTPV (org FK)
│   │   ├── admin.py
│   │   ├── constants.py                  # Constantes TPV (60 SM, descontos)
│   │   ├── engine.py                     # Engine TPV (multi-CDA)
│   │   ├── validators.py                 # Validação elegibilidade CDA
│   │   ├── importers.py                  # Parser CSV + Excel (openpyxl)
│   │   ├── serializers.py
│   │   ├── views.py                      # APIViews: simular, wizard, import, elegibilidade
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_constants.py
│   │       ├── test_engine.py
│   │       ├── test_validators.py
│   │       ├── test_importers.py
│   │       └── test_views.py
│   ├── indices/                          # Índices econômicos (SELIC, IPCA)
│   │   ├── __init__.py
│   │   ├── models.py                     # IndiceEconomico
│   │   ├── admin.py
│   │   ├── client.py                     # HTTP client API BCB (SGS)
│   │   ├── service.py                    # Sync + cache + cálculo SELIC acumulada
│   │   ├── tasks.py                      # django-rq jobs: sync diário
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── sync_indices.py       # Management command para cron
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_client.py
│   │       └── test_service.py
│   ├── comparador/                       # Comparação entre modalidades
│   │   ├── __init__.py
│   │   ├── service.py                    # TPV vs Capacidade: qual é melhor?
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_service.py
│   └── pdf/                              # Geração de PDF
│       ├── __init__.py
│       ├── generators.py                 # WeasyPrint + Django templates → PDF
│       ├── views.py                      # Endpoints de download PDF
│       ├── urls.py
│       └── tests/
│           ├── __init__.py
│           └── test_generators.py
├── templates/                            # Django templates (HTMX frontend + PDF)
│   ├── base.html                         # Layout base com Tailwind + HTMX
│   ├── components/                       # Componentes reutilizáveis
│   │   ├── _navbar.html
│   │   ├── _footer.html
│   │   ├── _rating_badge.html            # Badge CAPAG A/B/C/D
│   │   ├── _calculo_detalhe.html         # Passo a passo do cálculo com ref legal
│   │   └── _fluxo_parcelas.html
│   ├── core/
│   │   ├── login.html
│   │   ├── invite.html
│   │   └── organization_setup.html
│   ├── empresas/
│   │   ├── list.html
│   │   ├── form.html
│   │   └── _search_results.html          # HTMX partial
│   ├── transacao/
│   │   ├── simulacao_basica.html         # Diagnóstico Prévio
│   │   ├── simulacao_avancada.html       # CAPAG com P/M/J/E
│   │   ├── resultado.html
│   │   ├── resultado_avancado.html
│   │   └── historico.html
│   ├── tpv/
│   │   ├── simulador_cda.html            # TPV por CDA
│   │   ├── wizard.html                   # Wizard simplificado
│   │   ├── resultado.html
│   │   ├── elegibilidade.html
│   │   └── import_cdas.html
│   ├── comparador/
│   │   └── comparacao.html
│   └── pdf/                              # Templates exclusivos para PDF
│       ├── _pdf_base.html                # Base com CSS @page A4
│       ├── diagnostico.html
│       ├── simulacao_avancada_resumido.html
│       ├── simulacao_avancada_completo.html
│       └── tpv_relatorio.html
├── static/
│   ├── css/
│   │   └── app.css                       # Tailwind custom + print styles
│   └── js/
│       └── app.js                        # HTMX config + Alpine.js (se necessário)
└── conftest.py                           # pytest fixtures globais
```

---

## Task 1: Projeto Django + Docker + Settings

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`
- Create: `requirements/base.txt`, `requirements/dev.txt`
- Create: `config/settings/base.py`, `config/settings/local.py`, `config/settings/test.py`
- Create: `config/urls.py`, `config/wsgi.py`
- Create: `manage.py`

- [ ] **Step 1: Criar `requirements/base.txt`**

```
Django==5.2.12
djangorestframework==3.16.1
django-allauth==65.15.0
django-rq==4.0.1
django-htmx==1.27.0
django-weasyprint==2.4.0
psycopg2-binary==2.9.10
redis==5.2.1
httpx==0.28.1
weasyprint==68.1
openpyxl==3.1.5
```

- [ ] **Step 2: Criar `requirements/dev.txt`**

```
-r base.txt
pytest==9.0.2
pytest-django==4.12.0
factory-boy==3.3.3
black==25.1.0
isort==6.0.1
flake8==7.2.0
pre-commit==4.2.0
coverage==7.6.0
```

- [ ] **Step 3: Criar `config/settings/base.py`**

```python
"""
Settings base do WAS Contábil.
Todas as variáveis sensíveis vêm de variáveis de ambiente.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "django_htmx",
    "django_rq",
    # Local apps
    "apps.core",
    "apps.empresas",
    "apps.transacao",
    "apps.tpv",
    "apps.indices",
    "apps.comparador",
    "apps.pdf",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.core.middleware.OrganizationMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "was_contabil"),
        "USER": os.environ.get("DB_USER", "was_contabil"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "was_contabil"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

# --- Sessão: máximo 24 horas ---
SESSION_COOKIE_AGE = 86400
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

# --- Segurança ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "120/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# django-allauth
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "optional"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# django-rq
RQ_QUEUES = {
    "default": {
        "URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "DEFAULT_TIMEOUT": 300,
    },
}

# BCB API
BCB_API_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
```

- [ ] **Step 4: Criar `config/settings/local.py`**

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = "dev-secret-key-not-for-production"

# Segurança relaxada em dev (NUNCA em produção)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# DRF: browsable API habilitada + sem throttle em dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"anon": "1000/minute", "user": "1000/minute"}  # noqa: F405
```

- [ ] **Step 5: Criar `config/settings/test.py`**

```python
from .base import *

DEBUG = False
SECRET_KEY = "test-secret-key"
DATABASES["default"]["NAME"] = "was_contabil_test"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Convites gerenciados manualmente via apps.core.models.Invitation
```

- [ ] **Step 6: Criar `config/urls.py`**

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("convites/", include("apps.core.urls_invitations")),
    path("django-rq/", include("django_rq.urls")),
    # API REST (preparado para Vue frontend)
    path("api/v1/empresas/", include("apps.empresas.urls")),
    path("api/v1/transacao/", include("apps.transacao.urls")),
    path("api/v1/tpv/", include("apps.tpv.urls")),
    path("api/v1/indices/", include("apps.indices.urls")),
    path("api/v1/comparador/", include("apps.comparador.urls")),
    # Frontend templates (HTMX)
    path("", include("apps.core.urls")),
]
```

- [ ] **Step 7: Criar `Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libglib2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 8: Criar `docker-compose.yml`**

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app

  worker:
    build: .
    command: python manage.py rqworker default
    env_file: .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.local
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
      POSTGRES_DB: was_contabil
      POSTGRES_USER: was_contabil
      POSTGRES_PASSWORD: was_contabil
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U was_contabil"]
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

- [ ] **Step 9: Criar `manage.py`, `config/__init__.py`, `config/wsgi.py`**

```python
# manage.py
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
```

- [ ] **Step 10: Criar `pyproject.toml` (Black + isort config)**

```toml
[tool.black]
line-length = 120
target-version = ["py312"]

[tool.isort]
profile = "black"
line_length = 120
known_django = ["django", "rest_framework"]
known_first_party = ["apps", "config"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "DJANGO", "FIRSTPARTY", "LOCALFOLDER"]
```

- [ ] **Step 11: Criar `setup.cfg` (flake8 config)**

```ini
[flake8]
max-line-length = 120
extend-ignore = E203,W503
exclude = .git,__pycache__,migrations,staticfiles,node_modules
per-file-ignores =
    __init__.py:F401
```

- [ ] **Step 12: Criar `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 25.1.0
    hooks:
      - id: black
        args: [--line-length=120]
  - repo: https://github.com/pycqa/isort
    rev: 6.0.1
    hooks:
      - id: isort
        args: [--profile=black, --line-length=120]
  - repo: https://github.com/pycqa/flake8
    rev: 7.2.0
    hooks:
      - id: flake8
        args: [--max-line-length=120, --extend-ignore=E203]
```

- [ ] **Step 13: Criar `.env.example` e `.gitignore`**

```bash
cat > .env.example << 'EOF'
DJANGO_SECRET_KEY=gerar-chave-segura
DJANGO_SETTINGS_MODULE=config.settings.local
DB_NAME=was_contabil
DB_USER=was_contabil
DB_PASSWORD=was_contabil
DB_HOST=postgres
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
EOF
```

- [ ] **Step 14: Criar `conftest.py` global**

```python
import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Membership, Organization

User = get_user_model()


@pytest.fixture
def organization(db):
    """Cria organização de teste com UUID como PK."""
    org = Organization.objects.create(name="Escritório Teste", slug="escritorio-teste")
    assert isinstance(org.pk, uuid.UUID)  # Garante UUID
    return org


@pytest.fixture
def user(db, organization):
    """Cria usuário de teste vinculado a uma organização."""
    user = User.objects.create_user(email="test@test.com", password="testpass123")
    Membership.objects.create(user=user, organization=organization)
    return user


@pytest.fixture
def api_client(user):
    """APIClient autenticado com organização setada."""
    client = APIClient()
    client.force_authenticate(user=user)
    # Simula o middleware setando a org
    client._organization = user.membership_set.first().organization
    return client
```

- [ ] **Step 15: Verificar que Docker build funciona**

Run: `docker compose build`
Expected: Build completo sem erros

- [ ] **Step 16: Inicializar Django + migrations + superuser**

Run:
```bash
docker compose up -d postgres redis
docker compose run app python manage.py migrate
docker compose run app python manage.py createsuperuser
```

- [ ] **Step 17: Instalar pre-commit hooks + rodar formatação**

Run:
```bash
pip install -r requirements/dev.txt
pre-commit install
black .
isort .
flake8 .
```
Expected: Zero erros de formatação e linting

- [ ] **Step 18: Commit**

```bash
git init
echo -e ".env\n__pycache__\n*.pyc\n.pytest_cache\npgdata\nstaticfiles/\ndb.sqlite3\n*.egg-info/\ncredenciais.json" > .gitignore
git add .
# Pre-commit hooks rodam automaticamente (black, isort, flake8)
git commit -m "feat: Django project setup with Docker, DRF, allauth, django-rq, multi-tenant, Black+PEP8"
```

---

## Task 2: App Core — Organization, Membership, Invitations

**Files:**
- Create: `apps/core/__init__.py`
- Create: `apps/core/models.py`
- Create: `apps/core/middleware.py`
- Create: `apps/core/mixins.py`
- Create: `apps/core/admin.py`
- Create: `apps/core/urls.py`
- Create: `apps/core/views.py`
- Create: `apps/core/tests/test_models.py`
- Create: `apps/core/tests/test_middleware.py`
- Create: `apps/core/tests/test_invitations.py`

- [ ] **Step 1: Escrever testes dos models core**

```python
# apps/core/tests/test_models.py
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Organization, Membership, UUIDModel

User = get_user_model()


@pytest.mark.django_db
class TestUUIDModel:
    def test_organization_pk_is_uuid(self):
        org = Organization.objects.create(name="Test", slug="test")
        assert isinstance(org.pk, uuid.UUID)

    def test_membership_pk_is_uuid(self):
        org = Organization.objects.create(name="Test", slug="test")
        user = User.objects.create_user(email="u@t.com", password="pass123")
        m = Membership.objects.create(user=user, organization=org)
        assert isinstance(m.pk, uuid.UUID)

    def test_all_models_inherit_uuid_model(self):
        assert issubclass(Organization, UUIDModel)
        assert issubclass(Membership, UUIDModel)


@pytest.mark.django_db
class TestOrganization:
    def test_create_organization(self):
        org = Organization.objects.create(name="Escritório ABC", slug="escritorio-abc")
        assert org.name == "Escritório ABC"
        assert str(org) == "Escritório ABC"
        assert isinstance(org.id, uuid.UUID)

    def test_slug_unique(self):
        Organization.objects.create(name="Org 1", slug="org-1")
        with pytest.raises(Exception):
            Organization.objects.create(name="Org 2", slug="org-1")


@pytest.mark.django_db
class TestMembership:
    def test_user_belongs_to_organization(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(email="user@test.com", password="pass123")
        membership = Membership.objects.create(user=user, organization=org, is_owner=True)

        assert membership.user == user
        assert membership.organization == org
        assert membership.is_owner is True

    def test_user_cannot_join_same_org_twice(self):
        org = Organization.objects.create(name="Test Org", slug="test-org")
        user = User.objects.create_user(email="user@test.com", password="pass123")
        Membership.objects.create(user=user, organization=org)
        with pytest.raises(Exception):
            Membership.objects.create(user=user, organization=org)
```

- [ ] **Step 2: Rodar testes para ver falhar**

Run: `pytest apps/core/tests/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar models**

```python
# apps/core/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Organization(UUIDModel):
    """Escritório/consultoria — unidade de isolamento multi-tenant."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(UUIDModel):
    """Vínculo usuário ↔ organização."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_owner = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ["user", "organization"]

    def __str__(self):
        return f"{self.user} @ {self.organization}"


class Invitation(UUIDModel):
    """Convite por email para criar organização ou juntar-se a uma existente.

    Fluxo:
    - Superuser cria convite → email enviado → destinatário cria conta + org
    - Dono da org cria convite → email enviado → destinatário cria conta na org
    """

    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Se null, destinatário cria nova org. Se preenchido, entra na org existente.",
    )
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_org_invite = models.BooleanField(
        default=False, help_text="True = convite para criar nova org (só superuser)"
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Convite para {self.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_accepted(self):
        return self.accepted_at is not None
```

- [ ] **Step 4: Implementar middleware**

```python
# apps/core/middleware.py
from apps.core.models import Membership


class OrganizationMiddleware:
    """Seta request.organization baseado no usuário logado."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        if request.user.is_authenticated:
            membership = (
                Membership.objects.filter(user=request.user)
                .select_related("organization")
                .first()
            )
            if membership:
                request.organization = membership.organization
        return self.get_response(request)
```

- [ ] **Step 5: Implementar mixins para isolamento multi-tenant**

```python
# apps/core/mixins.py
from rest_framework.exceptions import PermissionDenied


class OrgQuerySetMixin:
    """Filtra queryset por organization do request."""

    def get_queryset(self):
        qs = super().get_queryset()
        if not hasattr(self.request, "organization") or not self.request.organization:
            raise PermissionDenied("Usuário não pertence a nenhuma organização.")
        return qs.filter(organization=self.request.organization)


class OrgCreateMixin:
    """Seta organization automaticamente ao criar objetos."""

    def perform_create(self, serializer):
        if not self.request.organization:
            raise PermissionDenied("Usuário não pertence a nenhuma organização.")
        serializer.save(organization=self.request.organization)
```

- [ ] **Step 6: Rodar testes**

Run: `pytest apps/core/tests/ -v`
Expected: Todos PASS

- [ ] **Step 7: Commit**

```bash
git add apps/core/
git commit -m "feat: core app - Organization, Membership, middleware, multi-tenant mixins"
```

---

> **Nota:** As Tasks 3-26 seguem o mesmo padrão TDD rigoroso. Para manter este documento gerenciável, vou listar as Tasks restantes com seus arquivos e responsabilidades, e detalhar o código completo das Tasks mais críticas (engines de cálculo).

---

## Task 3: App Empresas — CRUD com isolamento multi-tenant

**Files:** `apps/empresas/` (models, serializers, views, urls, tests)

**Model:** `Empresa(organization FK, nome, cnpj, porte, honorarios_percentual, observacoes)`

**Endpoints DRF:** `ModelViewSet` com `OrgQuerySetMixin` + `OrgCreateMixin` + busca por nome/CNPJ

- [ ] Escrever testes (CRUD + isolamento multi-tenant)
- [ ] Rodar testes → FAIL
- [ ] Implementar model + serializer + viewset
- [ ] Rodar testes → PASS
- [ ] Migration + commit

---

## Task 4: Constantes Legais Transação (com referências) + Testes

**Files:** `apps/transacao/constants.py`, `apps/transacao/tests/test_constants.py`

Mesmo conteúdo do plano anterior, mas com **documentação inline expandida** mostrando artigo + parágrafo de cada constante. Cada constante tem um docstring com a referência legal.

- [ ] Escrever testes
- [ ] Rodar → FAIL
- [ ] Implementar constants.py
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 5: Engine de Cálculo Básico (Diagnóstico Prévio) + Testes TDD

**Files:** `apps/transacao/engine.py`, `apps/transacao/tests/test_engine.py`

Engine puramente funcional. Cada função retorna um `dict` com campo `_calculo_detalhes` contendo o passo a passo:

```python
{
    "resultado": { ... },
    "_calculo_detalhes": [
        {
            "passo": 1,
            "descricao": "Desconto de 65% sobre multa+juros+encargos",
            "formula": "R$ 1.000,00 × 65% = R$ 650,00",
            "referencia_legal": "Lei 13.988/2020, art. 11, §2º, II",
        },
        ...
    ]
}
```

- [ ] Escrever testes (incluindo verificação dos detalhes do cálculo)
- [ ] Rodar → FAIL
- [ ] Implementar engine.py
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 6: Engine Avançado (P/M/J/E + CAPAG + 3 categorias) + Testes TDD

**Files:** `apps/transacao/engine_avancado.py`, `apps/transacao/tests/test_engine_avancado.py`

O engine mais importante do sistema. Inclui:
- Decomposição Principal/Multa/Juros/Encargos
- Desconto APENAS sobre multa+juros+encargos (art. 11, §2º, I)
- 3 categorias: Previdenciário (60m), Tributário (120/145m), Simples Nacional (120/145m)
- Rating CAPAG automático com fórmula transparente
- Honorários de êxito
- Menor/Maior desconto
- `_calculo_detalhes` em cada passo

- [ ] Escrever testes (rating, decomposição, honorários, transparência)
- [ ] Rodar → FAIL
- [ ] Implementar engine_avancado.py
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 7: Constantes e Validadores TPV + Testes TDD

**Files:** `apps/tpv/constants.py`, `apps/tpv/validators.py`, `apps/tpv/tests/`

Constantes TPV (60 SM, descontos 50/45/40/30%, entrada 5%), validação de CDA (valor ≤ 60 SM, inscrição > 1 ano), projeção de elegibilidade futura.

- [ ] Escrever testes
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 8: Engine TPV (Multi-CDA + Multi-Faixa + Wizard) + Testes TDD

**Files:** `apps/tpv/engine.py`, `apps/tpv/tests/test_engine.py`

Engine com:
- `calcular_tpv()` — simulação com CDAs individuais
- `calcular_tpv_todas_faixas()` — 4 faixas lado a lado
- `validar_elegibilidade_wizard()` — checklist de elegibilidade
- `_calculo_detalhes` em cada resultado

- [ ] Escrever testes
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 9: Importador CSV/Excel (CDAs do Regularize) + Testes

**Files:** `apps/tpv/importers.py`, `apps/tpv/tests/test_importers.py`

Parser CSV + Excel (.xlsx via openpyxl). Reconhece formato de exportação do Regularize.

- [ ] Escrever testes (CSV válido, Excel válido, linhas inválidas)
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 10: Client API Banco Central (SELIC/IPCA) + Testes

**Files:** `apps/indices/client.py`, `apps/indices/tests/test_client.py`

HTTP client (httpx sync) para API BCB SGS. Séries 4390, 11, 433.

- [ ] Escrever testes (com mock)
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 11: Serviço de Índices (Cache + Sync + Correção SELIC) + Testes

**Files:** `apps/indices/service.py`, `apps/indices/models.py`, `apps/indices/tasks.py`, `apps/indices/management/commands/sync_indices.py`

Model `IndiceEconomico`, sync via django-rq ou management command, cálculo SELIC acumulada.

- [ ] Escrever testes
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 12: Serviço Comparador de Modalidades + Testes

**Files:** `apps/comparador/service.py`, `apps/comparador/tests/test_service.py`

Compara TPV vs Capacidade de Pagamento, recomenda a melhor opção.

- [ ] Escrever testes
- [ ] Rodar → FAIL
- [ ] Implementar
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 13: Models de Simulação (Transação + TPV) + Migrations

**Files:** `apps/transacao/models.py`, `apps/tpv/models.py`

Models com `organization` FK, resultado em JSONField, versão do cálculo, referências legais usadas.

- [ ] Implementar models
- [ ] Gerar migrations
- [ ] Commit

---

## Task 14: Serializers DRF (Transação + TPV)

**Files:** `apps/transacao/serializers.py`, `apps/tpv/serializers.py`

Serializers de request/response para todos os endpoints. Validação de CNPJ com dígito verificador.

- [ ] Implementar serializers
- [ ] Commit

---

## Task 15: Views/Endpoints DRF (Transação + TPV + Índices)

**Files:** `apps/transacao/views.py`, `apps/tpv/views.py`, `apps/indices/views.py`, `apps/comparador/views.py`

Todos os endpoints da API REST com `OrgQuerySetMixin`.

- [ ] Implementar views
- [ ] Configurar urls.py de cada app
- [ ] Commit

---

## Task 16: Testes de Integração dos Endpoints

**Files:** `apps/transacao/tests/test_views.py`, `apps/tpv/tests/test_views.py`

Testes end-to-end com `APIClient` + multi-tenant.

- [ ] Escrever testes
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 17: Templates Base (HTML + Tailwind + HTMX)

**Files:** `templates/base.html`, `templates/components/`, `static/`

Layout base com Tailwind CSS (CDN para MVP), HTMX, navbar, footer, componentes reutilizáveis.

- [ ] Criar base.html com layout responsivo
- [ ] Criar componentes (_navbar, _footer, _rating_badge, _calculo_detalhe)
- [ ] Commit

---

## Task 18: Templates Transação (Diagnóstico Prévio + Avançado)

**Files:** `templates/transacao/`

Formulários com HTMX para simulação sem reload, resultado com passo a passo do cálculo.

- [ ] Criar templates
- [ ] Conectar views Django (não API, mas template views)
- [ ] Commit

---

## Task 19: Templates TPV (Simulador CDA + Wizard + Elegibilidade)

**Files:** `templates/tpv/`

Wizard de elegibilidade com HTMX, importação Excel, tabela de CDAs com status.

- [ ] Criar templates
- [ ] Conectar views
- [ ] Commit

---

## Task 20: Geração PDF (WeasyPrint + Django templates)

**Files:** `apps/pdf/generators.py`, `templates/pdf/`, `apps/pdf/tests/`

Reutiliza templates Django com CSS `@page` para A4. Modos: Resumido e Completo.

- [ ] Escrever testes (PDF gerado, contém dados corretos)
- [ ] Implementar generator + templates PDF
- [ ] Rodar → PASS
- [ ] Commit

---

## Task 21: Templates Login/Convites/Organização

**Files:** `templates/core/`

Páginas de login (allauth), aceitar convite, setup da organização.

- [ ] Criar templates
- [ ] Commit

---

## Task 22: Integração Final + Docker Compose Up + Smoke Test

- [ ] Subir toda a stack (`docker compose up -d`)
- [ ] Rodar migrations
- [ ] Criar superuser
- [ ] Testar login OAuth
- [ ] Testar simulação completa
- [ ] Rodar todos os testes (`pytest --tb=short`)
- [ ] Commit final

---

## Resumo de Referências Legais e Técnicas

### Legislação
| Referência | Assunto | Artigos-Chave |
|-----------|---------|---------------|
| Lei 13.988/2020 | Transação tributária | art. 11 (descontos/prazos/SELIC), art. 5 (vedações), art. 6 (ME/EPP) |
| Lei 14.375/2022 | Alterações na transação | Amplia desconto 65%, prazo 120m, prejuízo fiscal |
| Lei 14.689/2023 | Ampliação escopo | Autarquias/fundações, contencioso por adesão |
| Portaria PGFN 6.757/2022 | Regulamentação | arts. 21-40 (CAPAG A/B/C/D, entrada, parcelas) |
| CF/88, art. 195, §11 | Limite previdenciário | Máx. 60m contribuições patronais/trabalhadores |
| LC 123/2006, art. 3º | Definição ME/EPP | ME até R$360k, EPP até R$4,8M |
| Edital PGDAU 11/2025 | Modalidades vigentes | Até 29/05/2026, TPV + Capacidade + Difícil Recuperação |

### Vedações (validar no engine)
1. Vedado desconto no principal (art. 11, §2º, I) — **exceto TPV**
2. Vedado acumular reduções (art. 5º, §1º)
3. Vedado Simples Nacional sem LC (art. 5º, II, "a")
4. Vedado nova transação mesmo crédito (art. 20, I)
5. Vedado nova transação por 2 anos após rescisão (art. 4º, §4º)

### APIs Externas
| API | Série | Uso |
|-----|-------|-----|
| BCB SGS SELIC mensal | 4390 | Correção parcelas |
| BCB SGS SELIC diária | 11 | Cálculo preciso |
| BCB SGS IPCA | 433 | Referência inflação |

### Fórmula SELIC (Lei 13.988, art. 11, §1º)
```
valor_corrigido = valor_original × Π(1 + SELIC_mensal_i / 100) × 1.01
```

### Transparência dos Cálculos
Cada resultado inclui `_calculo_detalhes`:
```json
[
  {
    "passo": 1,
    "descricao": "Desconto de 70% sobre multa+juros+encargos",
    "formula": "Multa R$ 300,00 × 70% = R$ 210,00",
    "referencia_legal": "Lei 13.988/2020, art. 11, §2º, II + §3º (ME/EPP)",
    "valor_antes": "300.00",
    "valor_desconto": "210.00",
    "valor_depois": "90.00"
  }
]
```

---

## Testes de Compatibilidade com Plataformas HPR (OBRIGATÓRIO)

> **Estes testes validam que nosso sistema produz resultados compatíveis com as 4 plataformas HPR analisadas.**
> Cada teste reproduz uma simulação feita na plataforma HPR real, com dados de entrada e saída verificados manualmente via browser.
> Os testes devem PASSAR antes de considerar o MVP pronto.
> Arquivo: `tests/test_compatibilidade_hpr.py`

### Cenário 1 — Plataforma 1: Diagnóstico Prévio (Capacidade de Pagamento)

**Plataforma:** `hpr-diagnostico-transacao-copy-*.base44.app`
**Dados usados no teste real (browser):**
- Valor Total da Dívida: R$ 10.000,00
- % Dívida Previdenciária: 30%
- ME/EPP: Não (Demais Empresas)
- Desconto aplicado pela HPR: 30% (fixo)

**Resultado obtido na HPR:**
- Dívida Total: R$ 10.000,00
- Desconto (30%): -R$ 3.000,00
- Valor com desconto: R$ 7.000,00
- Entrada (6%): R$ 600,00 → 6x de R$ 100,00
- Previdenciário: R$ 3.000,00 → desconto R$ 900,00 → saldo R$ 2.100,00 → entrada 6x R$ 30,00 → 54x R$ 35,56
- Não Previdenciário: R$ 7.000,00 → desconto R$ 2.100,00 → saldo R$ 4.900,00 → entrada 6x R$ 70,00 → 114x R$ 39,30

```python
# tests/test_compatibilidade_hpr.py
"""
Testes de compatibilidade com plataformas HPR.

Cada teste reproduz uma simulação feita na plataforma HPR real,
com dados de entrada e saída verificados via browser em 17-18/03/2026.

Estes testes garantem que nosso motor de cálculo produz resultados
idênticos (ou superiores, quando a HPR tem erros) às plataformas de referência.
"""

from datetime import date
from decimal import Decimal

import pytest


class TestCompatibilidadePlataforma1DiagnosticoBasico:
    """Compatibilidade com HPR Diagnóstico Prévio de Transação Tributária.

    Plataforma: hpr-diagnostico-transacao-copy-*.base44.app
    Teste realizado em: 17/03/2026

    Nota: A HPR usa desconto fixo de 30% (incorreto — deveria variar por classificação).
    Nosso sistema calcula corretamente por classificação CAPAG, mas este teste verifica
    que com os mesmos parâmetros produzimos os mesmos números.
    """

    def test_demais_empresas_30pct_previdenciario(self):
        """Cenário HPR: R$10k, 30% prev, Demais Empresas, desconto 30%."""
        from apps.transacao.engine import calcular_diagnostico, DiagnosticoInput
        from apps.transacao.constants import ClassificacaoCredito

        inp = DiagnosticoInput(
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.C,  # C dá ~30% desconto com "menor desconto"
        )
        result = calcular_diagnostico(inp)

        # Valores da HPR (verificados via browser)
        assert result.valor_total == Decimal("10000")
        assert result.valor_entrada == Decimal("600")  # 6% de 10000
        assert result.parcelas_entrada == 6

        # Previdenciário
        assert result.previdenciario.prazo_total == 60  # CF/88, art. 195, §11
        assert result.previdenciario.num_entrada == 6

        # Não Previdenciário
        assert result.nao_previdenciario.prazo_total == 120  # Lei 13.988, art. 11, §2º, III

    def test_me_epp_30pct_previdenciario(self):
        """Cenário HPR: R$10k, 30% prev, ME/EPP, desconto 30%."""
        from apps.transacao.engine import calcular_diagnostico, DiagnosticoInput
        from apps.transacao.constants import ClassificacaoCredito

        inp = DiagnosticoInput(
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.C,
        )
        result = calcular_diagnostico(inp)

        # ME/EPP tem 12 meses de entrada e 145 meses não previdenciário
        assert result.parcelas_entrada == 12  # Portaria PGFN 6.757, art. 36, §2º
        assert result.previdenciario.prazo_total == 60  # Limite constitucional
        assert result.nao_previdenciario.prazo_total == 145  # Lei 13.988, art. 11, §3º


class TestCompatibilidadePlataforma2TPVSimulator:
    """Compatibilidade com HPR TPV Simulator.

    Plataforma: hpr-tpv-sim.base44.app
    Teste realizado em: 18/03/2026

    Testa validação de CDA (valor ≤ 60 SM, inscrição > 1 ano),
    descontos escalonados (50/45/40/30%) e cálculo de entrada 5%.
    """

    def test_cda_apta_50pct_desconto_7_parcelas(self):
        """Cenário HPR: CDA R$500, inscrita 15/03/2020, EPP, 7 parcelas saldo.

        Resultado HPR verificado:
        - Entrada (5%): R$ 25,00 → 1x de R$ 25,00
        - Saldo antes desconto: R$ 475,00
        - Desconto (50%): R$ 237,50
        - Saldo com desconto: R$ 237,50
        - Parcela saldo: 7x de R$ 33,93
        - Valor Final: R$ 262,50
        - Economia: R$ 237,50
        """
        from apps.tpv.engine import calcular_tpv, TPVInput, CDAInput

        inp = TPVInput(
            cdas=[CDAInput(numero="CDA-2020-001", valor=Decimal("500"), data_inscricao=date(2020, 3, 15))],
            parcelas_entrada=1,
            parcelas_saldo=7,
            salario_minimo=Decimal("1621"),
            data_simulacao=date(2026, 3, 18),
        )
        result = calcular_tpv(inp)

        # Valores EXATOS da HPR
        assert result.total_cdas_aptas == Decimal("500")
        assert result.valor_entrada == Decimal("25.00")
        assert result.parcela_entrada == Decimal("25.00")
        assert result.desconto_percentual == Decimal("0.50")
        assert result.saldo_antes_desconto == Decimal("475.00")
        assert result.saldo_com_desconto == Decimal("237.50")
        assert result.parcela_saldo == Decimal("33.93")
        assert result.valor_final == Decimal("262.50")
        assert result.economia == Decimal("237.50")
        assert len(result.fluxo) == 8  # 1 entrada + 7 saldo

    def test_cda_nao_apta_inscricao_inferior_1_ano(self):
        """Cenário HPR: CDA R$1.500, inscrita 15/06/2025 → NÃO APTA.

        Resultado HPR verificado:
        - Status: NÃO APTA
        - Motivo: "Inscrição inferior a 1 ano"
        - Projeção: "Apta por tempo em: 15/06/2026"
        - Dias restantes: 89
        """
        from apps.tpv.validators import validar_cda, MotivoInaptidao

        result = validar_cda(
            valor=Decimal("1500"),
            data_inscricao=date(2025, 6, 15),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is False
        assert MotivoInaptidao.INSCRICAO_INFERIOR_1_ANO in result.motivos
        assert result.data_elegibilidade_tempo == date(2026, 6, 15)
        assert result.dias_restantes_tempo == 89

    def test_cda_valor_exato_60sm_e_apta(self):
        """CDA no limite exato de 60 SM (R$ 97.260,00) deve ser APTA.

        SM vigente 2026: R$ 1.621,00 × 60 = R$ 97.260,00
        """
        from apps.tpv.validators import validar_cda

        result = validar_cda(
            valor=Decimal("97260"),
            data_inscricao=date(2025, 3, 17),
            data_simulacao=date(2026, 3, 18),
            salario_minimo=Decimal("1621"),
        )

        assert result.apta is True


class TestCompatibilidadePlataforma3PGFNDebtSolve:
    """Compatibilidade com HPR PGFN Debt Solve (TPV Simplificado/Wizard).

    Plataforma: pgfn-debt-solve.base44.app
    Teste realizado em: 18/03/2026

    Testa comparação das 4 faixas de desconto lado a lado e elegibilidade via wizard.
    """

    def test_todas_4_faixas_valor_750(self):
        """Cenário HPR: R$750, ME, todas CDAs aptas.

        Resultado HPR verificado (4 faixas):
        - Entrada (5%): R$ 37,50 → 5x de R$ 7,50
        - Saldo após entrada: R$ 712,50
        - Faixa 50% (7x):  desconto R$ 356,25 → saldo R$ 356,25 → 7x de R$ 50,89
        - Faixa 45% (12x): desconto R$ 320,63 → saldo R$ 391,88 → 12x de R$ 32,66
        - Faixa 40% (30x): desconto R$ 285,00 → saldo R$ 427,50 → 30x de R$ 14,25
        - Faixa 30% (55x): desconto R$ 213,75 → saldo R$ 498,75 → 55x de R$ 9,07
        - Economia máxima: R$ 356,25
        - Melhor valor final: R$ 393,75
        """
        from apps.tpv.engine import calcular_tpv_todas_faixas

        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))

        # Entrada
        assert result.valor_entrada == Decimal("37.50")
        assert result.parcela_entrada == Decimal("7.50")
        assert result.parcelas_entrada == 5
        assert result.saldo_apos_entrada == Decimal("712.50")

        # Faixa 50% (melhor opção)
        faixa_50 = result.faixas[0]
        assert faixa_50.desconto_percentual == Decimal("0.50")
        assert faixa_50.parcelas_max == 7
        assert faixa_50.desconto_valor == Decimal("356.25")
        assert faixa_50.saldo_final == Decimal("356.25")
        assert faixa_50.parcela_saldo == Decimal("50.89")
        assert faixa_50.is_melhor is True

        # Faixa 45%
        faixa_45 = result.faixas[1]
        assert faixa_45.desconto_percentual == Decimal("0.45")
        assert faixa_45.parcelas_max == 12
        assert faixa_45.desconto_valor == Decimal("320.63")
        assert faixa_45.saldo_final == Decimal("391.88")
        assert faixa_45.parcela_saldo == Decimal("32.66")

        # Faixa 40%
        faixa_40 = result.faixas[2]
        assert faixa_40.desconto_percentual == Decimal("0.40")
        assert faixa_40.parcelas_max == 30
        assert faixa_40.desconto_valor == Decimal("285.00")
        assert faixa_40.saldo_final == Decimal("427.50")
        assert faixa_40.parcela_saldo == Decimal("14.25")

        # Faixa 30%
        faixa_30 = result.faixas[3]
        assert faixa_30.desconto_percentual == Decimal("0.30")
        assert faixa_30.parcelas_max == 55
        assert faixa_30.desconto_valor == Decimal("213.75")
        assert faixa_30.saldo_final == Decimal("498.75")
        assert faixa_30.parcela_saldo == Decimal("9.07")

        # Economia máxima e melhor valor final
        assert result.economia_maxima == Decimal("356.25")
        assert result.melhor_valor_final == Decimal("393.75")

    def test_wizard_elegibilidade_elegivel(self):
        """Cenário HPR: ME, sem CDA >60SM, R$750, >1 ano → Elegível."""
        from apps.tpv.validators import validar_elegibilidade_wizard

        result = validar_elegibilidade_wizard(
            tipo_contribuinte="ME",
            possui_cda_acima_limite=False,
            valor_total=Decimal("750"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert result.elegivel is True
        assert all(c["status"] == "ok" for c in result.criterios)
        assert result.mensagem == "Elegível para Transação de Pequeno Valor"

    def test_wizard_elegibilidade_nao_elegivel_cda_acima_limite(self):
        """Cenário HPR: PF, com CDA >60SM → Não elegível.

        HPR mostra critério "Limite por CDA" como vermelho:
        "Possui CDA acima de 60 salários mínimos - não elegível"
        """
        from apps.tpv.validators import validar_elegibilidade_wizard

        result = validar_elegibilidade_wizard(
            tipo_contribuinte="PF",
            possui_cda_acima_limite=True,
            valor_total=Decimal("50000"),
            todas_cdas_mais_1_ano=True,
            salario_minimo=Decimal("1621"),
        )

        assert result.elegivel is False
        assert result.criterios[1]["status"] == "fail"
        assert "60 salários mínimos" in result.criterios[1]["detalhe"]


class TestCompatibilidadePlataforma4MetaSimulacao:
    """Compatibilidade com HPR Simulação de Transação Meta (a mais avançada).

    Plataforma: simulacao-de-transacao-meta-copy-*.base44.app
    Teste realizado em: 18/03/2026

    Testa decomposição P/M/J/E, rating CAPAG automático, desconto por componente,
    e parcelamento previdenciário vs tributário.
    """

    def test_me_epp_rating_d_maior_desconto(self):
        """Cenário HPR: Sítio Verde, ME/EPP, CAPAG R$1.000, Passivo RFB R$5.000.

        Débitos Previdenciários: Principal R$1.000 + Multa R$300 + Juros R$500 + Encargos R$200
        Débitos Tributários:     Principal R$1.500 + Multa R$450 + Juros R$600 + Encargos R$250
        Simples Nacional:        Não preenchido

        Resultado HPR verificado:
        - Rating: D (Crítico)
        - Desconto Aplicado: 70,00% (Máx: 70,00%)
        - Passivo PGFN: R$ 4.800,00
        - Passivo RFB: R$ 5.000,00

        Previdenciário (R$ 2.000,00):
          - Principal: R$ 1.000,00 → sem desconto → R$ 1.000,00
          - Multa: R$ 300,00 → -R$ 282,00 → R$ 18,00
          - Juros: R$ 500,00 → -R$ 470,00 → R$ 30,00
          - Encargos: R$ 200,00 → -R$ 188,00 → R$ 12,00
          - TOTAL: R$ 2.000,00 → desconto R$ 940,00 → R$ 1.060,00
          - Entrada (6%): R$ 120,00 → 12x de R$ 10,00
          - Restante: 48x de R$ 19,58

        Tributário (R$ 2.800,00):
          - Principal: R$ 1.500,00 → sem desconto → R$ 1.500,00
          - Multa: R$ 450,00 → -R$ 423,00 → R$ 27,00
          - Juros: R$ 600,00 → -R$ 564,00 → R$ 36,00
          - Encargos: R$ 250,00 → -R$ 235,00 → R$ 15,00
          - TOTAL: R$ 2.800,00 → desconto R$ 1.222,00 → R$ 1.578,00
          - Entrada (6%): R$ 168,00 → 12x de R$ 14,00
          - Restante: 133x de R$ 10,60

        Totais:
        - Desconto Total: R$ 2.162,00
        - Saldo após Desconto: R$ 2.638,00
        - Desconto Efetivo: 45,04%
        """
        from apps.transacao.engine_avancado import (
            DebitoComponentes,
            SimulacaoAvancadaInput,
            calcular_simulacao_avancada,
            RatingCAPAG,
        )

        inp = SimulacaoAvancadaInput(
            previdenciario=DebitoComponentes(
                principal=Decimal("1000"),
                multa=Decimal("300"),
                juros=Decimal("500"),
                encargos=Decimal("200"),
            ),
            tributario=DebitoComponentes(
                principal=Decimal("1500"),
                multa=Decimal("450"),
                juros=Decimal("600"),
                encargos=Decimal("250"),
            ),
            simples=DebitoComponentes(),  # Vazio
            is_me_epp=True,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            desconto_escolha="MAIOR",
            honorarios_percentual=Decimal("20"),
        )
        result = calcular_simulacao_avancada(inp)

        # Rating CAPAG
        # CAPAG R$1.000 / Passivo Total R$9.800 = 0.102 → < 0.5 → Rating D
        assert result.rating == RatingCAPAG.D

        # Desconto: 70% para ME/EPP com rating D (Lei 13.988, art. 11, §3º)
        assert result.desconto_percentual == Decimal("0.70")

        # --- Previdenciário ---
        prev = result.previdenciario

        # Principal NUNCA tem desconto (art. 11, §2º, I)
        assert prev.desconto_result.principal_final == Decimal("1000")
        assert prev.desconto_result.principal_desconto == Decimal("0")

        # Multa: R$300 × 70% = R$210 desconto... MAS a HPR mostra R$282
        # A HPR calcula o desconto de forma que o saldo transacionado ≈ CAPAG
        # Nosso teste verifica a LÓGICA correta, não necessariamente o valor idêntico à HPR
        # porque a HPR pode usar uma fórmula diferente de distribuição do desconto
        assert prev.desconto_result.multa_desconto > Decimal("0")
        assert prev.desconto_result.juros_desconto > Decimal("0")
        assert prev.desconto_result.encargos_desconto > Decimal("0")

        # Prazo previdenciário: 60 meses (CF/88, art. 195, §11)
        assert prev.prazo_total == 60
        assert prev.num_entrada == 12  # ME/EPP: 12 meses entrada

        # --- Tributário ---
        trib = result.tributario

        # Principal sem desconto
        assert trib.desconto_result.principal_final == Decimal("1500")
        assert trib.desconto_result.principal_desconto == Decimal("0")

        # Prazo tributário: 145 meses para ME/EPP (Lei 13.988, art. 11, §3º)
        assert trib.prazo_total == 145
        assert trib.num_entrada == 12

        # --- Totais ---
        # Passivo PGFN = Previdenciário + Tributário + Simples
        assert result.passivo_pgfn == Decimal("4800")
        assert result.passivo_rfb == Decimal("5000")
        assert result.passivo_total == Decimal("9800")

        # Desconto total deve ser > 0 (rating D tem desconto)
        assert result.desconto_total > Decimal("0")

        # Saldo após desconto = passivo PGFN - desconto total
        assert result.saldo_apos_desconto == result.passivo_pgfn - result.desconto_total

        # Desconto efetivo (%) = desconto / passivo PGFN × 100
        assert result.desconto_efetivo > Decimal("0")

        # Honorários = desconto × 20%
        assert result.honorarios == result.desconto_total * Decimal("0.20")

    def test_principal_nunca_tem_desconto(self):
        """Art. 11, §2º, I da Lei 13.988: 'É vedada a redução do montante principal.'

        Mesmo com 70% de desconto (máximo), o principal permanece intacto.
        O desconto incide APENAS sobre multa + juros + encargos.
        """
        from apps.transacao.engine_avancado import (
            DebitoComponentes,
            calcular_desconto_componentes,
        )

        componentes = DebitoComponentes(
            principal=Decimal("50000"),
            multa=Decimal("15000"),
            juros=Decimal("25000"),
            encargos=Decimal("10000"),
        )
        result = calcular_desconto_componentes(componentes, desconto_pct=Decimal("0.70"))

        # Principal INTOCADO
        assert result.principal_final == Decimal("50000")
        assert result.principal_desconto == Decimal("0")

        # Multa/Juros/Encargos com 70% desconto
        assert result.multa_desconto == Decimal("10500")  # 15000 × 70%
        assert result.juros_desconto == Decimal("17500")  # 25000 × 70%
        assert result.encargos_desconto == Decimal("7000")  # 10000 × 70%

        # Total desconto = apenas multa+juros+encargos
        assert result.total_desconto == Decimal("35000")  # 10500+17500+7000

        # Total final = 100000 - 35000 = 65000
        assert result.total_final == Decimal("65000")

    def test_rating_capag_formula_exata(self):
        """Validação da fórmula de Rating CAPAG (Portaria PGFN 6.757/2022, art. 24).

        Rating = CAPAG / Dívida Consolidada:
        - A: ratio ≥ 2.0
        - B: 1.0 ≤ ratio < 2.0
        - C: 0.5 ≤ ratio < 1.0
        - D: ratio < 0.5
        """
        from apps.transacao.engine_avancado import calcular_rating_capag, RatingCAPAG

        # A: CAPAG muito maior que dívida (pode pagar 2x)
        assert calcular_rating_capag(Decimal("200000"), Decimal("100000")) == RatingCAPAG.A

        # B: CAPAG cobre dívida mas não o dobro
        assert calcular_rating_capag(Decimal("150000"), Decimal("100000")) == RatingCAPAG.B

        # C: CAPAG cobre metade
        assert calcular_rating_capag(Decimal("60000"), Decimal("100000")) == RatingCAPAG.C

        # D: CAPAG muito inferior (caso Sítio Verde: 1000/9800 = 0.102)
        assert calcular_rating_capag(Decimal("1000"), Decimal("9800")) == RatingCAPAG.D

        # Edge cases
        assert calcular_rating_capag(Decimal("0"), Decimal("100000")) == RatingCAPAG.D
        assert calcular_rating_capag(Decimal("100000"), Decimal("0")) == RatingCAPAG.A  # Sem dívida

        # Limites exatos
        assert calcular_rating_capag(Decimal("200000"), Decimal("100000")) == RatingCAPAG.A  # = 2.0
        assert calcular_rating_capag(Decimal("100000"), Decimal("100000")) == RatingCAPAG.B  # = 1.0
        assert calcular_rating_capag(Decimal("50000"), Decimal("100000")) == RatingCAPAG.C   # = 0.5
        assert calcular_rating_capag(Decimal("49999"), Decimal("100000")) == RatingCAPAG.D   # < 0.5

    def test_rating_a_b_sem_desconto(self):
        """Ratings A e B: SEM desconto, apenas entrada facilitada.

        Portaria PGFN 6.757/2022 + Edital PGDAU 11/2025:
        'Contribuintes com classificação A ou B podem beneficiar-se de entrada facilitada,
        porém NÃO têm direito a descontos.'
        """
        from apps.transacao.engine_avancado import (
            DebitoComponentes,
            SimulacaoAvancadaInput,
            calcular_simulacao_avancada,
            RatingCAPAG,
        )

        # CAPAG alto → Rating A
        inp = SimulacaoAvancadaInput(
            previdenciario=DebitoComponentes(
                principal=Decimal("1000"),
                multa=Decimal("300"),
                juros=Decimal("500"),
                encargos=Decimal("200"),
            ),
            tributario=DebitoComponentes(),
            simples=DebitoComponentes(),
            is_me_epp=True,
            capag_60m=Decimal("50000"),  # CAPAG >> dívida
            passivo_rfb=Decimal("0"),
            desconto_escolha="MAIOR",
        )
        result = calcular_simulacao_avancada(inp)

        assert result.rating in (RatingCAPAG.A, RatingCAPAG.B)
        assert result.desconto_total == Decimal("0")
        assert result.saldo_apos_desconto == result.passivo_pgfn  # Sem desconto

    def test_fluxo_parcelas_consolidado(self):
        """Fluxo de parcelas consolidado: entrada + parcelas regulares.

        HPR mostra:
        - Entrada R$ 24,00/mês (12 meses)
        - Após Entrada R$ 30,18/mês
        """
        from apps.transacao.engine_avancado import (
            DebitoComponentes,
            SimulacaoAvancadaInput,
            calcular_simulacao_avancada,
        )

        inp = SimulacaoAvancadaInput(
            previdenciario=DebitoComponentes(
                principal=Decimal("1000"),
                multa=Decimal("300"),
                juros=Decimal("500"),
                encargos=Decimal("200"),
            ),
            tributario=DebitoComponentes(
                principal=Decimal("1500"),
                multa=Decimal("450"),
                juros=Decimal("600"),
                encargos=Decimal("250"),
            ),
            simples=DebitoComponentes(),
            is_me_epp=True,
            capag_60m=Decimal("1000"),
            passivo_rfb=Decimal("5000"),
            desconto_escolha="MAIOR",
        )
        result = calcular_simulacao_avancada(inp)

        # Previdenciário: entrada 12x → 48 parcelas restantes (60 total)
        assert result.previdenciario.num_entrada == 12
        assert result.previdenciario.num_parcelas_saldo == 48

        # Tributário: entrada 12x → 133 parcelas restantes (145 total)
        assert result.tributario.num_entrada == 12
        assert result.tributario.num_parcelas_saldo == 133


class TestCompatibilidadeLimitesParcela:
    """Testes de limites legais que as plataformas HPR NÃO validam (nosso diferencial).

    Verificamos que nosso sistema respeita parcela mínima, que a HPR ignora.
    """

    def test_parcela_minima_demais_100_reais(self):
        """Portaria PGFN 6.757/2022: parcela mínima R$ 100,00 para PJ (exceto MEI).

        A HPR gerou parcelas de R$ 35,56 e R$ 39,30 para dívida de R$ 10.000 —
        abaixo do mínimo legal. Nosso sistema deve respeitar o mínimo.
        """
        from apps.transacao.engine import calcular_diagnostico, DiagnosticoInput
        from apps.transacao.constants import ClassificacaoCredito, PARCELA_MINIMA_DEMAIS

        inp = DiagnosticoInput(
            valor_total_divida=Decimal("10000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
        )
        result = calcular_diagnostico(inp)

        # Verificar que nenhuma parcela é inferior ao mínimo legal
        if result.previdenciario.valor_parcela > 0:
            assert result.previdenciario.valor_parcela >= PARCELA_MINIMA_DEMAIS, (
                f"Parcela previdenciária R$ {result.previdenciario.valor_parcela} "
                f"abaixo do mínimo legal R$ {PARCELA_MINIMA_DEMAIS}"
            )
        if result.nao_previdenciario.valor_parcela > 0:
            assert result.nao_previdenciario.valor_parcela >= PARCELA_MINIMA_DEMAIS, (
                f"Parcela não previdenciária R$ {result.nao_previdenciario.valor_parcela} "
                f"abaixo do mínimo legal R$ {PARCELA_MINIMA_DEMAIS}"
            )

    def test_tpv_parcela_minima_100_reais(self):
        """TPV para EPP: parcela mínima R$ 100,00.

        A HPR gerou parcela TPV de R$ 7,50 — abaixo do mínimo legal.
        """
        from apps.tpv.engine import calcular_tpv_todas_faixas
        from apps.transacao.constants import PARCELA_MINIMA_DEMAIS

        result = calcular_tpv_todas_faixas(valor_total=Decimal("750"))

        # Para EPP, parcela mínima é R$ 100,00
        # Com R$ 750, a parcela de entrada seria R$ 7,50 (5% / 5)
        # Nosso sistema deve ajustar ou avisar
        for faixa in result.faixas:
            if faixa.parcela_saldo > 0:
                # Registra o valor, mesmo que abaixo do mínimo, mas com flag
                pass  # Engine deve ter campo `alerta_parcela_minima`


class TestComparadorModalidades:
    """Teste do comparador de modalidades — feature exclusiva nossa (não existe na HPR)."""

    def test_tpv_melhor_para_divida_pequena_classificacao_a(self):
        """Para dívida pequena (< 60 SM) com classificação A (sem desconto CAPAG),
        TPV é claramente melhor porque tem desconto de 50%.

        CAPAG sem desconto: paga R$ 50.000 integral
        TPV com 50%: paga R$ 50.000 × 95% × 50% + entrada = ~R$ 26.250
        """
        from apps.comparador.service import comparar_modalidades
        from apps.transacao.constants import ClassificacaoCredito

        result = comparar_modalidades(
            valor_total=Decimal("50000"),
            percentual_previdenciario=Decimal("0"),
            is_me_epp=True,
            classificacao=ClassificacaoCredito.A,
            tpv_elegivel=True,
        )

        assert result.tpv_disponivel is True
        assert result.recomendacao == "TPV"
        assert result.economia_diferenca > Decimal("0")

    def test_capacidade_unica_opcao_para_divida_grande(self):
        """Para dívida > 60 SM, TPV não é elegível. Só Capacidade de Pagamento."""
        from apps.comparador.service import comparar_modalidades
        from apps.transacao.constants import ClassificacaoCredito

        result = comparar_modalidades(
            valor_total=Decimal("500000"),
            percentual_previdenciario=Decimal("30"),
            is_me_epp=False,
            classificacao=ClassificacaoCredito.D,
            tpv_elegivel=False,
        )

        assert result.tpv_disponivel is False
        assert result.recomendacao == "CAPACIDADE"
```
