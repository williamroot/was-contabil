# Relatório de Análise - Plataforma HPR Diagnóstico de Transação Tributária

**Data:** 17 de março de 2026
**Plataforma analisada:** https://hpr-diagnostico-transacao-copy-206cb47f.base44.app/
**Empresa auditada:** COMERCIO HORTIFRUTI SITIO VERDE (CNPJ: 03.523.294/0001-24)

---

## 1. O QUE A PLATAFORMA FAZ

A plataforma **HPR Consultoria - Diagnóstico Prévio de Transação Tributária** é um simulador web que calcula as condições de pagamento para adesão ao programa de **Transação Tributária Federal** (negociação de dívidas com a PGFN/RFB).

### 1.1 Dados de Entrada
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Nome da Empresa | Sim | Razão social |
| CNPJ | Sim | Identificação fiscal |
| Telefone | Não | Contato |
| E-mail | Não | Contato |
| Valor Total da Dívida | Sim | Valor consolidado da dívida ativa |
| % Dívida Previdenciária | Sim | Percentual da dívida que é previdenciária |
| ME ou EPP? | Sim | Se a empresa é Microempresa ou Empresa de Pequeno Porte |

### 1.2 Resultado Gerado
O simulador gera um diagnóstico completo com:
- **Resumo da dívida** (total, desconto, valor com desconto)
- **Valor de entrada** e número de parcelas de entrada
- **Separação Previdenciária vs. Não Previdenciária** com prazos distintos
- **Fluxo de pagamento consolidado** mês a mês
- **Tabelas detalhadas** de cada modalidade (Previdenciária e Não Previdenciária)
- **Exportação em PDF** do diagnóstico completo
- **Botão "Copiar Resumo"** para compartilhamento rápido

---

## 2. REGRAS DE NEGÓCIO IDENTIFICADAS

### 2.1 Taxas e Percentuais Aplicados

| Parâmetro | Valor | Fonte Legal |
|-----------|-------|-------------|
| **Desconto sobre dívida** | **30%** (fixo para ambos os cenários testados) | Lei nº 13.988/2020 (art. 11) e Portaria PGFN nº 6.757/2022 - desconto mínimo de até 65% para transações individuais; a plataforma usa 30% como piso estimativo |
| **Entrada** | **6% do valor com desconto** | Portaria PGFN nº 6.757/2022, art. 36 - entrada mínima de 6% para adesão |
| **Parcelas de entrada (Demais Empresas)** | **6 meses** | Portaria PGFN nº 6.757/2022, art. 36, §1º |
| **Parcelas de entrada (ME/EPP)** | **12 meses** | Portaria PGFN nº 6.757/2022, art. 36, §2º - condição diferenciada para ME/EPP |
| **Prazo Previdenciário (máx.)** | **60 meses** | CF/88, art. 195, §11 - limite constitucional para parcelamento previdenciário |
| **Prazo Não Previdenciário (Demais)** | **120 meses** | Lei nº 13.988/2020 e Portaria PGFN nº 6.757/2022 |
| **Prazo Não Previdenciário (ME/EPP)** | **145 meses** | Portaria PGFN nº 6.757/2022, art. 38 - prazo estendido para ME/EPP |

### 2.2 Lógica de Cálculo Identificada

#### Para Demais Empresas (testado com R$ 10.000,00, 30% previdenciário):
```
Dívida Total:                R$ 10.000,00
Desconto (30%):             -R$  3.000,00
Saldo com desconto:          R$  7.000,00
Entrada (6%):                R$    600,00 → 6x de R$ 100,00

Previdenciária (30%):        R$  3.000,00
  Desconto (30%):           -R$    900,00
  Saldo:                     R$  2.100,00
  Entrada (6x):              R$   30,00/mês = R$ 180,00
  Parcelas (54x):            R$   35,56/mês = R$ 1.920,00 (saldo R$ 2.100 - 180 = R$ 1.920 / 54)

Não Previdenciária (70%):    R$  7.000,00
  Desconto (30%):           -R$  2.100,00
  Saldo:                     R$  4.900,00
  Entrada (6x):              R$   70,00/mês = R$ 420,00
  Parcelas (114x):           R$   39,30/mês = R$ 4.480,00 (saldo R$ 4.900 - 420 = R$ 4.480 / 114)
```

