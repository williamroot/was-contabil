# Base Legal — Referencia Rapida

## Legislacao principal

| Lei/Portaria | Artigos-chave | O que define |
|-------------|--------------|-------------|
| Lei 13.988/2020, art. 11, §2º, I | **Principal NUNCA tem desconto** | Vedacao expressa |
| Lei 13.988/2020, art. 11, §2º, II | Desconto max **65%** (geral) | Limite sobre valor total |
| Lei 13.988/2020, art. 11, §3º | Desconto max **70%** (ME/EPP/PF) | Limite diferenciado |
| Lei 13.988/2020, art. 11, §2º, III | Prazo max **120 meses** (geral) | Parcelamento |
| Lei 13.988/2020, art. 11, §3º | Prazo max **145 meses** (ME/EPP) | Parcelamento diferenciado |
| Lei 13.988/2020, art. 11, §1º | SELIC + 1% no mes do pagamento | Correcao das parcelas |
| CF/88, art. 195, §11 | **60 meses** max previdenciario | Limite constitucional |
| Portaria PGFN 6.757/2022, art. 24 | Rating A/B/C/D | CAPAG / Divida |
| Portaria PGFN 6.757/2022, art. 36 | Entrada **6%** em 6/12 parcelas | Entrada obrigatoria |
| Edital PGDAU 11/2025 | TPV: 60 SM, 1 ano, 50/45/40/30% | Modalidade vigente |

## Rating CAPAG (Portaria PGFN 6.757/2022, art. 24)

```
A: CAPAG >= 2x divida  → SEM desconto
B: CAPAG >= 1x divida  → SEM desconto
C: CAPAG >= 0.5x divida → Desconto ate 65%/70%
D: CAPAG < 0.5x divida  → Desconto ate 65%/70%
```

## Criterios objetivos para Rating D (art. 25)

1. Inscrito ha > 15 anos sem garantia
2. Suspenso judicialmente ha > 10 anos
3. Falido / recuperacao judicial / liquidacao
4. CNPJ baixado ou inapto
5. PF com indicativo de obito
6. Execucao fiscal arquivada ha > 3 anos

## TPV — Transacao de Pequeno Valor

- Elegivel: PF, ME, EPP
- CDA <= 60 SM e inscrita ha > 1 ano
- Entrada: 5% em ate 5 parcelas
- Desconto sobre TODO o saldo (inclusive principal — excecao legal)
- Faixas: 50% (7x), 45% (12x), 40% (30x), 30% (55x)

## Formula SELIC

```
valor_corrigido = valor × prod(1 + SELIC_mensal/100) × 1.01
```

## Formula desconto metodo CAPAG (engenharia reversa HPR)

```
desconto = M+J+E × (1 - ENTRADA_PERCENTUAL) = M+J+E × 94%
```
O contribuinte paga: Principal (intacto) + 6% de M+J+E como entrada.
