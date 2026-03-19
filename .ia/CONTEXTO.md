# Contexto do Projeto — WAS Contabil

## O que e este projeto?

Plataforma web multi-tenant para escritorios de contabilidade e advocacia tributaria simularem transacoes tributarias federais (PGFN). Calcula descontos, parcelamentos e gera relatorios PDF com transparencia total dos calculos.

## Publico-alvo

Contadores e advogados tributaristas que negociam dividas federais de seus clientes junto a PGFN (Procuradoria-Geral da Fazenda Nacional).

## Dominio de negocio

### Transacao tributaria

E um programa do governo federal que permite ao contribuinte devedor negociar suas dividas com descontos e parcelamentos. Existem varias modalidades:

- **Capacidade de Pagamento (CAPAG):** O desconto depende da capacidade de pagamento do contribuinte (rating A/B/C/D). Desconto so sobre multa/juros/encargos, NUNCA sobre o principal.
- **Transacao de Pequeno Valor (TPV):** Para dividas ate 60 salarios minimos por CDA, com descontos de 30-50% sobre TODO o saldo (inclusive principal — excecao legal).

### Termos importantes

- **CDA:** Certidao de Divida Ativa — documento que formaliza a inscricao do debito
- **CAPAG:** Capacidade de Pagamento — estimativa da PGFN de quanto o contribuinte pode pagar em 60 meses
- **Rating:** Classificacao A (alta recuperacao) a D (irrecuperavel) baseada na relacao CAPAG/divida
- **P/M/J/E:** Principal, Multa, Juros, Encargos — decomposicao da divida
- **SM:** Salario Minimo (R$ 1.621 em 2026)
- **PGFN:** Procuradoria-Geral da Fazenda Nacional
- **RFB:** Receita Federal do Brasil
- **Regularize:** Portal da PGFN onde contribuintes acessam suas dividas

## Origem do projeto

Construido como replica melhorada de 4 plataformas comerciais da HPR Consultoria. Analises detalhadas das plataformas estao em `docs/analise-plataformas/`. A formula de calculo foi obtida por engenharia reversa e validada com testes de compatibilidade (`tests/test_compatibilidade_hpr.py`).