#### Para ME/EPP (testado com R$ 10.000,00, 30% previdenciário):
```
Mesmos valores de desconto e entrada, porém:
  Entrada em 12 meses (ao invés de 6)
  Previdenciária: 60 meses (12 entrada + 48 parcelas)
    Entrada (12x): R$ 15,00/mês
    Parcelas (48x): R$ 40,00/mês
  Não Previdenciária: 145 meses (12 entrada + 133 parcelas)
    Entrada (12x): R$ 35,00/mês
    Parcelas (133x): R$ 33,68/mês
```

---

## 3. FONTES LEGAIS DAS TAXAS

### 3.1 Base Legal Principal
| Legislação | Assunto | Link/Referência |
|-----------|---------|-----------------|
| **Lei nº 13.988/2020** | Institui a transação tributária no âmbito federal | Dispõe sobre resolução de conflitos entre Administração Tributária Federal e contribuintes |
| **Portaria PGFN nº 6.757/2022** | Regulamenta as modalidades de transação no âmbito da PGFN | Define regras de entrada, prazos, descontos e condições |
| **CF/88, art. 195, §11** | Limite constitucional de 60 meses para parcelamento de contribuições previdenciárias | Não pode ser alterado por lei ordinária |
| **LC 123/2006** | Define ME (até R$ 360 mil) e EPP (até R$ 4,8 milhões) | Critério para enquadramento diferenciado |
| **Portaria PGFN nº 1.241/2025** | Atualiza regras de transação para 2025-2026 | Valores mínimos de parcela e novas modalidades |

### 3.2 Observações sobre os Descontos
A plataforma utiliza um **desconto fixo de 30%** como referência. Na prática, os descontos na transação tributária podem variar:

| Modalidade | Desconto Máx. | Prazo Máx. |
|-----------|---------------|------------|
| Transação por Adesão (edital) | Até 65% | 120 meses |
| Transação Individual | Até 65% | 120 meses |
| Transação Individual (ME/EPP) | Até 70% | 145 meses |
| Transação Excepcional (créditos irrecuperáveis) | Até 100% juros/multa | 145 meses |

---

## 4. DADOS DA AUDITORIA (~/Desktop/auditoria_1)

### 4.1 Visão Geral dos Dados
| Métrica | Valor |
|---------|-------|
| **Total de NFes** | 19.767 |
| **Valor total das NFes** | R$ 68.479.339,30 |
| **CNPJs emitentes únicos** | 298 fornecedores |
| **CNPJ destinatário** | 03.523.294/0001-24 (Comercio Hortifruti Sítio Verde) |
| **Período coberto** | 2020 a 2025 (bulk em jan-out/2025) |

### 4.2 Regime Tributário dos Fornecedores
| CRT | Regime | Qtd. NFes | % |
|-----|--------|-----------|---|
| 3 | Regime Normal (Lucro Presumido/Real) | 18.741 | 94,8% |
| 1 | Simples Nacional | 913 | 4,6% |
| 4 | Simples Nacional - MEI | 97 | 0,5% |
| 2 | SN - Excesso de sublimite | 15 | 0,1% |

### 4.3 Tributos Totais nas NFes
| Tributo | Valor |
|---------|-------|
| ICMS próprio | R$ 740.814,12 |
| ICMS-ST | R$ 9.102,91 |
| PIS | R$ 41.365,24 |
| COFINS | R$ 190.811,03 |
| IPI | R$ 47.173,08 |
| **TOTAL** | **R$ 1.029.266,38** |

### 4.4 Principais CFOPs (Operações Fiscais)
| CFOP | Descrição | Qtd. Itens |
|------|-----------|-----------|
| 5102 | Venda de mercadoria adquirida (dentro do estado) | 35.583 |
| 5101 | Venda de produção do estabelecimento (dentro do estado) | 13.196 |
| 5929 | Lançamento para documentar NFC-e | 5.061 |
| 5405 | Venda de mercadoria com ST (dentro do estado) | 2.247 |
| 6102 | Venda de mercadoria adquirida (fora do estado) | 677 |
| 5923 | Remessa de mercadoria por conta e ordem de terceiros | 328 |
| 5656 | Venda de combustível (dentro do estado) | 236 |

### 4.5 CSTs ICMS Mais Frequentes
| CST | Descrição | Qtd. |
|-----|-----------|------|
| ICMS40 (CST 40) | Isento | 42.290 |
| ICMS40 (CST 41) | Não tributado | 5.808 |
| ICMS60 (CST 60) | ICMS cobrado anteriormente por ST | 2.856 |
| ICMS00 (CST 00) | Tributado integralmente | 1.954 |
| ICMSSN500 | CSOSN 500 - Simples Nacional com ST | 1.625 |

