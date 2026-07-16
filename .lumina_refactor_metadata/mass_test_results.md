# LuminaAI - Relatorio de Stress Test em Massa

> Gerado em: **2026-07-15 13:26:15** | Tempo total de execucao: **159.7s (2.7 min)**

---

## 📊 Resumo Executivo

| Métrica | Valor |
|---|---|
| **Total de Perguntas Executadas** | 20/200 |
| **Cenarios Testados** | 10/100 |
| **Taxa de Sucesso** | 85.0% (17 de 20) |
| **Respostas Parciais/Ambiguas** | 3 |
| **Bloqueios de Escopo/Seguranca** | 0 (comportamento esperado) |
| **Falhas SQL** | 0 |
| **Timeouts** | 0 |
| **Excecoes** | 0 |
| **Latencia Media** | 7972ms |
| **Latencia P95** | 20275ms |
| **Erros de Sintaxe SQL** | 0 |

---

## Distribuicao de Classificacoes

| Classificacao | Qtd | Descricao |
|---|---|---|
| [OK] SUCCESS | 17 | Pipeline executou e retornou dados corretamente |
| [~~] PARTIAL/EMPTY | 3 | Query OK mas resultado vazio ou ambiguidade |
| [--] BLOCKED | 0 | Consulta fora de escopo (comportamento correto) |
| [XX] FAIL_SQL | 0 | Erro de sintaxe SQL no banco |
| [TO] TIMEOUT | 0 | Excedeu 45s sem resposta |
| [!!] EXCEPTION | 0 | Excecao nao tratada no pipeline |

---

## Resultados por Cenario


### [BASIC] Cenarios 1-30: View Unica (Basico-Intermediario)

| # | Cenário | Pergunta A | Pergunta B | Latência Méd. |
|---|---|---|---|---|
| 1 | Clientes por Estado | [OK] SUCCESS | [OK] SUCCESS | 9252ms |
| 2 | Clientes de São Paulo | [OK] SUCCESS | [OK] SUCCESS | 12757ms |
| 3 | Catálogo de Produtos | [OK] SUCCESS | [OK] SUCCESS | 8699ms |
| 4 | Produtos por Custo | [OK] SUCCESS | [OK] SUCCESS | 10031ms |
| 5 | Vendas do Dia | [OK] SUCCESS | [OK] SUCCESS | 8568ms |
| 6 | Vendas de Junho 2026 | [OK] SUCCESS | [??] AMBIGUOUS | 6634ms |
| 7 | Clientes Inativos | [OK] SUCCESS | [OK] SUCCESS | 7209ms |
| 8 | Vendedores Sudeste | [??] AMBIGUOUS | [??] AMBIGUOUS | 3048ms |
| 9 | Produtos com Pro no Nome | [OK] SUCCESS | [OK] SUCCESS | 6577ms |
| 10 | Clientes Letra A | [OK] SUCCESS | [OK] SUCCESS | 6947ms |

---

## [OK] Zero Erros de Sintaxe SQL

> Nenhum erro de sintaxe SQL foi encontrado durante o stress test!

---

*Relatório gerado automaticamente pelo LuminaAI Mass Stress Test — 2026-07-15 13:26:15*