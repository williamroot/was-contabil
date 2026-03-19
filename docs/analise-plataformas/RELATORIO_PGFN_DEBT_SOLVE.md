# Relatório de Análise - Plataforma PGFN Debt Solve (Diagnóstico TPV - PGFN)

**Data:** 18 de março de 2026
**Plataforma analisada:** https://pgfn-debt-solve.base44.app/
**Tipo:** Diagnóstico simplificado de Transação de Pequeno Valor

---

## 1. O QUE A PLATAFORMA FAZ

O **Diagnóstico TPV - PGFN** é uma versão **simplificada** do simulador TPV. Em vez de cadastrar CDAs individuais, ele funciona com **perguntas de elegibilidade** (tipo wizard/formulário condicional) para determinar se o contribuinte é elegível e, se sim, calcular as opções de parcelamento.

### 1.1 Fluxo de Perguntas (Formulário Condicional)

O formulário revela campos progressivamente conforme as respostas:

```
1. Tipo de Contribuinte → [PF | ME | EPP]
   Se elegível (PF/ME/EPP): ✅ Critério 1 verde

2. Possui CDA > 60 SM? → [Sim | Não]
   Se "Não": ✅ Critério 2 verde → revela campo Valor Total
   Se "Sim": ❌ Critério 2 vermelho → bloqueia simulação

3. Valor Total da Dívida → R$ [input numérico]
   Quando preenchido: ✅ Critério 3 verde

4. CDAs inscritas há mais de 1 ano? → [Sim | Não]
   Se "Sim": ✅ Critério 4 verde → botão "Simular" habilitado
   Se "Não": ❌ Critério 4 vermelho → bloqueia simulação
```

### 1.2 Painel de Critérios de Elegibilidade (sidebar)

Um painel lateral mostra o status de cada critério em tempo real:

| Critério | Status Possíveis |
|----------|-----------------|
| Tipo de Contribuinte | "Selecione o tipo" / "Tipo elegível" ✅ |
| Limite por CDA | "Responda sobre CDAs" / "Todas dentro do limite" ✅ / "Possui CDA acima - não elegível" ❌ |
| Valor da Dívida | "Informe o valor" / "Valor informado" ✅ |
| Tempo de Inscrição | "Confirme o tempo" / "Todas com mais de 1 ano" ✅ / "Não elegível" ❌ |

**Alerta geral:**
- Amarelo: "Preencha todos os critérios para continuar"
- Verde: "Elegível para Transação de Pequeno Valor"

### 1.3 Resultado da Simulação

Quando todos os critérios são ✅, o resultado mostra:

**Cabeçalho:**
- Dívida Original: R$ X
- Economia Máxima: -R$ Y (com badge "Até 50% OFF")
- Melhor Valor Final: R$ Z

**Entrada (5%):**
- Valor da entrada: R$ X (sem desconto)
- Parcelamento: 5x de R$ Y

**Opções de Parcelamento do Saldo (todas as 4 faixas comparadas lado a lado):**

| Faixa | Desconto | Parcelas | Desconto $ | Saldo Final | Parcela |
|-------|----------|----------|-----------|-------------|---------|
| **50%** (melhor opção) | 50% | Até 7x | -R$ 356,25 | R$ 356,25 | 7x de R$ 50,89 |
| 45% | 45% | Até 12x | -R$ 320,63 | R$ 391,88 | 12x de R$ 32,66 |
| 40% | 40% | Até 30x | -R$ 285,00 | R$ 427,50 | 30x de R$ 14,25 |
| 30% | 30% | Até 55x | -R$ 213,75 | R$ 498,75 | 55x de R$ 9,07 |

**Entrada Obrigatória (repetida no final):**
- Valor: R$ 37,50 (5%)
- 5x de R$ 7,50

**Exportar PDF:** Botão disponível no cabeçalho do resultado.

---

## 2. REGRAS DE NEGÓCIO (confirmam a 2ª plataforma)

As regras são idênticas à 2ª plataforma (TPV Simulator), com as mesmas constantes:

| Parâmetro | Valor |
|-----------|-------|
| Entrada | 5% do total (sem desconto) |
| Parcelas entrada | Fixo 5 meses |
| Desconto 7 parcelas | 50% |
| Desconto 12 parcelas | 45% |
| Desconto 30 parcelas | 40% |
| Desconto 55 parcelas | 30% |
| Limite por CDA | 60 SM (R$ 97.260) |
| Tempo mínimo inscrição | 1 ano |
| Elegíveis | PF, ME, EPP |
| SM referência | R$ 1.621,00 (2026) |