### 4.6 Principais NCMs (Produtos)
| NCM | Produto | Qtd. |
|-----|---------|------|
| 07051900 | Alho (outros) | 9.488 |
| 08061000 | Uvas frescas | 5.161 |
| 07099990 | Outros legumes frescos | 2.213 |
| 07020000 | Tomates frescos | 1.601 |
| 08071900 | Melões (outros) | 1.404 |
| 07096000 | Pimentões | 1.349 |
| 08081000 | Maçãs | 1.053 |
| 08109090 | Outras frutas frescas | 1.025 |
| 08051000 | Laranjas | 1.020 |

### 4.7 Top Fornecedores (nas NFes com diretório organizado)
| Fornecedor | NFes | Valor Total |
|-----------|------|-------------|
| ASSTAM COMBUSTIVEIS LTDA (07793634000198) | 66 | R$ 2.339.480,00 |
| INDUGAS (68345826000126) | 58 | R$ 144.344,99 |

---

## 5. PONTOS QUE PODEMOS MELHORAR NA RÉPLICA

### 5.1 Melhorias Funcionais Críticas

#### A) Desconto Variável (não fixo em 30%)
**Problema:** A plataforma HPR aplica desconto fixo de 30% para todos os cenários.
**Melhoria:** Implementar cálculo dinâmico baseado na classificação da dívida:
- **Crédito Irrecuperável (D/E):** até 65-70% de desconto
- **Crédito de difícil recuperação (C):** até 50% de desconto
- **Crédito recuperável (A/B):** até 30% de desconto
- Considerar capacidade de pagamento do contribuinte
- Fonte: Portaria PGFN nº 6.757/2022, arts. 30-35

#### B) Integração com Dados Reais da PGFN
**Problema:** A plataforma pede valor da dívida manualmente.
**Melhoria:** Integrar com:
- **Regularize (PGFN):** Consulta automatizada de dívida ativa por CNPJ
- **e-CAC (RFB):** Consulta de débitos federais
- **Certidão PGFN:** Verificação de situação fiscal
- Isso eliminaria erros de input e daria valores precisos

#### C) Separação Detalhada das Naturezas de Dívida
**Problema:** A plataforma só separa "Previdenciário" vs. "Não Previdenciário".
**Melhoria:** Detalhar por natureza:
- IRPJ, CSLL, PIS, COFINS, IPI (cada um pode ter condições específicas)
- Multas de ofício vs. multas moratórias (descontos diferentes)
- Juros SELIC acumulados (calculados pela data do débito original)

#### D) Cálculo de Capacidade de Pagamento
**Problema:** Não existe análise de capacidade contributiva.
**Melhoria:** A transação tributária exige comprovação de capacidade de pagamento. Podemos:
- Solicitar faturamento dos últimos 12 meses
- Calcular a parcela máxima suportável
- Verificar se a proposta é viável para o contribuinte
- Fonte: Portaria PGFN nº 6.757/2022, art. 26

### 5.2 Melhorias de Análise Fiscal (usando dados da auditoria)

#### E) Diagnóstico de Créditos Tributários
Com os 19.767 XMLs de NFe, podemos calcular:
- **Créditos de PIS/COFINS** sobre insumos (R$ 41k PIS + R$ 190k COFINS nas entradas)
- **Créditos de ICMS-ST** a recuperar (CST 60 presente em 2.856 itens)
- **Aproveitamento de créditos de ICMS** nas compras tributadas integralmente (CST 00 - 1.954 itens)
- **Valores pagos a maior** por ST incorreta

#### F) Análise de Fornecedores e Compliance
- 94,8% dos fornecedores são Regime Normal (CRT 3) - verificar se estão destacando ICMS corretamente
- 4,6% Simples Nacional - verificar se o Sítio Verde está aproveitando créditos permitidos
- 97 NFes de MEI (CRT 4) - MEI não gera crédito de ICMS/PIS/COFINS, verificar se está correto

#### G) Simulação com Múltiplos Cenários de Transação
- **Cenário 1:** Transação por Adesão (edital PGFN mais recente)
- **Cenário 2:** Transação Individual (negociação direta)
- **Cenário 3:** Transação Individual Simplificada (para dívidas até R$ 1 milhão)
- **Cenário 4:** Litígio Zero (para débitos em contencioso)

