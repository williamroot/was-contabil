# Arquitetura Tecnica

## Stack

- Python 3.12, Django 5.2 LTS, DRF 3.16
- PostgreSQL 17, Redis 7, django-rq 4.0
- django-allauth (OAuth Google/Microsoft)
- Tailwind CSS 3 + HTMX 2 + Alpine.js 3
- WeasyPrint (PDF), openpyxl (Excel)
- pytest + factory-boy (testes)
- Black + isort + flake8 (qualidade)

## Padrao de camadas (OBRIGATORIO)

```
View → Serializer → Service → Engine → Constants
                        ↓
                      Model
```

- **View:** Fina. Recebe HTTP, delega ao service, retorna response. ZERO logica.
- **Serializer:** Valida input do DRF. Nunca chama engine diretamente.
- **Service:** Orquestra engine + persistencia. Unico ponto de acesso.
- **Engine:** Calculo PURO. Sem Django, sem I/O, sem banco. Apenas Decimal + dataclasses.
- **Model:** Schema do banco. UUID PK. FK organization para multi-tenant.
- **Constants:** Constantes legais com referencia ao artigo/lei.

## Multi-tenant

Isolamento por FK `organization_id` em todos os models de negocio.

- `OrganizationMiddleware` seta `request.organization` automaticamente.
- `OrgQuerySetMixin` filtra querysets por org. Retorna `qs.none()` se org e None.
- `OrgCreateMixin` seta org ao criar. IGNORA qualquer org_id do payload.
- Superuser cria convite → dono cria org → dono convida membros.

## Apps

| App | Responsabilidade |
|-----|-----------------|
| `core` | Organization, Membership, Invitation, middleware, mixins, UUIDModel |
| `empresas` | CRUD empresas com busca, honorarios, isolamento |
| `transacao` | Engines de calculo (basico + avancado P/M/J/E + CAPAG) |
| `tpv` | TPV (CDAs, validacao, wizard, importacao CSV/Excel) |
| `indices` | Client BCB, sync SELIC/IPCA, correcao monetaria |
| `comparador` | Compara TPV vs Capacidade de Pagamento |
| `pdf` | Geracao PDF via WeasyPrint + Django templates |

## Metodo de desconto

Dois metodos disponiveis (usuario escolhe, padrao = CAPAG):

- **CAPAG:** Desconta M+J+E × 94% (preserva 6% entrada). Compativel com HPR.
- **PERCENTUAL:** Aplica % fixo (65%/70%) sobre cada componente. Mais conservador.

## Banco de dados

- TODOS os models herdam de `UUIDModel` (UUID v4 como PK)
- NUNCA usar AutoField/BigAutoField nos models do projeto
- URLs usam `<uuid:pk>`, nunca `<int:pk>`

## APIs externas

- BCB SGS (series 4390, 11, 433): SELIC e IPCA em tempo real
- Endpoint: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json`
