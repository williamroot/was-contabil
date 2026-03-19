# Regras do Projeto

## Codigo Python

- **PEP 8 rigoroso** via Black (line-length=120) + isort + flake8
- **snake_case** para funcoes/variaveis, **PascalCase** para classes, **UPPER_CASE** para constantes
- **Decimal** para TODOS os valores financeiros. NUNCA float.
- **Type hints** em todas as funcoes publicas
- **Docstrings Google-style** com referencia legal em funcoes de calculo
- Rodar `black . && isort . && flake8 apps/ config/` ANTES de cada commit
- NUNCA usar `--no-verify` nos commits

## Models

- **TODOS herdam de UUIDModel** (apps.core.models). NUNCA AutoField.
- **FK organization** em todos os models de negocio (multi-tenant)
- URLs com `<uuid:pk>`, NUNCA `<int:pk>`
- Campos `created_at` (auto_now_add) e `updated_at` (auto_now) obrigatorios

## Seguranca

- Sessao maxima 24h (SESSION_COOKIE_AGE=86400)
- NUNCA retornar queryset sem filtro de organization
- NUNCA aceitar organization_id ou user_id do payload do cliente
- CSRF sempre ativo. Rate limiting nos endpoints DRF.
- NUNCA commitar secrets, .env, credenciais.json

## Testes

- **TDD rigoroso:** teste primeiro → ver falhar → implementar → ver passar
- Testes sao codigo de producao — mesma qualidade (Black, docstrings)
- `make test` deve sempre passar antes de qualquer commit
- Edge cases obrigatorios: valor zero, limites exatos, formatos brasileiros

## Engines de calculo

- Python PURO — sem Django, sem I/O, sem banco
- Retornar `calculo_detalhes` com passo a passo e referencia legal
- Principal NUNCA tem desconto (art. 11, par.2, I da Lei 13.988)

## Commits

- NUNCA mencionar ferramentas de IA nos commits
- Mensagens descritivas em portugues, formato conventional commits (feat/fix/refactor)
- Um commit por feature logica, nao por arquivo

## Frontend

- Mobile-first: classes base para mobile, sm:/md:/lg: para desktop
- HTMX para interacoes server-side, Alpine.js para client-side
- NUNCA larguras fixas em pixels — usar w-full, max-w-*, flex, grid
- Transicoes suaves, loading states com hx-indicator