### 5.3 Melhorias de UX/Produto

#### H) Dashboard com Histórico
- Salvar simulações anteriores para comparação
- Gráficos de evolução da dívida
- Timeline de prazos e vencimentos

#### I) Alertas sobre Editais Vigentes
- Monitorar editais de transação da PGFN (publicados periodicamente no DOU)
- Notificar clientes quando há janela de adesão aberta
- Mostrar deadline de cada modalidade

#### J) Geração de Documentos
- Pré-preencher requerimento de adesão à transação
- Gerar relatório para assinatura do contador
- Checklist de documentos necessários para adesão

#### K) Multi-Inscrição
- Permitir simular múltiplas inscrições em Dívida Ativa separadamente
- Cada inscrição pode ter natureza/condição diferente
- Consolidar visão total com subtotais por inscrição

### 5.4 Melhorias Técnicas

#### L) Validação de CNPJ
- A plataforma atual não valida o CNPJ digitado
- Implementar consulta à Receita Federal via CNPJ

#### M) Valores Mínimos de Parcela
- A plataforma não verifica o valor mínimo da parcela (R$ 100,00 para PF, R$ 500,00 para PJ conforme Portaria PGFN)
- No teste com R$ 10.000,00 as parcelas ficaram abaixo de R$ 100,00 (R$ 35,56 e R$ 39,30) o que seria rejeitado pela PGFN

#### N) Atualização Monetária (SELIC)
- A plataforma não aplica atualização SELIC sobre as parcelas
- Na prática, as parcelas da transação tributária são atualizadas mensalmente pela SELIC
- Fonte: Lei nº 13.988/2020, art. 11, §1º

#### O) Índices de Correção nos XMLs
- Aproveitar os dados fiscais para calcular o impacto real da correção monetária sobre dívidas existentes

---

## 6. ARQUITETURA SUGERIDA PARA RÉPLICA

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│  ┌─────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │Formulário│  │ Dashboard │  │ Gestão Clientes  │  │
│  │Simulação │  │ Gráficos  │  │ Histórico        │  │
│  └─────────┘  └───────────┘  └──────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│                    BACKEND                           │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ Engine de    │  │ Parser XML  │  │ Integração │ │
│  │ Cálculo      │  │ (NFe)       │  │ APIs Gov   │ │
│  │ Transação    │  │             │  │ (Regularize│ │
│  └──────────────┘  └─────────────┘  │  e-CAC)    │ │
│  ┌──────────────┐  ┌─────────────┐  └────────────┘ │
│  │ Tabelas de   │  │ Gerador PDF │                  │
│  │ Descontos/   │  │ Relatórios  │                  │
│  │ Prazos       │  │             │                  │
│  └──────────────┘  └─────────────┘                  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│                   BANCO DE DADOS                     │
│  Clientes │ Simulações │ NFes │ Dívidas │ Editais  │
└─────────────────────────────────────────────────────┘
```

---

## 7. RESUMO EXECUTIVO

### O que a plataforma HPR faz bem:
1. Interface limpa e profissional
2. Separação clara entre dívida previdenciária e não previdenciária
3. Fluxo de pagamento mês a mês consolidado
4. Exportação PDF
5. Distinção entre ME/EPP e Demais Empresas

### Onde podemos superar:
1. **Desconto dinâmico** baseado na classificação real do crédito (não fixo em 30%)
2. **Valor mínimo de parcela** - a HPR não valida (gera parcelas de R$ 35 que seriam rejeitadas)
3. **Atualização SELIC** nas parcelas (falta na HPR)
4. **Integração com dados fiscais reais** (NFes) para cruzamento e diagnóstico de créditos
5. **Capacidade de pagamento** calculada automaticamente
6. **Múltiplos cenários** de transação (adesão, individual, simplificada, litígio zero)
7. **Monitoramento de editais** vigentes
8. **Multi-inscrição** (cada dívida pode ter condições diferentes)

### Estimativa de Impacto para o Sítio Verde:
Com base nos dados das NFes:
- **Faturamento estimado (2025):** R$ 65,9 milhões (baseado nas NFes de recebimento)
- **Tributos nas entradas:** R$ 1,03 milhão (potenciais créditos a recuperar/validar)
- **298 fornecedores ativos** - oportunidade de auditoria fiscal de entradas

---

*Relatório gerado em 17/03/2026 por análise automatizada da plataforma HPR e dados de auditoria.*