### Fórmula verificada (R$ 750,00):
```
Dívida:             R$ 750,00
Entrada (5%):       R$  37,50  → 5x de R$ 7,50
Saldo:              R$ 712,50  (750 - 37,50)

Opção 50% (7x):    Desconto R$ 356,25 → Saldo R$ 356,25 → 7x de R$ 50,89
Opção 45% (12x):   Desconto R$ 320,63 → Saldo R$ 391,88 → 12x de R$ 32,66
Opção 40% (30x):   Desconto R$ 285,00 → Saldo R$ 427,50 → 30x de R$ 14,25
Opção 30% (55x):   Desconto R$ 213,75 → Saldo R$ 498,75 → 55x de R$ 9,07
```

---

## 3. DIFERENÇAS ENTRE AS 3 PLATAFORMAS HPR

| Aspecto | 1ª (Diagnóstico Transação) | 2ª (TPV Simulator) | 3ª (PGFN Debt Solve) |
|---------|---------------------------|-------------------|----------------------|
| **Modalidade** | Capacidade de Pagamento | TPV por CDA | TPV simplificado |
| **Abordagem** | Valor consolidado | CDA por CDA | Wizard de perguntas |
| **CDAs individuais** | Não | Sim (com importação) | Não (apenas total) |
| **Validação** | Nenhuma | Por CDA automatizada | Por perguntas Sim/Não |
| **Elegibilidade** | Não | Dashboard com projeção | Checklist em tempo real |
| **Resultado** | 1 cenário fixo | 1 cenário escolhido | **4 cenários comparados** |
| **Desconto** | Fixo 30% | Escolhe 1 faixa | **Mostra todas as faixas** |
| **Histórico** | Não | Sim (CRUD) | Não |
| **Impressão** | PDF genérico | Relatório A4 | PDF (botão) |
| **Entrada** | 6%, 6-12 parcelas | 5%, 1-5 parcelas | 5%, fixo 5 parcelas |
| **SM dinâmico** | Não | Sim (editável) | Sim (fixo R$ 1.621) |

---

## 4. NOVOS REQUISITOS PARA NOSSO PLANO

### A) Wizard de Elegibilidade (Formulário Condicional)
- Formulário que revela campos progressivamente conforme respostas
- Painel lateral com status de cada critério (verde/amarelo/vermelho)
- Mensagem "Elegível" ou "Não Elegível" em tempo real
- Bloqueia simulação se algum critério falhar
- **UX superior**: guia o usuário passo a passo, não sobrecarrega com campos

### B) Comparação de TODAS as Faixas de Desconto
- A 3ª plataforma mostra as 4 opções lado a lado (50/45/40/30%)
- Marca a "Melhor opção" (50% - 7 parcelas)
- Mostra desconto, saldo final e parcela para cada faixa
- **Nós devemos implementar isso em AMBOS os módulos (TPV com CDA e TPV simplificado)**

### C) Badge "Melhor Opção" / "Até X% OFF"
- Destaque visual para a opção com maior desconto
- Cálculo da economia máxima vs economia por faixa

### D) Modo Simplificado vs Avançado
- **Simplificado (wizard):** como a 3ª plataforma — perguntas rápidas, sem cadastro de CDAs
- **Avançado (por CDA):** como a 2ª plataforma — cadastro individual, importação lote, elegibilidade futura
- Toggle entre os dois modos no mesmo módulo TPV

### E) Entrada Fixa em 5 Parcelas
- A 3ª plataforma fixa a entrada em 5 parcelas (não dá opção)
- A 2ª plataforma permite escolher de 1 a 5
- Nosso sistema deve permitir escolha (como a 2ª) mas usar 5 como padrão

---

## 5. PONTOS QUE PODEMOS MELHORAR SOBRE TODAS AS 3

1. **Unificar as 3 modalidades** em uma única plataforma com navegação clara
2. **Comparação entre modalidades**: simular TPV e Capacidade de Pagamento lado a lado e mostrar qual é mais vantajosa
3. **Atualização SELIC dinâmica** (nenhuma das 3 plataformas aplica correção SELIC)
4. **Validação real de CNPJ/CPF** (nenhuma das 3 valida)
5. **Formulário condicional inteligente**: combinar o wizard (3ª) com o detalhamento por CDA (2ª)
6. **Parcela mínima validada**: a 3ª plataforma gerou parcela de R$ 7,50 que está abaixo do mínimo legal (R$ 100,00 PJ / R$ 25,00 MEI)
7. **Histórico unificado** com busca, filtros e tags por modalidade
8. **Multi-cenário com comparação** visual (gráficos de economia por faixa)
