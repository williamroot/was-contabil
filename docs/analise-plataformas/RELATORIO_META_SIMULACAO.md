# Relatório de Análise - Plataforma Simulação de Transação Meta (HPR)

**Data:** 18 de março de 2026
**Plataforma analisada:** https://simulacao-de-transacao-meta-copy-2c85aed1.base44.app/
**Tipo:** Simulador completo de Transação Tributária com cadastro de empresas

---

## 1. O QUE A PLATAFORMA FAZ

É a plataforma **mais avançada** das 4. Combina cadastro de empresas, simulação com decomposição de dívida (principal/multa/juros/encargos), classificação CAPAG automática, honorários de êxito, e impressão em dois modos (resumido/completo).

### 1.1 Páginas/Módulos

| Página | Função |
|--------|--------|
| **Empresas** | Cadastro CRUD com busca, porte, honorários |
| **Nova Simulação** | Formulário detalhado com 3 categorias de débitos |
| **Resultado da Simulação** | Rating CAPAG, desconto por componente, parcelamento detalhado |
| **Simulações** | Histórico de todas as simulações |
| **Impressão** | Dois modos: Resumido e Completo |

### 1.2 Cadastro de Empresa

| Campo | Detalhe |
|-------|---------|
| Nome da Empresa | Razão social |
| CNPJ | Com formatação |
| Porte | **ME ou EPP** / **Demais Empresas** |
| **% Honorários de Êxito** | Percentual para cálculo de honorários sobre a economia |
| Observações | Texto livre |

### 1.3 Dados de Entrada da Simulação

**Dados Gerais:**
| Campo | Detalhe |
|-------|---------|
| Empresa | Seleção do cadastro (pré-carrega CNPJ/porte) |
| **Passivo RFB** | Valor total do passivo na Receita Federal |
| **CAPAG Presumida (60 meses)** | Capacidade de pagamento estimada em 60 meses |
| **Escolha do Desconto** | "Menor Desconto" / "Maior Desconto" |

**3 Categorias de Débitos (cada uma com 4 componentes):**

| Categoria | Prazo | Componentes |
|-----------|-------|-------------|
| **Débitos Previdenciários** | Limitado a 60 meses | Principal, Multa, Juros, Encargos |
| **Débitos Tributários e Não Tributários** | ME/EPP: 145m / Demais: 120m | Principal, Multa, Juros, Encargos |
| **Débitos Simples Nacional** | ME/EPP: 145m / Demais: 120m | Principal, Multa, Juros, Encargos |

---

## 2. REGRAS DE NEGÓCIO IDENTIFICADAS

### 2.1 Classificação CAPAG Automática (Rating)

A plataforma calcula automaticamente o **Rating** baseado na relação CAPAG/Passivo:
- **Rating D** (Crítico) — aplicado quando CAPAG é muito inferior ao passivo total
- Mostra badge colorido: D = vermelho "Crítico"

### 2.2 Desconto por Componente (CORRETO juridicamente)

**O desconto NÃO incide sobre o Principal** — apenas sobre Multa, Juros e Encargos:

| Componente | Valor Original | Desconto | Valor Final |
|-----------|---------------|----------|-------------|
| Principal | R$ 1.000,00 | **-** (sem desconto) | R$ 1.000,00 |
| Multa | R$ 300,00 | -R$ 282,00 | R$ 18,00 |
| Juros | R$ 500,00 | -R$ 470,00 | R$ 30,00 |
| Encargos | R$ 200,00 | -R$ 188,00 | R$ 12,00 |
| **TOTAL** | R$ 2.000,00 | -R$ 940,00 | R$ 1.060,00 |

**Desconto aplicado:** 70% sobre multa+juros+encargos (para ME/EPP, classificação D)

### 2.3 Fórmula de Desconto Verificada

Para classificação D + ME/EPP + "Maior Desconto":
```
Multa:    R$ 300 × (1 - 0.06) × 0% = R$ 300 × 0.94 = R$ 282 desconto → R$ 18 final
          (desconto de ~94% sobre multa? Ou 70% do total de multa+juros+encargos?)
```

O desconto parece ser calculado com base na relação CAPAG/Passivo, não um percentual fixo. A lógica exata é:
- CAPAG Presumida / Passivo Total = grau de capacidade de pagamento
- Rating derivado disso
- Desconto aplicável conforme rating e porte

### 2.4 Parcelamento

| Categoria | Entrada | Parcelas Entrada (ME/EPP) | Saldo | Parcelas Saldo |
|-----------|---------|--------------------------|-------|---------------|
| Previdenciário | 6% | 12x | Saldo após desconto | 48x (60 - 12) |
| Tributário | 6% | 12x | Saldo após desconto | 133x (145 - 12) |

### 2.5 Resumo do Passivo

Mostra um dashboard com badges:
- **Previd.** R$ 2.000
- **Trib. e Não Trib.** R$ 2.800
- **PGFN** R$ 4.800 (soma previd + trib)
- **RFB** R$ 5.000 (passivo RFB informado)
- **Desconto** R$ 2.162
- **Total** R$ 9.800

### 2.6 Honorários de Êxito

Botão "Mostrar Honorários de Êxito" — calcula o valor dos honorários sobre a economia obtida (ex: 20% de R$ 2.162 = R$ 432,40).

### 2.7 Impressão

