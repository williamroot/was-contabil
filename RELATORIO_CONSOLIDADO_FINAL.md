# Relatório Consolidado — Box de Ferramentas HPR + Nosso Plano

**Data:** 18 de março de 2026
**Fonte:** Análise de 4 plataformas HPR + vídeo de apresentação (Helena Roberto)
**Vídeo:** https://www.youtube.com/watch?v=0fwVJlM_Si0

---

## 1. O QUE É O BOX DE FERRAMENTAS HPR

São **4 ferramentas** vendidas em conjunto para advogados e contadores que atuam em transação tributária:

| # | Ferramenta | Uso Principal | URL Analisada |
|---|-----------|---------------|---------------|
| 1 | **Diagnóstico Prévio** | Reuniões de prospecção — análise rápida sem detalhes técnicos | `hpr-diagnostico-transacao-copy-*.base44.app` |
| 2 | **Simulador CAPAG** | Análise profunda com dados do Regularize — múltiplos cenários | `simulacao-de-transacao-meta-copy-*.base44.app` |
| 3 | **Simulador TPV** | Transação de Pequeno Valor — validação por CDA, importação Excel | `hpr-tpv-sim.base44.app` |
| 4 | **Diagnóstico TPV Simplificado** | Wizard rápido de elegibilidade TPV | `pgfn-debt-solve.base44.app` |

### Público-alvo
- Advogados tributaristas
- Contadores
- Consultores fiscais

### Modelo de negócio
- Venda de licença profissional
- Aplicativo web responsivo (PC, celular, iPad)
- Atualizações conforme mudanças nos editais PGFN
- Cupons de desconto para associados (ex: ABET com 20%)

---

## 2. MAPA COMPLETO DE FUNCIONALIDADES (4 plataformas + vídeo)

### 2.1 Diagnóstico Prévio (Ferramenta 1)
**Quando usar:** Prospecção, reuniões iniciais com cliente

| Feature | Detalhe |
|---------|---------|
| Input simplificado | Valor total da dívida, % previdenciário, porte |
| Desconto padrão 30% | Estimativa conservadora para primeira conversa |
| Separação Prev/Não Prev | Prazos 60m vs 120/145m |
| Entrada 6% em 6/12 parcelas | Conforme porte |
| Fluxo de parcelas | Mês a mês consolidado |
| Exportação PDF | Para enviar ao prospect |

### 2.2 Simulador CAPAG (Ferramenta 2 — a principal)
**Quando usar:** Análise profunda com dados reais do Regularize

| Feature | Detalhe |
|---------|---------|
| Cadastro de empresas | CRUD com busca, porte, honorários de êxito |
| Dados do Regularize | CAPAG presumida, Passivo RFB, débitos detalhados |
| Decomposição P/M/J/E | Principal, Multa, Juros, Encargos (separados) |
| 3 categorias de débitos | Previdenciário, Tributário/Não Tributário, Simples Nacional |
| Rating CAPAG automático | A/B/C/D baseado em CAPAG/Passivo |
| Desconto correto | Apenas sobre multa+juros+encargos (nunca principal) |
| Menor/Maior desconto | Cenário conservador vs otimista |
| Honorários de êxito | % sobre economia obtida |
| Múltiplos cenários por cliente | Editar e salvar diferentes simulações |
| PDF para petições | Relatório Resumido e Completo |
| Desconto efetivo | Métrica real (desconto / dívida total) |

### 2.3 Simulador TPV (Ferramenta 3)
**Quando usar:** Quando a revisão da CAPAG não é vantajosa, para dívidas pequenas

| Feature | Detalhe |
|---------|---------|
| Validação por CDA individual | Valor ≤ 60 SM + inscrição > 1 ano |
| Importação em lote (Excel) | Dados do Regularize exportados |
| CDAs Aptas vs Não Aptas | Classificação automática |
| Elegibilidade futura | Projeção de quando CDA ficará apta |
| Descontos escalonados | 50/45/40/30% conforme parcelas |
| Entrada 5% em até 5 parcelas | Específico da TPV |
| Desconto sobre todo o saldo | Inclusive principal (exceção legal) |
| Relatório A4 imprimível | Para apresentar ao cliente |

### 2.4 Diagnóstico TPV Simplificado (Ferramenta 4)
**Quando usar:** Verificação rápida de elegibilidade

| Feature | Detalhe |
|---------|---------|
| Wizard de perguntas | Tipo, CDA > 60SM?, Valor, > 1 ano? |
| Checklist em tempo real | 4 critérios verde/vermelho |
| Comparação 4 faixas | 50/45/40/30% lado a lado |
| Badge "Melhor opção" | Destaque visual |
| Economia máxima | Cálculo automático |

---

## 3. FLUXO DE TRABALHO DO PROFISSIONAL

```
PROSPECÇÃO                    ANÁLISE                      EXECUÇÃO
─────────────                ──────────                   ──────────

1. Diagnóstico     ──→    2. Simulador CAPAG    ──→    Petição ao
   Prévio                    (dados do                   Regularize
   (reunião rápida)          Regularize)                 (PDF gerado)
                                  │
                                  ├── Se CAPAG ruim ──→ 3. Simulador TPV
                                  │                        (verificar CDAs)
                                  │
                                  └── Se dúvida ──→ 4. Diagnóstico TPV
                                       rápida           (wizard elegibilidade)
```

