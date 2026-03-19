# Relatório de Análise - Plataforma HPR TPV Simulator

**Data:** 18 de março de 2026
**Plataforma analisada:** https://hpr-tpv-sim.base44.app/
**Tipo:** Simulador de Transação de Pequeno Valor (TPV)

---

## 1. O QUE A PLATAFORMA FAZ

O **TPV Simulator** é uma ferramenta especializada na modalidade de **Transação de Pequeno Valor** do Edital PGDAU 11/2025. Diferente da plataforma anterior (Diagnóstico de Transação genérico), esta trabalha no nível de **CDA (Certidão de Dívida Ativa) individual**, com validação automática de elegibilidade.

### 1.1 Páginas/Módulos

| Página | Função |
|--------|--------|
| **Início** | Landing page com explicação das funcionalidades |
| **Simulador TPV** | Formulário principal: identificação + cadastro de CDAs + cálculo |
| **Simulações** | Histórico de simulações salvas |
| **Impressão** | Geração de relatório A4 imprimível |
| **Elegibilidade** | Acompanhamento de CDAs não aptas com projeção de quando serão aptas |

### 1.2 Dados de Entrada

| Campo | Detalhe |
|-------|---------|
| Nome do Contribuinte | Razão social ou nome completo |
| CPF/CNPJ | Identificação fiscal |
| Tipo/Porte | **Pessoa Física (PF)**, **Microempresa (ME)**, **Empresa de Pequeno Porte (EPP)** |
| Salário Mínimo Vigente | Valor atual (R$ 1.621,00 em 2026) — usado para calcular limite de 60 SM |
| Data da Simulação | Data base do cálculo |
| Data Início Pagamento | Opcional — quando começam as parcelas |
| **CDAs individuais** | Número, valor total, data de inscrição (uma por uma ou importação em lote) |

---

## 2. REGRAS DE NEGÓCIO IDENTIFICADAS

### 2.1 Validação de Elegibilidade por CDA

Cada CDA é validada em **dois critérios simultâneos**:

| Critério | Regra | Verificação |
|----------|-------|-------------|
| **Valor ≤ 60 SM** | CDA deve ter valor total ≤ 60 × salário mínimo vigente | Automática (check verde/vermelho) |
| **Inscrição > 1 ano** | CDA deve estar inscrita há mais de 1 ano da data da simulação | Automática (check verde/vermelho) |

**Status resultante:**
- **APTA** — atende ambos os critérios → entra no cálculo
- **NÃO APTA** — falha em pelo menos um critério → não entra no cálculo

### 2.2 Cálculo da TPV

| Parâmetro | Valor | Fonte Legal |
|-----------|-------|-------------|
| **Entrada** | **5%** do valor total das CDAs aptas (sem desconto) | Edital PGDAU 11/2025, modalidade Pequeno Valor |
| **Parcelas de entrada** | Até **5 meses** | Edital PGDAU 11/2025 |
| **Desconto sobre saldo** | Variável conforme nº de parcelas (tabela abaixo) | Edital PGDAU 11/2025 |
| **Desconto incide sobre principal** | **SIM** — exceção legal da TPV | Art. 11, §2º, I da Lei 13.988 tem exceção para pequeno valor |
| **Limite por CDA** | **60 salários mínimos** (R$ 97.260,00 em 2026) | Edital PGDAU 11/2025 |
| **Quem pode aderir** | Apenas **PF, ME, EPP** | Edital PGDAU 11/2025 |
| **Tempo mínimo inscrição** | **1 ano** (CDA inscrita há mais de 1 ano) | Portaria PGFN 6.757/2022 |

### 2.3 Tabela de Descontos por Parcelas (Saldo)

| Parcelas do Saldo | Desconto |
|-------------------|----------|
| Até **7 parcelas** | **50%** |
| Até **12 parcelas** | **45%** |
| Até **30 parcelas** | **40%** |
| Até **55 parcelas** | **30%** |

### 2.4 Fórmula de Cálculo (verificada com teste R$ 500,00, 7 parcelas)

```
Valor CDAs Aptas:          R$ 500,00
Entrada (5%):              R$  25,00   → 1x de R$ 25,00
Saldo antes desconto:      R$ 475,00   (500 - 25)
Desconto (50%):            R$ 237,50   (475 × 0.50)
Saldo com desconto:        R$ 237,50   (475 - 237,50)
Parcelas do saldo (7x):    R$  33,93   (237,50 / 7)
Valor Final Negociado:     R$ 262,50   (25 + 237,50)
Economia total:            R$ 237,50   (50% OFF)
Total de parcelas:         8           (1 entrada + 7 saldo)
```

### 2.5 Projeção de Elegibilidade para CDAs Não Aptas

Quando uma CDA é "NÃO APTA", a plataforma mostra:
- **Motivo:** "Inscrição inferior a 1 ano" ou "Valor acima de 60 SM"
- **Data projetada:** "Apta por tempo em: DD/MM/YYYY"
- **Contagem regressiva:** "Faltam X dias para completar 1 ano"

