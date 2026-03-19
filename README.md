# ⚖️ WAS Contabil

> Plataforma de diagnostico e simulacao de **transacao tributaria federal** (PGFN) para escritorios de contabilidade e advocacia tributaria.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2_LTS-green.svg)](https://djangoproject.com)
[![Tests](https://img.shields.io/badge/Tests-532_passing-brightgreen.svg)](#-testes)
[![Coverage](https://img.shields.io/badge/Coverage-99%25-brightgreen.svg)](#-testes)

---

## 🎯 O que faz?

Simula cenarios de negociacao de dividas federais com base na legislacao vigente, gerando relatorios com **total transparencia dos calculos** e referencias legais em cada passo.

### 📋 Modulos

| | Modulo | O que faz |
|---|--------|-----------|
| 🏛️ | **Simulacao CAPAG** | Decomposicao Principal/Multa/Juros/Encargos, rating automatico (A/B/C/D), 3 categorias de debitos, honorarios de exito |
| 📄 | **TPV Avancado** | Transacao de Pequeno Valor com validacao por CDA individual, importacao CSV/Excel, elegibilidade futura |
| 🧙 | **TPV Wizard** | Checklist de elegibilidade em tempo real + comparacao das 4 faixas de desconto lado a lado |
| ⚖️ | **Comparador** | Compara TPV vs Capacidade de Pagamento e recomenda a melhor opcao |
| 📈 | **Indices BCB** | SELIC e IPCA em tempo real via API do Banco Central para correcao monetaria |
| 🏢 | **Empresas** | Cadastro com busca, honorarios, isolamento multi-tenant por escritorio |
| 📑 | **PDF** | Relatorios A4 (resumido + completo) com rating, tabelas e fluxo de parcelas |

---

## 🛠️ Stack

| | Tecnologia | Versao |
|---|-----------|--------|
| 🐍 | Python | 3.12 |
| 🌿 | Django + DRF | 5.2 LTS + 3.16 |
| 🐘 | PostgreSQL | 17 |
| ⚡ | Redis + django-rq | 7 + 4.0 |
| 🔐 | django-allauth | 65.x (Google + Microsoft OAuth) |
| 🎨 | Tailwind + HTMX + Alpine.js | 3 + 2 + 3 |
| 📄 | WeasyPrint | 68.x |
| 🧪 | pytest + factory-boy | 9.0 + 3.3 |
| ✨ | Black + isort + flake8 | PEP 8 rigoroso |
| 🐳 | Docker + docker-compose | - |

---

## 🚀 Inicio rapido

### Pre-requisitos

- 🐳 Docker e docker-compose
- 🐍 Python 3.12+

### ⚡ Setup em 3 comandos

```bash
git clone git@github.com:williamroot/was-contabil.git
cd was-contabil
cp .env.example .env
make setup
```

Pronto! Acesse **http://localhost:8000**

```
📧 Login: admin@wascontabil.com
🔑 Senha: WAS@2026!
```

### 🔧 Comandos do dia a dia

```bash
make run           # 🚀 Sobe postgres + redis + servidor
make test          # 🧪 Roda todos os 532 testes
make lint          # ✨ Formata + verifica codigo
make quality       # 🏆 Lint + check + test (tudo junto)
make shell         # 🐚 Django shell interativo
make worker        # ⚙️  Worker RQ (fila de tarefas)
make sync-indices  # 📈 Sincroniza SELIC/IPCA do BCB
```

> 💡 Digite `make` para ver todos os comandos disponiveis.

### 🧪 Testes

```bash
make test              # Roda tudo
make test-v            # Com verbose
make test-cov          # Com cobertura (99%)
make test-compat       # Testes de compatibilidade HPR
make test-app APP=tpv  # Testes de um app especifico
```

---

## 🏗️ Arquitetura

### Camadas (SOLID)

```
📨 View (HTTP)
  └─ 📋 Serializer (validacao)
       └─ ⚙️  Service (orquestracao)
            └─ 🧮 Engine (calculo puro — sem Django, sem I/O)
                 └─ referencia → 📜 Constants (leis + portarias)

  💾 Model (persistencia — UUID PK, multi-tenant FK)
```

| Camada | Responsabilidade | Regra de ouro |
|--------|-----------------|---------------|
| 📨 **View** | Receber HTTP, delegar, responder | Fina — zero logica de negocio |
| 📋 **Serializer** | Validar input, serializar output | Validacao rigorosa no backend |
| ⚙️ **Service** | Orquestrar engine + persistir | Unico ponto de acesso |
| 🧮 **Engine** | Calculo puro, Decimal, dataclasses | Python puro — sem Django, sem banco |
| 💾 **Model** | Schema + managers | UUID PK, FK organization |
| 📜 **Constants** | Constantes legais | Cada valor com artigo/lei citado |

### 🏢 Multi-tenant

Cada escritorio e uma **organizacao** isolada. Dados nunca vazam entre orgs.

```
👑 Superuser
  └─ ✉️  Convida dono do escritorio
       └─ 🏢 Dono cria conta + Organizacao
            └─ ✉️  Dono convida membros
                 └─ 👤 Membro entra na mesma org
```

### 🔍 Transparencia dos calculos

Cada simulacao mostra o **passo a passo** com formula e referencia legal:

```json
{
  "passo": 1,
  "descricao": "Desconto de 70% sobre multa+juros+encargos",
  "formula": "Multa R$ 300 x 70% = R$ 210",
  "referencia_legal": "Lei 13.988/2020, art. 11, par.3 (ME/EPP)"
}
```

---

## 📜 Base legal

| | Legislacao | Assunto |
|---|-----------|---------|
| ⚖️ | Lei 13.988/2020 | Transacao tributaria federal |
| 📝 | Lei 14.375/2022 | Ampliacao de descontos e prazos |
| 📊 | Portaria PGFN 6.757/2022 | CAPAG, classificacao A/B/C/D |
| 🏛️ | CF/88, art. 195, par.11 | Limite 60 meses previdenciario |
| 🏪 | LC 123/2006 | Definicao ME/EPP |
| 📋 | Edital PGDAU 11/2025 | Modalidades ate 29/05/2026 |

### Regras principais

- 🔴 **Principal NUNCA tem desconto** (art. 11, par.2, I)
- 📉 Desconto maximo: 65% (geral) / 70% (ME/EPP)
- ⏱️ Previdenciario: max 60 meses | Nao previdenciario: 120/145 meses
- 💰 Entrada: 6% em 6 parcelas (geral) / 12 parcelas (ME/EPP)
- 📄 TPV: entrada 5%, descontos 50/45/40/30%, limite 60 SM por CDA
- 📈 Correcao SELIC: `valor x prod(1 + SELIC/100) x 1.01`
- 🏷️ Rating CAPAG: A (>= 2x), B (>= 1x), C (>= 0.5x), D (< 0.5x)

### Metodos de desconto

| Metodo | Como funciona | Quando usar |
|--------|--------------|-------------|
| 🎯 **CAPAG** (padrao) | Desconta 94% de M+J+E (preserva 6% entrada) | Maximiza desconto |
| 📐 **PERCENTUAL** | Aplica % fixo sobre cada componente | Mais conservador |

---

## 🔌 API REST

Preparada para frontend Vue.js ou qualquer framework.

### Endpoints

#### 🏛️ Transacao (Capacidade de Pagamento)
```
POST   /api/v1/transacao/simular/basico/       Diagnostico previo
POST   /api/v1/transacao/simular/avancado/      CAPAG com P/M/J/E
GET    /api/v1/transacao/historico/              Historico
GET    /api/v1/transacao/<uuid>/                 Detalhe
```

#### 📄 TPV (Pequeno Valor)
```
POST   /api/v1/tpv/simular/                     Simulacao por CDA
POST   /api/v1/tpv/wizard/                      Wizard + 4 faixas
POST   /api/v1/tpv/importar/                    Importar CDAs (CSV/Excel)
GET    /api/v1/tpv/historico/                    Historico
```

#### ⚖️ Comparador / 📈 Indices / 🏢 Empresas
```
POST   /api/v1/comparador/comparar/             TPV vs Capacidade
GET    /api/v1/indices/selic/ultimos/            Ultimos N indices
GET    /api/v1/indices/selic/acumulada/          SELIC acumulada
GET    /api/v1/empresas/                         Listar (com busca)
POST   /api/v1/empresas/                         Criar
PUT    /api/v1/empresas/<uuid>/                  Atualizar
DELETE /api/v1/empresas/<uuid>/                  Excluir
```

#### 📑 PDF
```
GET    /pdf/diagnostico/<uuid>/                  PDF diagnostico
GET    /pdf/simulacao-avancada/<uuid>/           PDF (?modo=resumido|completo)
GET    /pdf/tpv/<uuid>/                          PDF TPV
```

> 🔐 Autenticacao via sessao + OAuth. Rate limit: 20/min (anon), 120/min (auth).

---

## 🧪 Testes

```
✅ 532 testes | 📊 99% cobertura | ⚡ 5.9s
```

| | Categoria | Testes |
|---|-----------|--------|
| 🧮 | Engine transacao | 143 |
| 📄 | Engine TPV | 67 |
| 📋 | Serializers | 83 |
| 🔌 | Views/API | 37 |
| 💾 | Models | 36 |
| 📑 | PDF | 38 |
| 📥 | Importadores | 20 |
| 📈 | Indices BCB | 32 |
| ⚖️ | Comparador | 14 |
| 🏢 | Core | 23 |
| 🏢 | Empresas | 25 |
| 🎯 | Compatibilidade HPR | 17 |

### Testes de compatibilidade

Os testes em `tests/test_compatibilidade_hpr.py` reproduzem simulacoes das plataformas HPR reais e garantem resultados identicos:

- ✅ Plataforma 1: Diagnostico previo (R$10k, 30% prev)
- ✅ Plataforma 2: TPV Simulator (CDA R$500, 50% desconto)
- ✅ Plataforma 3: PGFN Debt Solve (R$750, 4 faixas exatas)
- ✅ Plataforma 4: Meta Simulacao (CAPAG Sitio Verde, Rating D, P/M/J/E)

---

## 🔒 Seguranca

| | Medida | Detalhe |
|---|--------|---------|
| ⏱️ | Sessao maxima | 24 horas |
| 🍪 | Cookies | httponly, secure, samesite=Lax |
| 🔒 | HSTS | 1 ano com preload |
| 🛡️ | CSRF | Ativo em todas as requisicoes |
| 🚦 | Rate limiting | 20/min anon, 120/min auth |
| 🏢 | Multi-tenant | Isolamento via FK + middleware |
| 🔑 | Primary keys | UUID v4 (sem IDs sequenciais) |
| 🚫 | Browsable API | Desabilitada em producao |
| 👮 | django-rq | Dashboard protegido (staff only) |
| 🔐 | Passwords | 4 validators (similarity, length, common, numeric) |

---

## 📁 Estrutura

```
was-contabil/
├── 📦 config/                    Settings (base/local/test/production)
├── 📂 apps/
│   ├── 🏢 core/                  Multi-tenant (Org, Membership, Invitation)
│   ├── 🏪 empresas/              Cadastro (CRUD + honorarios)
│   ├── 🏛️ transacao/             Simulacao CAPAG (basico + avancado)
│   ├── 📄 tpv/                   Pequeno Valor (CDAs + wizard)
│   ├── 📈 indices/               SELIC/IPCA (API BCB)
│   ├── ⚖️ comparador/            TPV vs Capacidade
│   └── 📑 pdf/                   Geracao PDF (WeasyPrint)
├── 🎨 templates/                 Tailwind + HTMX + Alpine.js
├── 📂 static/                    CSS + JS
├── 🧪 tests/                     Compatibilidade HPR
├── 📂 docs/                      Analises + planos
├── 🤖 .ia/                       Documentacao para agents AI
├── 🐳 Dockerfile
├── 🐳 docker-compose.yml
├── 📋 Makefile                   Atalhos (make help)
└── 📖 README.md
```

---

## 📄 Licenca

Software proprietario. Uso exclusivo autorizado.

**WAS Contabil** — Simulador de Transacao Tributaria