**Insight do vídeo:** A ferramenta 1 (Diagnóstico Prévio) é usada na **prospecção** para convencer o cliente. A ferramenta 2 (Simulador CAPAG) é a principal, usada quando o cliente **já contratou** e tem os dados do Regularize. As ferramentas 3 e 4 são alternativas para quando a CAPAG não é vantajosa.

---

## 4. DADOS QUE VÊM DO REGULARIZE (PGFN)

O vídeo confirma que os dados de entrada vêm do portal **Regularize** (www.regularize.pgfn.gov.br):

| Dado | Onde encontrar no Regularize |
|------|------------------------------|
| CAPAG Presumida (60 meses) | Consulta de Capacidade de Pagamento |
| Passivo RFB | Consulta de Débitos |
| Débitos Previdenciários (P/M/J/E) | Detalhamento de inscrições |
| Débitos Tributários (P/M/J/E) | Detalhamento de inscrições |
| Débitos Simples Nacional (P/M/J/E) | Detalhamento de inscrições |
| Lista de CDAs com valores e datas | Consulta de inscrições em dívida ativa |

**Oportunidade para nós:** Automatizar a extração desses dados (scraping do Regularize ou importação de relatório exportado).

---

## 5. O QUE NOSSO PLANO JÁ COBRE vs O QUE FALTA

### Já coberto no plano (26 Tasks):
- [x] Diagnóstico Prévio (Tasks 1-14)
- [x] Simulador CAPAG com decomposição P/M/J/E (Tasks 23-26)
- [x] Simulador TPV com validação por CDA (Tasks 15-19)
- [x] Diagnóstico TPV simplificado/wizard (Tasks 20-21)
- [x] Comparador de Modalidades (Task 22)
- [x] Cadastro de Empresas com honorários (Task 23)
- [x] Rating CAPAG automático (Task 24)
- [x] Importação CSV de CDAs (Task 17)
- [x] PDF Resumido e Completo (Task 26)
- [x] Correção SELIC dinâmica (Tasks 5-6) **exclusivo nosso**
- [x] Comparador TPV vs Capacidade (Task 22) **exclusivo nosso**

### Novos insights do vídeo para adicionar:

#### A) Fluxo de Trabalho Guiado
O vídeo mostra que as 4 ferramentas são usadas em **sequência** conforme o estágio do cliente. Nossa plataforma deve ter uma **navegação guiada**:
- "Reunião de prospecção? → Diagnóstico Prévio"
- "Cliente contratado, tem dados do Regularize? → Simulador CAPAG"
- "CAPAG não é vantajosa? → Simulador TPV"

#### B) Múltiplos Cenários por Cliente
O vídeo destaca que o profissional pode **editar e salvar múltiplos cenários** para o mesmo cliente. Isso já está parcialmente coberto no histórico, mas devemos:
- Permitir duplicar uma simulação existente e editar
- Comparar cenários lado a lado para o mesmo cliente
- Nomear cenários (ex: "Cenário Conservador", "Cenário Otimista")

#### C) Importação Excel do Regularize
O vídeo menciona importação em lote via **Excel** (não CSV). Devemos suportar:
- Upload de .xlsx além de .csv
- Parser que reconhece o formato de exportação do Regularize
- Mapeamento automático de colunas

#### D) Responsividade (Mobile/Tablet)
O vídeo destaca que funciona em **celular e iPad**. Nossa API REST já suporta qualquer frontend, mas devemos garantir que o frontend (quando construído) seja responsivo.

#### E) Atualizações Conforme Editais
O vídeo menciona que a ferramenta é **atualizada constantemente** conforme novos editais da PGFN. Devemos:
- Manter as constantes legais em arquivo separado (já feito: `constants.py`)
- Ter um sistema de versionamento das regras de cálculo
- Log de qual versão de regras foi usada em cada simulação (já feito: `versao_calculo`)

---

## 6. PLANO FINAL — 26 TASKS, 135 STEPS

O plano está completo e cobre TODAS as funcionalidades das 4 plataformas HPR mais features exclusivas nossas:

| Bloco | Tasks | Descrição |
|-------|-------|-----------|
| Infraestrutura | 1-2 | Docker, DB, Models, Alembic |
| Engine Básico | 3-4 | Constantes legais, Motor de cálculo |
| Índices BCB | 5-6 | Client API SELIC/IPCA, Sync, Correção |
| Auth | 7 | OAuth Google + Microsoft + JWT |
| API Diagnóstico Prévio | 8-14 | Schemas, Service, Router, PDF, Main |
| TPV Avançado (por CDA) | 15-19 | Constantes, Validadores, Engine, CSV, Router, PDF |
| TPV Simplificado + Comparador | 20-22 | Multi-faixa, Wizard, Comparação modalidades |
| Empresas + Simulação Avançada | 23-26 | CRUD, Engine P/M/J/E + CAPAG, Router, PDF |

### Features exclusivas nossas (não existem em nenhuma HPR):
1. **Correção SELIC dinâmica** nas parcelas via API BCB
2. **Comparador TPV vs Capacidade de Pagamento** — recomendação automática
3. **Rating CAPAG transparente** — mostra a fórmula, não só o resultado
4. **OAuth Google + Microsoft** (HPR usa email/senha simples)
5. **API REST documentada** — pode ser consumida por qualquer frontend

### Fonte do vídeo:
- https://www.youtube.com/watch?v=0fwVJlM_Si0
- Apresentado por Helena Roberto (HPR Consultoria e Assessoria Tributária)
- Box de Ferramentas vendido para advogados/contadores