---

## 3. FUNCIONALIDADES EXTRAS IDENTIFICADAS

### 3.1 Importação de CDA em Lote
- Botão "Importar CDA em Lote" (formato não explorado — provavelmente CSV/Excel)

### 3.2 Salvar Simulação
- Botão "Salvar" persiste a simulação completa
- Página "Simulações" lista todas as simulações salvas
- Possibilidade de consultar, visualizar ou excluir

### 3.3 Impressão/Relatório A4
- Página dedicada para geração de relatório imprimível
- Inclui: CDAs, status, cálculo financeiro, fluxo de parcelas

### 3.4 Elegibilidade Futura
- Dashboard dedicado para acompanhar CDAs não aptas
- **Ranking de Elegibilidade** com colunas: CDA, Valor, Inscrição, Motivo, Apta Tempo, Apta Valor, Parcelas, Previsão
- **KPIs:** Total CDAs não aptas, Próxima elegibilidade, Média para concluir
- **Filtros:** por tipo de impedimento
- Nota: "Estimativas por valor são simplificadas e não consideram atualização SELIC/encargos"

---

## 4. DIFERENÇAS ENTRE AS DUAS PLATAFORMAS HPR

| Aspecto | Diagnóstico Transação (1ª) | TPV Simulator (2ª) |
|---------|---------------------------|-------------------|
| **Modalidade** | Transação por Capacidade de Pagamento | Transação de Pequeno Valor |
| **Granularidade** | Valor total da dívida (consolidado) | **CDA por CDA** (individual) |
| **Validação** | Nenhuma (aceita qualquer valor) | **Dupla validação**: valor ≤ 60 SM + inscrição > 1 ano |
| **Desconto** | Fixo 30% (para todos) | **Variável 30-50%** conforme parcelas |
| **Base do desconto** | Valor total | **Todo o saldo** (inclusive principal — exceção legal TPV) |
| **Entrada** | 6% em 6 ou 12 meses | **5% em até 5 meses** |
| **Quem pode** | Qualquer empresa | Apenas **PF, ME, EPP** |
| **Múltiplas CDAs** | Não suporta | **Sim**, com importação em lote |
| **Elegibilidade** | Não tem | **Dashboard dedicado** com projeção |
| **Histórico** | Não tem | **Sim**, com listagem e exclusão |
| **Salário mínimo** | Não usa | **Dinâmico** (calcula limite de 60 SM) |
| **Impressão** | PDF genérico | **Relatório A4** profissional |

---

## 5. REQUISITOS NOVOS PARA NOSSO PLANO

### A) Módulo TPV (Transação de Pequeno Valor) — NOVA FEATURE
- Simulador com cadastro de CDAs individuais
- Validação automática: valor ≤ 60 SM + inscrição > 1 ano
- Tabela de descontos escalonada (50/45/40/30% por parcelas)
- Entrada de 5% em até 5 parcelas
- Desconto incide sobre TODO o saldo (inclusive principal)
- Fluxo de parcelas detalhado

### B) Multi-CDA com Status
- Adicionar CDAs uma a uma ou importar em lote (CSV)
- Validar cada CDA individualmente
- Separar CDAs Aptas (usadas no cálculo) vs Não Aptas (acompanhamento)
- Botão excluir CDA individual

### C) Elegibilidade Futura — NOVA FEATURE
- Dashboard para CDAs não aptas
- Projeção de data de elegibilidade
- Contagem regressiva (X dias para completar 1 ano)
- Ranking com filtros
- KPIs: total não aptas, próxima elegibilidade, média para concluir

### D) Salário Mínimo Dinâmico
- Campo editável com valor vigente
- Cálculo automático do limite de 60 SM
- Atualizar quando mudar o SM (via config ou API?)

### E) Relatório A4 Imprimível
- Template otimizado para impressão
- CDAs, status, cálculo, fluxo de parcelas
- Diferente do PDF da transação geral

### F) Importação em Lote de CDAs
- Upload CSV/Excel com múltiplas CDAs
- Validação em batch
- Preview antes de confirmar

---

## 6. PONTOS QUE PODEMOS MELHORAR

1. **Atualização SELIC nas CDAs não aptas** — a plataforma HPR admite que "estimativas por valor são simplificadas e não consideram atualização SELIC/encargos". Podemos calcular o valor atualizado da CDA na data projetada de elegibilidade.

2. **Valor da CDA formato** — ao inserir "150000", o sistema interpretou como R$ 1.500,00 (parece ter divisão por 100 automática). Nosso sistema deve aceitar ambos os formatos.

3. **Integração entre modalidades** — permitir que o usuário simule AMBAS as modalidades (Capacidade de Pagamento + TPV) para a mesma empresa e compare qual é mais vantajosa.

4. **Validação de CNPJ/CPF com dígito verificador** — a HPR não valida.

5. **Histórico de salário mínimo** — manter tabela com valores históricos para simulações retroativas.

6. **Notificação de elegibilidade** — avisar por email quando uma CDA atingir a elegibilidade.