Dois modos:
- **Modo Impressão (Resumido)** — visão geral
- **Modo Impressão (Completo)** — todas as 145 parcelas

### 2.8 Desconto Efetivo

No rodapé mostra:
- Dívida Total PGFN: R$ 4.800
- Saldo após Desconto: R$ 2.638
- Desconto Obtido: R$ 2.162
- **Desconto Efetivo: 45,04%** (R$ 2.162 / R$ 4.800)

---

## 3. DIFERENÇAS ENTRE AS 4 PLATAFORMAS HPR

| Aspecto | 1ª Diagnóstico | 2ª TPV Sim | 3ª PGFN Debt | **4ª Meta** |
|---------|---------------|-----------|-------------|------------|
| **Modalidade** | Cap. Pagamento | TPV por CDA | TPV wizard | **Cap. Pagamento avançado** |
| **Cadastro empresa** | Não | Não | Não | **Sim (CRUD + busca)** |
| **Decomposição** | Valor total | Valor total | Valor total | **Principal/Multa/Juros/Encargos** |
| **Categorias** | Prev + Não Prev | N/A | N/A | **Prev + Trib/NãoTrib + Simples** |
| **CAPAG** | Não | N/A | N/A | **Sim (presumida + rating auto)** |
| **Desconto principal** | Sim (erro) | Sim (exceção TPV) | Sim (exceção TPV) | **Não (correto juridicamente)** |
| **Passivo RFB** | Não | Não | Não | **Sim (separado de PGFN)** |
| **Honorários** | Não | Não | Não | **Sim (% sobre economia)** |
| **Impressão** | PDF | Relatório A4 | PDF | **Resumido + Completo** |
| **Escolha desconto** | Fixo 30% | Escalonado | Escalonado | **Menor/Maior desconto** |
| **Rating visual** | Não | Não | Não | **Sim (badge D Crítico)** |
| **Simples Nacional** | Não | Não | Não | **Sim (categoria separada)** |

---

## 4. NOVOS REQUISITOS PARA NOSSO PLANO

### A) Cadastro de Empresas (CRUD completo)
- Nome, CNPJ, Porte (ME/EPP ou Demais)
- **% Honorários de Êxito** — campo numérico
- Observações
- Busca por nome ou CNPJ
- Editar/Excluir empresa
- Vincular empresa à simulação (FK)

### B) Decomposição Principal/Multa/Juros/Encargos
- **Desconto NÃO incide sobre Principal** (art. 11, §2º, I da Lei 13.988)
- Input separado para cada componente
- Tabela de resultado mostrando desconto por componente
- Cálculo correto: desconto % aplicado APENAS sobre (multa + juros + encargos)

### C) 3 Categorias de Débitos
- **Previdenciário** — prazo máximo 60 meses (CF/88)
- **Tributário e Não Tributário** — prazo 120/145 meses
- **Simples Nacional** — prazo 120/145 meses (mesmas regras trib.)
- Cada categoria com seus 4 componentes separados

### D) CAPAG Presumida + Rating Automático
- Input: CAPAG Presumida (60 meses) + Passivo RFB
- Cálculo automático do rating (A/B/C/D) baseado na relação CAPAG/Passivo
- Badge visual com cor: A=verde, B=amarelo, C=laranja, D=vermelho
- Rating determina desconto aplicável (A/B = sem desconto, C/D = com desconto)

### E) Escolha Menor/Maior Desconto
- "Menor Desconto" — cenário conservador (desconto mínimo para o rating)
- "Maior Desconto" — cenário otimista (desconto máximo para o rating)
- Útil para apresentar faixa de possibilidades ao cliente

### F) Passivo RFB separado de PGFN
- Passivo na Receita Federal (pode incluir débitos não inscritos em dívida ativa)
- PGFN = soma dos débitos inscritos (previdenciário + tributário + simples)
- Total = RFB + PGFN

### G) Cálculo de Honorários de Êxito
- % configurável por empresa no cadastro
- Botão "Mostrar Honorários de Êxito"
- Cálculo: economia_obtida × percentual_honorarios
- Ex: R$ 2.162 × 20% = R$ 432,40

### H) Dois Modos de Impressão
- **Resumido:** Dashboard com resumo, rating, descontos, parcelas resumidas
- **Completo:** Todas as parcelas (até 145) detalhadas mês a mês

### I) Desconto Efetivo
- Métrica: Desconto Obtido / Dívida Total × 100
- Mostra o impacto real do desconto considerando que o principal não tem desconto

---

## 5. PONTOS QUE PODEMOS MELHORAR

1. **Fórmula CAPAG → Rating automática e transparente** — a HPR calcula mas não mostra a fórmula. Nós mostramos o cálculo.
2. **Cenário A/B/C/D comparativo** — simular todos os 4 ratings lado a lado.
3. **Atualização SELIC nas parcelas** — nenhuma plataforma HPR aplica.
4. **3ª categoria (Simples Nacional) com regras específicas** — verificar se há vedação de desconto no Simples (art. 5º, II, "a" da Lei 13.988).
5. **Integração com dados reais da PGFN/Regularize** — puxar passivo automaticamente.
6. **Validação de CNPJ** com dígito verificador.
7. **Multi-cenário exportável** — PDF com Menor Desconto vs Maior Desconto lado a lado.
