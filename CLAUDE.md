# Instrucoes para AI Agents

## Contextualizacao obrigatoria

Antes de qualquer tarefa, leia os arquivos em `.ia/` nesta ordem:

1. `.ia/CONTEXTO.md` — O que e o projeto, dominio de negocio, termos
2. `.ia/ARQUITETURA.md` — Stack, camadas, multi-tenant, apps
3. `.ia/REGRAS.md` — Padrao de codigo, seguranca, testes, commits
4. `.ia/BASE_LEGAL.md` — Legislacao, formulas, rating CAPAG

## Regras criticas

- **PEP 8 + Black** (line-length=120). Rodar `make lint` antes de cada commit.
- **TDD rigoroso**: teste primeiro, ver falhar, implementar, ver passar.
- **Decimal** para valores financeiros. NUNCA float.
- **UUID** em todos os models (herdar de `apps.core.models.UUIDModel`).
- **Multi-tenant**: NUNCA retornar queryset sem filtro de organization.
- **Engine puro**: sem Django, sem I/O. View → Serializer → Service → Engine.
- **Commits**: NUNCA mencionar ferramentas de IA. Formato conventional commits em portugues.
- **Transparencia**: cada calculo inclui `calculo_detalhes` com formula + referencia legal.
- **Principal NUNCA tem desconto** (Lei 13.988/2020, art. 11, par.2, I).

## Comandos uteis

```bash
make test          # Rodar todos os testes (532, 99% cobertura)
make lint          # Formatar + verificar codigo
make quality       # Lint + check + test (tudo junto)
make run           # Subir servidor local
make shell         # Django shell
make test-app APP=transacao  # Testar app especifico
```

## Estrutura dos apps

Cada app segue a mesma estrutura:
```
apps/<nome>/
  models.py       — Models Django (UUIDModel, FK org)
  constants.py    — Constantes legais com refs
  engine.py       — Calculo puro (sem Django)
  serializers.py  — DRF serializers
  views.py        — Views API (DRF)
  views_pages.py  — Views template (HTMX)
  urls.py         — URLs API
  urls_pages.py   — URLs paginas
  tests/          — Testes TDD
```
