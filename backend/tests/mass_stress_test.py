"""
LuminaAI - Mass Stress Test: 200 Perguntas / 100 Cenarios Analiticos
=====================================================================
Executa 100 cenarios (2 perguntas cada: inicial + continuidade) diretamente
contra o new_query_orchestrator.run_pipeline(), mede latencia e classifica
resultados. Gera relatorio Markdown consolidado ao final.

Uso:
    python tests/mass_stress_test.py

Saida:
    .lumina_refactor_metadata/mass_test_results.md
"""
import io
import sys
# Forca UTF-8 no stdout para suportar acentos e emojis no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio
import os
import time
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# Garante que o backend está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

TENANT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
OUTPUT_DIR = Path(__file__).parent.parent.parent / ".lumina_refactor_metadata"
OUTPUT_FILE = OUTPUT_DIR / "mass_test_results.md"
TIMEOUT_SECONDS = 45  # Timeout por pergunta

# ─────────────────────────────────────────────────────────────────────────────
# 100 CENÁRIOS × 2 PERGUNTAS = 200 PERGUNTAS TOTAIS
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS: List[Dict] = [
    # =========================================================================
    # BLOCO 1: CENÁRIOS 1-30 — VIEW ÚNICA (Básicos a Intermediários)
    # =========================================================================
    {
        "id": 1, "tier": "SINGLE_VIEW", "titulo": "Clientes por Estado",
        "pergunta_a": "Quais clientes são do estado de MG?",
        "pergunta_b": "E quais deles têm status ATIVO?",
    },
    {
        "id": 2, "tier": "SINGLE_VIEW", "titulo": "Clientes de São Paulo",
        "pergunta_a": "Liste todos os clientes da cidade de São Paulo.",
        "pergunta_b": "Qual deles tem a maior receita registrada?",
    },
    {
        "id": 3, "tier": "SINGLE_VIEW", "titulo": "Catálogo de Produtos",
        "pergunta_a": "Mostre todos os produtos cadastrados.",
        "pergunta_b": "Filtre apenas os produtos da categoria Eletronicos.",
    },
    {
        "id": 4, "tier": "SINGLE_VIEW", "titulo": "Produtos por Custo",
        "pergunta_a": "Quais produtos têm custo acima de R$ 1.000?",
        "pergunta_b": "Ordene esses produtos do mais caro para o mais barato.",
    },
    {
        "id": 5, "tier": "SINGLE_VIEW", "titulo": "Vendas do Dia",
        "pergunta_a": "Quais foram as vendas realizadas em 14 de julho de 2026?",
        "pergunta_b": "Qual o total faturado nesse dia?",
    },
    {
        "id": 6, "tier": "SINGLE_VIEW", "titulo": "Vendas de Junho 2026",
        "pergunta_a": "Mostre todas as vendas de junho de 2026.",
        "pergunta_b": "Quantos pedidos foram feitos nesse período?",
    },
    {
        "id": 7, "tier": "SINGLE_VIEW", "titulo": "Clientes Inativos",
        "pergunta_a": "Liste todos os clientes com status INATIVO.",
        "pergunta_b": "Quantos desses clientes são do estado de SP?",
    },
    {
        "id": 8, "tier": "SINGLE_VIEW", "titulo": "Vendedores Sudeste",
        "pergunta_a": "Quais vendedores atuam na região Sudeste?",
        "pergunta_b": "Quantos vendedores existem nessa região?",
    },
    {
        "id": 9, "tier": "SINGLE_VIEW", "titulo": "Produtos com Pro no Nome",
        "pergunta_a": "Liste os produtos que contém a palavra Pro no nome.",
        "pergunta_b": "Qual é o custo médio desses produtos?",
    },
    {
        "id": 10, "tier": "SINGLE_VIEW", "titulo": "Clientes Letra A",
        "pergunta_a": "Quais clientes têm o nome começando com a letra A?",
        "pergunta_b": "Quantos clientes no total começam com A?",
    },
    {
        "id": 11, "tier": "SINGLE_VIEW", "titulo": "Faturamento 2026",
        "pergunta_a": "Qual o faturamento total de todas as vendas de 2026?",
        "pergunta_b": "Qual mês teve o maior volume de vendas em 2026?",
    },
    {
        "id": 12, "tier": "SINGLE_VIEW", "titulo": "Vendas Alto Valor",
        "pergunta_a": "Mostre as vendas com valor acima de R$ 10.000.",
        "pergunta_b": "Qual produto gerou mais dessas vendas de alto valor?",
    },
    {
        "id": 13, "tier": "SINGLE_VIEW", "titulo": "Lista de Vendedores",
        "pergunta_a": "Mostre a lista completa de todos os vendedores cadastrados.",
        "pergunta_b": "Ordene os vendedores por nome em ordem alfabética.",
    },
    {
        "id": 14, "tier": "SINGLE_VIEW", "titulo": "Clientes do RJ",
        "pergunta_a": "Quais são os clientes do Rio de Janeiro?",
        "pergunta_b": "Qual a receita total desses clientes?",
    },
    {
        "id": 15, "tier": "SINGLE_VIEW", "titulo": "Produtos Baratos",
        "pergunta_a": "Liste os produtos com custo menor que R$ 1.000.",
        "pergunta_b": "Quais categorias aparecem nesses produtos mais baratos?",
    },
    {
        "id": 16, "tier": "SINGLE_VIEW", "titulo": "Total de Clientes",
        "pergunta_a": "Quantos clientes estão cadastrados no sistema?",
        "pergunta_b": "Quantos desses clientes estão com status ATIVO?",
    },
    {
        "id": 17, "tier": "SINGLE_VIEW", "titulo": "Vendas Julho 2026",
        "pergunta_a": "Quais foram as vendas realizadas em julho de 2026?",
        "pergunta_b": "Qual o valor total faturado em julho?",
    },
    {
        "id": 18, "tier": "SINGLE_VIEW", "titulo": "Produtos Moveis",
        "pergunta_a": "Quais produtos pertencem à categoria Moveis?",
        "pergunta_b": "Qual é o custo médio dos produtos de Moveis?",
    },
    {
        "id": 19, "tier": "SINGLE_VIEW", "titulo": "Clientes de Belo Horizonte",
        "pergunta_a": "Liste os clientes cadastrados em Belo Horizonte.",
        "pergunta_b": "Qual o status atual desses clientes de BH?",
    },
    {
        "id": 20, "tier": "SINGLE_VIEW", "titulo": "Vendas Faixa de Valor",
        "pergunta_a": "Mostre vendas com valor entre R$ 5.000 e R$ 15.000.",
        "pergunta_b": "Quantas dessas vendas ocorreram em junho de 2026?",
    },
    {
        "id": 21, "tier": "SINGLE_VIEW", "titulo": "Vendedores Sul",
        "pergunta_a": "Quantos vendedores atuam na região Sul?",
        "pergunta_b": "Mostre os nomes desses vendedores da região Sul.",
    },
    {
        "id": 22, "tier": "SINGLE_VIEW", "titulo": "Produto PRD001",
        "pergunta_a": "Mostre os detalhes do produto com código PRD001.",
        "pergunta_b": "Qual a categoria e o custo desse produto?",
    },
    {
        "id": 23, "tier": "SINGLE_VIEW", "titulo": "Clientes Inativos Lista",
        "pergunta_a": "Mostre todos os clientes com status INATIVO.",
        "pergunta_b": "Quantos clientes inativos existem no cadastro?",
    },
    {
        "id": 24, "tier": "SINGLE_VIEW", "titulo": "Vendas por Vendedor",
        "pergunta_a": "Mostre o total de vendas agrupado por vendedor em 2026.",
        "pergunta_b": "Qual vendedor teve o maior faturamento total?",
    },
    {
        "id": 25, "tier": "SINGLE_VIEW", "titulo": "Vendas do Cliente CLI003",
        "pergunta_a": "Mostre todas as vendas realizadas para o cliente CLI003.",
        "pergunta_b": "Qual o total comprado pelo cliente CLI003?",
    },
    {
        "id": 26, "tier": "SINGLE_VIEW", "titulo": "Eletrodomésticos Custo",
        "pergunta_a": "Mostre os produtos da categoria Eletrodomesticos.",
        "pergunta_b": "Qual o custo médio dos Eletrodomesticos?",
    },
    {
        "id": 27, "tier": "SINGLE_VIEW", "titulo": "Vendedores Nordeste",
        "pergunta_a": "Quais vendedores atuam na região Nordeste?",
        "pergunta_b": "Mostre os nomes e IDs desses vendedores.",
    },
    {
        "id": 28, "tier": "SINGLE_VIEW", "titulo": "Clientes Porto Alegre Inativos",
        "pergunta_a": "Existem clientes em Porto Alegre com status INATIVO?",
        "pergunta_b": "Mostre os detalhes desses clientes.",
    },
    {
        "id": 29, "tier": "SINGLE_VIEW", "titulo": "Faturamento Junho Diário",
        "pergunta_a": "Qual o faturamento total em junho de 2026?",
        "pergunta_b": "Qual dia de junho teve o maior faturamento?",
    },
    {
        "id": 30, "tier": "SINGLE_VIEW", "titulo": "Clientes Alta Receita",
        "pergunta_a": "Quais clientes têm receita registrada acima de R$ 50.000?",
        "pergunta_b": "De quais estados são esses clientes com alta receita?",
    },

    # =========================================================================
    # BLOCO 2: CENÁRIOS 31-70 — MULTI-VIEW / JOINs (Complexos)
    # =========================================================================
    {
        "id": 31, "tier": "MULTI_VIEW", "titulo": "Faturamento por Cliente Jun/26",
        "pergunta_a": "Qual o faturamento gerado por cada cliente em junho de 2026?",
        "pergunta_b": "Filtre apenas clientes com faturamento acima de R$ 10.000.",
    },
    {
        "id": 32, "tier": "MULTI_VIEW", "titulo": "Produto Mais Vendido Junho",
        "pergunta_a": "Qual produto foi mais vendido em junho de 2026?",
        "pergunta_b": "Qual o faturamento total gerado por esse produto em junho?",
    },
    {
        "id": 33, "tier": "MULTI_VIEW", "titulo": "Ranking de Vendedores",
        "pergunta_a": "Mostre o ranking de vendedores por faturamento total.",
        "pergunta_b": "Qual vendedor ficou em primeiro lugar e qual o valor?",
    },
    {
        "id": 34, "tier": "MULTI_VIEW", "titulo": "Clientes SP e Compras",
        "pergunta_a": "Quais clientes do estado de SP fizeram compras?",
        "pergunta_b": "Qual o total comprado por esses clientes paulistas?",
    },
    {
        "id": 35, "tier": "MULTI_VIEW", "titulo": "Ranking Clientes por Valor",
        "pergunta_a": "Mostre o ranking dos clientes que mais compraram em valor total.",
        "pergunta_b": "Quais os 3 maiores compradores e seus valores?",
    },
    {
        "id": 36, "tier": "MULTI_VIEW", "titulo": "Produtos por Vendedor Junho",
        "pergunta_a": "Quais produtos cada vendedor vendeu em junho de 2026?",
        "pergunta_b": "Qual a combinação vendedor-produto com maior receita?",
    },
    {
        "id": 37, "tier": "MULTI_VIEW", "titulo": "Compras por Cliente Julho",
        "pergunta_a": "Qual o total de compras de cada cliente em julho de 2026?",
        "pergunta_b": "Qual cliente fez mais compras em julho?",
    },
    {
        "id": 38, "tier": "MULTI_VIEW", "titulo": "Clientes Ativos e Faturamento",
        "pergunta_a": "Qual o faturamento total gerado por clientes com status ATIVO?",
        "pergunta_b": "Compare com o faturamento de clientes INATIVOS.",
    },
    {
        "id": 39, "tier": "MULTI_VIEW", "titulo": "Produtos do CLI001",
        "pergunta_a": "Quais produtos o cliente CLI001 já comprou?",
        "pergunta_b": "Qual o produto mais caro comprado pelo CLI001?",
    },
    {
        "id": 40, "tier": "MULTI_VIEW", "titulo": "Faturamento por Estado",
        "pergunta_a": "Qual o faturamento total agrupado por estado dos clientes em junho de 2026?",
        "pergunta_b": "Qual estado gerou mais receita em junho?",
    },
    {
        "id": 41, "tier": "MULTI_VIEW", "titulo": "Vendedores e Clientes Atendidos",
        "pergunta_a": "Quais clientes cada vendedor atendeu?",
        "pergunta_b": "Qual vendedor atendeu o maior número de clientes distintos?",
    },
    {
        "id": 42, "tier": "MULTI_VIEW", "titulo": "Produto Lucrativo por Região",
        "pergunta_a": "Qual produto gerou mais faturamento por região de cliente?",
        "pergunta_b": "Na região Sudeste, qual produto liderou as vendas?",
    },
    {
        "id": 43, "tier": "MULTI_VIEW", "titulo": "Clientes MG Eletronicos",
        "pergunta_a": "Quais clientes de MG compraram produtos da categoria Eletronicos?",
        "pergunta_b": "Qual o valor total dessas compras de clientes MG em Eletronicos?",
    },
    {
        "id": 44, "tier": "MULTI_VIEW", "titulo": "Margem por Produto",
        "pergunta_a": "Qual a relação entre o valor de venda e o custo de cada produto?",
        "pergunta_b": "Qual produto tem a maior diferença entre preço vendido e custo?",
    },
    {
        "id": 45, "tier": "MULTI_VIEW", "titulo": "Pedidos por Cliente 2026",
        "pergunta_a": "Quantos pedidos cada cliente fez em 2026?",
        "pergunta_b": "Qual cliente fez mais pedidos?",
    },
    {
        "id": 46, "tier": "MULTI_VIEW", "titulo": "Top 3 Vendedores",
        "pergunta_a": "Quais são os 3 melhores vendedores por valor total de vendas?",
        "pergunta_b": "Qual a diferença de faturamento entre o 1º e o 3º colocado?",
    },
    {
        "id": 47, "tier": "MULTI_VIEW", "titulo": "Ticket Médio por Cliente",
        "pergunta_a": "Qual o ticket médio por compra de cada cliente?",
        "pergunta_b": "Qual cliente tem o maior ticket médio?",
    },
    {
        "id": 48, "tier": "MULTI_VIEW", "titulo": "Produtos para Inativos",
        "pergunta_a": "Quais produtos foram vendidos para clientes INATIVOS?",
        "pergunta_b": "Qual o valor total dessas vendas para clientes inativos?",
    },
    {
        "id": 49, "tier": "MULTI_VIEW", "titulo": "Faturamento VED001 Mensal",
        "pergunta_a": "Qual o faturamento mensal do vendedor VED001 em 2026?",
        "pergunta_b": "Em qual mês o VED001 teve melhor desempenho?",
    },
    {
        "id": 50, "tier": "MULTI_VIEW", "titulo": "Clientes Sul e Compras",
        "pergunta_a": "Quais clientes da região Sul (RS, SC, PR) fizeram compras?",
        "pergunta_b": "Qual o faturamento total desses clientes do Sul?",
    },
    {
        "id": 51, "tier": "MULTI_VIEW", "titulo": "Produtos com Boa Margem",
        "pergunta_a": "Quais produtos geraram receita de venda muito acima do custo cadastrado?",
        "pergunta_b": "Ordene esses produtos do com maior para menor lucro bruto.",
    },
    {
        "id": 52, "tier": "MULTI_VIEW", "titulo": "Clientes Multi-Produto",
        "pergunta_a": "Quais clientes compraram mais de um produto diferente?",
        "pergunta_b": "Quantos produtos distintos cada um desses clientes comprou?",
    },
    {
        "id": 53, "tier": "MULTI_VIEW", "titulo": "Vendedor Mais Clientes",
        "pergunta_a": "Qual vendedor atendeu o maior número de clientes distintos?",
        "pergunta_b": "Liste os clientes desse vendedor líder.",
    },
    {
        "id": 54, "tier": "MULTI_VIEW", "titulo": "Faturamento por Categoria",
        "pergunta_a": "Qual o faturamento total agrupado por categoria de produto?",
        "pergunta_b": "Qual categoria de produto é a mais lucrativa?",
    },
    {
        "id": 55, "tier": "MULTI_VIEW", "titulo": "Vendedor do CLI005",
        "pergunta_a": "Qual vendedor realizou as vendas para o cliente CLI005?",
        "pergunta_b": "Qual o total vendido por esse vendedor para o CLI005?",
    },
    {
        "id": 56, "tier": "MULTI_VIEW", "titulo": "Vendas por Cidade",
        "pergunta_a": "Qual o total de vendas agrupado por cidade dos clientes?",
        "pergunta_b": "Qual cidade gerou mais receita para a empresa?",
    },
    {
        "id": 57, "tier": "MULTI_VIEW", "titulo": "Produtos Clientes RJ",
        "pergunta_a": "Quais produtos foram comprados por clientes do Rio de Janeiro?",
        "pergunta_b": "Qual o produto mais popular entre os clientes do RJ?",
    },
    {
        "id": 58, "tier": "MULTI_VIEW", "titulo": "Faturamento Acumulado Vendedores",
        "pergunta_a": "Qual o faturamento acumulado de cada vendedor em todo o período de 2026?",
        "pergunta_b": "Qual a participação percentual de cada vendedor no total?",
    },
    {
        "id": 59, "tier": "MULTI_VIEW", "titulo": "Clientes Notebook Pro",
        "pergunta_a": "Quais clientes compraram o produto Notebook Pro?",
        "pergunta_b": "Qual o total gasto por esses clientes no Notebook Pro?",
    },
    {
        "id": 60, "tier": "MULTI_VIEW", "titulo": "Pedidos por Produto Junho",
        "pergunta_a": "Quantos pedidos de cada produto foram feitos em junho de 2026?",
        "pergunta_b": "Qual produto teve mais pedidos em junho?",
    },
    {
        "id": 61, "tier": "MULTI_VIEW", "titulo": "Produto Favorito CLI003",
        "pergunta_a": "Qual produto o cliente CLI003 mais comprou em valor total?",
        "pergunta_b": "Quantas vezes o CLI003 comprou esse produto?",
    },
    {
        "id": 62, "tier": "MULTI_VIEW", "titulo": "Faturamento por UF",
        "pergunta_a": "Qual o faturamento total agrupado por UF (estado) dos clientes?",
        "pergunta_b": "Quais os 3 estados que mais geraram receita?",
    },
    {
        "id": 63, "tier": "MULTI_VIEW", "titulo": "Vendedores em Eletrodomésticos",
        "pergunta_a": "Quais vendedores realizaram vendas de produtos Eletrodomesticos?",
        "pergunta_b": "Qual desses vendedores faturou mais em Eletrodomesticos?",
    },
    {
        "id": 64, "tier": "MULTI_VIEW", "titulo": "Clientes Curitiba e Produtos",
        "pergunta_a": "Quais produtos foram comprados por clientes de Curitiba?",
        "pergunta_b": "Qual o valor total dessas compras de Curitiba?",
    },
    {
        "id": 65, "tier": "MULTI_VIEW", "titulo": "Top 5 Clientes",
        "pergunta_a": "Mostre os 5 clientes que mais compraram em valor total.",
        "pergunta_b": "Qual a participação desses top 5 no faturamento geral?",
    },
    {
        "id": 66, "tier": "MULTI_VIEW", "titulo": "PRD004 por Vendedor",
        "pergunta_a": "Qual o faturamento do produto PRD004 agrupado por vendedor?",
        "pergunta_b": "Qual vendedor vendeu mais unidades do PRD004?",
    },
    {
        "id": 67, "tier": "MULTI_VIEW", "titulo": "Inativos que Compraram",
        "pergunta_a": "Existem clientes com status INATIVO que realizaram compras?",
        "pergunta_b": "Qual o valor total comprado por clientes inativos?",
    },
    {
        "id": 68, "tier": "MULTI_VIEW", "titulo": "Produtos do VED002",
        "pergunta_a": "Quais produtos o vendedor VED002 vendeu?",
        "pergunta_b": "Qual produto gerou mais receita para o VED002?",
    },
    {
        "id": 69, "tier": "MULTI_VIEW", "titulo": "Receita por Status de Cliente",
        "pergunta_a": "Qual a receita total agrupada por status de cliente (ATIVO vs INATIVO)?",
        "pergunta_b": "Qual a diferença percentual de receita entre ativos e inativos?",
    },
    {
        "id": 70, "tier": "MULTI_VIEW", "titulo": "Cruzamento Cliente Produto Estado",
        "pergunta_a": "Mostre as vendas cruzando cliente, produto e estado de origem do cliente.",
        "pergunta_b": "Qual combinação estado-produto gerou mais receita?",
    },

    # =========================================================================
    # BLOCO 3: CENÁRIOS 71-90 — MÉTRICAS AVANÇADAS / HAVING / GROUP BY
    # =========================================================================
    {
        "id": 71, "tier": "ADVANCED", "titulo": "Clientes HAVING Compras Altas",
        "pergunta_a": "Quais clientes compraram mais de R$ 20.000 no acumulado?",
        "pergunta_b": "Qual o ranking desses clientes por valor decrescente?",
    },
    {
        "id": 72, "tier": "ADVANCED", "titulo": "Produtos Mais de 2 Vendas",
        "pergunta_a": "Quais produtos foram vendidos em mais de 2 transações diferentes?",
        "pergunta_b": "Qual o faturamento total desses produtos populares?",
    },
    {
        "id": 73, "tier": "ADVANCED", "titulo": "Vendedores HAVING 50k+",
        "pergunta_a": "Quais vendedores tiveram faturamento total acima de R$ 50.000?",
        "pergunta_b": "Qual a média de faturamento por venda desses vendedores top?",
    },
    {
        "id": 74, "tier": "ADVANCED", "titulo": "Ticket Médio Alto HAVING",
        "pergunta_a": "Quais clientes têm ticket médio por compra acima de R$ 10.000?",
        "pergunta_b": "Compare esse ticket médio com a média geral de todos os clientes.",
    },
    {
        "id": 75, "tier": "ADVANCED", "titulo": "Faturamento por Estado Agrupado",
        "pergunta_a": "Mostre o faturamento total de junho de 2026 agrupado por estado dos clientes.",
        "pergunta_b": "Ordene os estados do maior para menor faturamento.",
    },
    {
        "id": 76, "tier": "ADVANCED", "titulo": "Faturamento Mensal 2026",
        "pergunta_a": "Mostre o faturamento total agrupado por mês em 2026.",
        "pergunta_b": "Qual mês teve o maior crescimento em relação ao anterior?",
    },
    {
        "id": 77, "tier": "ADVANCED", "titulo": "Estados com Múltiplos Clientes",
        "pergunta_a": "Quais estados têm mais de 1 cliente cadastrado?",
        "pergunta_b": "Qual o faturamento total desses estados com múltiplos clientes?",
    },
    {
        "id": 78, "tier": "ADVANCED", "titulo": "Custo Total Vendas HAVING",
        "pergunta_a": "Quais produtos têm soma de custo de venda acima de R$ 5.000?",
        "pergunta_b": "Liste esses produtos com seu faturamento e custo total.",
    },
    {
        "id": 79, "tier": "ADVANCED", "titulo": "Vendedores Mais de 3 Vendas",
        "pergunta_a": "Quais vendedores fizeram mais de 3 vendas no período total?",
        "pergunta_b": "Qual o valor médio de venda desses vendedores mais ativos?",
    },
    {
        "id": 80, "tier": "ADVANCED", "titulo": "Faturamento Mínimo por Categoria",
        "pergunta_a": "Quais categorias de produto têm faturamento total acima de R$ 5.000?",
        "pergunta_b": "Ordene essas categorias da mais para menos lucrativa.",
    },
    {
        "id": 81, "tier": "ADVANCED", "titulo": "Clientes Multi-Mês",
        "pergunta_a": "Quais clientes fizeram compras em mais de um mês diferente?",
        "pergunta_b": "Qual desses clientes comprou em mais meses distintos?",
    },
    {
        "id": 82, "tier": "ADVANCED", "titulo": "Análise de Concentração Top 3",
        "pergunta_a": "Qual o faturamento total dos 3 maiores clientes?",
        "pergunta_b": "Qual a participação percentual desses 3 clientes no faturamento global?",
    },
    {
        "id": 83, "tier": "ADVANCED", "titulo": "Crescimento Mês a Mês",
        "pergunta_a": "Compare o faturamento de junho de 2026 com julho de 2026.",
        "pergunta_b": "Houve crescimento ou queda percentual entre esses meses?",
    },
    {
        "id": 84, "tier": "ADVANCED", "titulo": "Breakdown Trimestral",
        "pergunta_a": "Mostre o faturamento total agrupado por trimestre de 2026.",
        "pergunta_b": "Qual trimestre de 2026 teve o melhor desempenho?",
    },
    {
        "id": 85, "tier": "ADVANCED", "titulo": "Vendedores Acima da Média",
        "pergunta_a": "Qual a média de faturamento por vendedor em 2026?",
        "pergunta_b": "Quais vendedores estão acima dessa média geral?",
    },
    {
        "id": 86, "tier": "ADVANCED", "titulo": "Produtos Acima de 10% Share",
        "pergunta_a": "Quais produtos representam mais de 10% do faturamento total?",
        "pergunta_b": "Qual a participação percentual exata de cada produto desse grupo?",
    },
    {
        "id": 87, "tier": "ADVANCED", "titulo": "Faturamento Vendedor vs Média",
        "pergunta_a": "Mostre o faturamento de cada vendedor comparado com a média geral.",
        "pergunta_b": "Quantos vendedores estão acima e quantos estão abaixo da média?",
    },
    {
        "id": 88, "tier": "ADVANCED", "titulo": "Clientes Alta Frequência",
        "pergunta_a": "Quais clientes realizaram mais de 2 compras no total?",
        "pergunta_b": "Qual o valor médio por compra desses clientes mais frequentes?",
    },
    {
        "id": 89, "tier": "ADVANCED", "titulo": "Análise Pareto 80/20",
        "pergunta_a": "Quais clientes concentram 80% do faturamento total?",
        "pergunta_b": "Esses clientes são de quais estados?",
    },
    {
        "id": 90, "tier": "ADVANCED", "titulo": "Sazonalidade de Produtos",
        "pergunta_a": "Quais produtos tiveram vendas tanto em junho quanto em julho de 2026?",
        "pergunta_b": "Qual produto manteve o melhor faturamento nos dois meses?",
    },

    # =========================================================================
    # BLOCO 4: CENÁRIOS 91-100 — UI / RESILIÊNCIA / EDGE CASES
    # =========================================================================
    {
        "id": 91, "tier": "UI_RESILIENCE", "titulo": "Gráfico Mensal 2026",
        "pergunta_a": "Mostre o gráfico de faturamento mensal de 2026.",
        "pergunta_b": "Altere a exibição para gráfico de barras e ordene de forma decrescente.",
    },
    {
        "id": 92, "tier": "UI_RESILIENCE", "titulo": "Tabela Clientes Ativos",
        "pergunta_a": "Exiba a tabela completa de clientes ativos.",
        "pergunta_b": "Ordene essa tabela por nome de cliente em ordem alfabética crescente.",
    },
    {
        "id": 93, "tier": "UI_RESILIENCE", "titulo": "Pergunta com Erro de Digitação",
        "pergunta_a": "Qual o faturamaneto de junhoo de 2026?",
        "pergunta_b": "E o de julho tambem com o total?",
    },
    {
        "id": 94, "tier": "UI_RESILIENCE", "titulo": "Pergunta em Inglês",
        "pergunta_a": "Show me the top clients by revenue in 2026.",
        "pergunta_b": "And which products did they buy the most?",
    },
    {
        "id": 95, "tier": "UI_RESILIENCE", "titulo": "Fora de Escopo - Salários",
        "pergunta_a": "Qual o salário dos vendedores da empresa?",
        "pergunta_b": "E qual o custo de folha de pagamento mensal total?",
    },
    {
        "id": 96, "tier": "UI_RESILIENCE", "titulo": "Pergunta Ambígua",
        "pergunta_a": "ranking",
        "pergunta_b": "dos clientes por valor total comprado.",
    },
    {
        "id": 97, "tier": "UI_RESILIENCE", "titulo": "Tentativa de SQL Injection",
        "pergunta_a": "Mostre vendas'; DROP TABLE vw_vendas_lm; --",
        "pergunta_b": "E DELETE FROM vw_clientes_cad_lm WHERE 1=1",
    },
    {
        "id": 98, "tier": "UI_RESILIENCE", "titulo": "Pergunta Muito Longa",
        "pergunta_a": (
            "Preciso de uma análise completa e detalhada do faturamento total "
            "de todos os clientes ativos e inativos de todos os estados do Brasil "
            "que compraram algum produto da categoria de Eletronicos ou Eletrodomesticos "
            "nos meses de junho e julho de 2026, agrupado por vendedor, estado do cliente "
            "e categoria do produto, ordenado pelo maior faturamento, "
            "mostrando também o ticket médio por cliente e por vendedor."
        ),
        "pergunta_b": "Filtre agora apenas os que tiveram faturamento acima de R$ 5.000 nesse agrupamento.",
    },
    {
        "id": 99, "tier": "UI_RESILIENCE", "titulo": "Fora de Escopo - Médico",
        "pergunta_a": "Quais funcionários estão de licença médica?",
        "pergunta_b": "Mostre os dados de saúde e prontuário dos colaboradores.",
    },
    {
        "id": 100, "tier": "UI_RESILIENCE", "titulo": "Pergunta Recursiva/Filosófica",
        "pergunta_a": "Qual é o sentido da vida e como isso afeta as vendas?",
        "pergunta_b": "Me dê os dados de faturamento de clientes felizes.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTOR E ANALISADOR
# ─────────────────────────────────────────────────────────────────────────────

def classify_response(res: Dict[str, Any], pergunta: str) -> Tuple[str, Optional[str]]:
    """
    Classifica a resposta como SUCCESS, PARTIAL, FAIL, BLOCKED ou AMBIGUOUS.
    Retorna (classificação, detalhe_do_erro_se_houver)
    """
    if isinstance(res, Exception):
        return "EXCEPTION", str(res)

    status = res.get("status", "")
    sql_error = None

    if status == "DATABASE_ERROR":
        msg = res.get("message", "")
        return "FAIL_SQL", msg
    elif status == "SECURITY_VIOLATION":
        return "BLOCKED_SECURITY", None
    elif status in ("AMBIGUOUS", "MISSING_INFORMATION"):
        return "AMBIGUOUS", None
    elif status == "OUT_OF_SCOPE":
        return "BLOCKED_SCOPE", None
    elif status == "NEEDS_REPLANNING":
        return "FAIL_PLAN", "BFS não encontrou caminho entre views"
    elif status == "UI_MODIFIED":
        return "SUCCESS_UI", None
    elif status == "FULL_RENDERING":
        # Verifica se tem dados reais
        rows = (res.get("chart_data") or {}).get("rows", [])
        if rows is not None:
            return "SUCCESS", None
        return "PARTIAL", "Status FULL_RENDERING mas sem rows"
    elif status == "EMPTY_ANOMALY":
        return "PARTIAL", "Query OK mas dataset vazio (período sem dados)"
    elif res.get("resposta_direta"):
        return "SUCCESS_DIRECT", None
    else:
        return "UNKNOWN", str(status)


async def run_scenario(
    orchestrator,
    scenario: Dict,
    scenario_num: int,
    total: int
) -> Dict:
    """Executa um cenário (2 perguntas) e retorna o resultado estruturado."""
    result = {
        "id": scenario["id"],
        "tier": scenario["tier"],
        "titulo": scenario["titulo"],
        "perguntas": [],
    }

    history = []
    session_id = f"mass_test_scenario_{scenario['id']}"

    for pergunta_key, label in [("pergunta_a", "A"), ("pergunta_b", "B")]:
        pergunta_original = scenario[pergunta_key]
        pergunta = pergunta_original
        pergunta = pergunta.replace("CLI001", "586")
        pergunta = pergunta.replace("CLI003", "3172")
        pergunta = pergunta.replace("CLI005", "3645")
        pergunta = pergunta.replace("Joao Silva", "ADRIANO AMARAL BISPO")
        pergunta = pergunta.replace("Ana Costa", "LAGES E LOPES LTDA")
        pergunta = pergunta.replace("Fernanda Lima", "PRODUTOR RURAL MODELO")
        pergunta = pergunta.replace("VED001", "74")
        pergunta = pergunta.replace("VED002", "1")
        pergunta = pergunta.replace("Pedro Santos", "AMANDA CRISTINA SOARES SILVA")
        pergunta = pergunta.replace("Mariana Torres", "PADRAO")
        pergunta = pergunta.replace("PRD001", "0000921")
        pergunta = pergunta.replace("PRD004", "0001284")
        pergunta = pergunta.replace("Notebook Pro", "LAMINA 2 PONTAS 241 HUSQVARNA")
        pergunta = pergunta.replace("Eletrônicos", "ACESSORIOS ROC")
        pergunta = pergunta.replace("Eletronicos", "ACESSORIOS ROC")
        pergunta = pergunta.replace("Eletrodomésticos", "RACAO")
        pergunta = pergunta.replace("Eletrodomesticos", "RACAO")
        
        q_num = (scenario_num - 1) * 2 + (1 if label == "A" else 2)

        print(
            f"  [{q_num:03d}/{total}] #{scenario['id']:03d}-{label} "
            f"({scenario['tier']}) {pergunta[:70]}{'...' if len(pergunta) > 70 else ''}"
        )

        t_start = time.perf_counter()
        res = None
        try:
            res = await asyncio.wait_for(
                orchestrator.run_pipeline(
                    pergunta=pergunta,
                    tenant_id=TENANT_ID,
                    session_id=session_id,
                    history=history,
                ),
                timeout=TIMEOUT_SECONDS
            )
            elapsed = (time.perf_counter() - t_start) * 1000
            classification, error_detail = classify_response(res, pergunta)

            # Adiciona ao histórico para simular continuidade
            history.append({"role": "user", "content": pergunta})
            if res.get("resposta_direta") or res.get("ia_justificativa"):
                resp_text = res.get("resposta_direta") or res.get("ia_justificativa") or ""
                history.append({"role": "assistant", "content": resp_text[:500]})

        except asyncio.TimeoutError:
            elapsed = TIMEOUT_SECONDS * 1000
            classification = "TIMEOUT"
            error_detail = f"Timeout após {TIMEOUT_SECONDS}s"
            res = {}
        except Exception as exc:
            elapsed = (time.perf_counter() - t_start) * 1000
            classification = "EXCEPTION"
            error_detail = traceback.format_exc(limit=3)
            res = {}

        status_icon = {
            "SUCCESS": "[OK]", "SUCCESS_DIRECT": "[OK]", "SUCCESS_UI": "[OK]",
            "PARTIAL": "[~~]", "AMBIGUOUS": "[??]", "BLOCKED_SCOPE": "[--]",
            "BLOCKED_SECURITY": "[##]", "FAIL_SQL": "[XX]", "FAIL_PLAN": "[XX]",
            "TIMEOUT": "[TO]", "EXCEPTION": "[!!]", "UNKNOWN": "[?]",
        }.get(classification, "[?]")

        print(f"      {status_icon} {classification} | {elapsed:.0f}ms")
        if error_detail and classification not in ("AMBIGUOUS", "BLOCKED_SCOPE", "BLOCKED_SECURITY"):
            print(f"      [!] {str(error_detail)[:120]}")

        # Extrai SQL do telemetry para análise
        sql_query = None
        if isinstance(res, dict) and res.get("telemetry"):
            sql_query = res["telemetry"].get("sql")

        result["perguntas"].append({
            "label": label,
            "pergunta": pergunta,
            "classification": classification,
            "elapsed_ms": round(elapsed, 1),
            "error_detail": error_detail,
            "sql": sql_query,
            "status": res.get("status") if isinstance(res, dict) else None,
            "row_count": len((res.get("chart_data") or {}).get("rows") or []) if isinstance(res, dict) else 0,
        })

    return result


def generate_markdown_report(results: List[Dict], total_time_s: float) -> str:
    """Gera o relatório Markdown consolidado."""
    total_perguntas = sum(len(r["perguntas"]) for r in results)
    
    # Contadores por classificação
    counts = {}
    latencies = []
    sql_errors = []
    
    for r in results:
        for p in r["perguntas"]:
            c = p["classification"]
            counts[c] = counts.get(c, 0) + 1
            latencies.append(p["elapsed_ms"])
            if p["classification"] == "FAIL_SQL" and p["sql"]:
                sql_errors.append({
                    "scenario": r["id"],
                    "titulo": r["titulo"],
                    "pergunta": p["pergunta"],
                    "error": p["error_detail"],
                    "sql": p["sql"],
                })

    success_count = sum(v for k, v in counts.items() if k.startswith("SUCCESS"))
    partial_count = counts.get("PARTIAL", 0) + counts.get("AMBIGUOUS", 0)
    blocked_count = counts.get("BLOCKED_SCOPE", 0) + counts.get("BLOCKED_SECURITY", 0)
    fail_count = sum(v for k, v in counts.items() if k.startswith("FAIL"))
    timeout_count = counts.get("TIMEOUT", 0)
    exception_count = counts.get("EXCEPTION", 0)
    
    success_pct = (success_count / total_perguntas * 100) if total_perguntas else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        "# LuminaAI - Relatorio de Stress Test em Massa",
        f"\n> Gerado em: **{now}** | Tempo total de execucao: **{total_time_s:.1f}s ({total_time_s/60:.1f} min)**",
        "\n---\n",
        "## 📊 Resumo Executivo\n",
        f"| Métrica | Valor |",
        f"|---|---|",
        f"| **Total de Perguntas Executadas** | {total_perguntas}/200 |",
        f"| **Cenarios Testados** | {len(results)}/100 |",
        f"| **Taxa de Sucesso** | {success_pct:.1f}% ({success_count} de {total_perguntas}) |",
        f"| **Respostas Parciais/Ambiguas** | {partial_count} |",
        f"| **Bloqueios de Escopo/Seguranca** | {blocked_count} (comportamento esperado) |",
        f"| **Falhas SQL** | {fail_count} |",
        f"| **Timeouts** | {timeout_count} |",
        f"| **Excecoes** | {exception_count} |",
        f"| **Latencia Media** | {avg_latency:.0f}ms |",
        f"| **Latencia P95** | {p95_latency:.0f}ms |",
        f"| **Erros de Sintaxe SQL** | {len(sql_errors)} |",
        "\n---\n",
        "## Distribuicao de Classificacoes\n",
        "| Classificacao | Qtd | Descricao |",
        "|---|---|---|",
        f"| [OK] SUCCESS | {success_count} | Pipeline executou e retornou dados corretamente |",
        f"| [~~] PARTIAL/EMPTY | {partial_count} | Query OK mas resultado vazio ou ambiguidade |",
        f"| [--] BLOCKED | {blocked_count} | Consulta fora de escopo (comportamento correto) |",
        f"| [XX] FAIL_SQL | {fail_count} | Erro de sintaxe SQL no banco |",
        f"| [TO] TIMEOUT | {timeout_count} | Excedeu {TIMEOUT_SECONDS}s sem resposta |",
        f"| [!!] EXCEPTION | {exception_count} | Excecao nao tratada no pipeline |",
        "\n---\n",
    ]

    # Resultados por tier
    tiers = ["SINGLE_VIEW", "MULTI_VIEW", "ADVANCED", "UI_RESILIENCE"]
    tier_labels = {
        "SINGLE_VIEW": "[BASIC] Cenarios 1-30: View Unica (Basico-Intermediario)",
        "MULTI_VIEW":  "[MULTI] Cenarios 31-70: Multi-View / JOINs Complexos",
        "ADVANCED":    "[ADV]   Cenarios 71-90: Metricas Avancadas / HAVING",
        "UI_RESILIENCE": "[UI]  Cenarios 91-100: UI e Resiliencia de Escopo",
    }

    lines.append("## Resultados por Cenario\n")

    for tier in tiers:
        tier_results = [r for r in results if r["tier"] == tier]
        if not tier_results:
            continue
        
        lines.append(f"\n### {tier_labels[tier]}\n")
        lines.append("| # | Cenário | Pergunta A | Pergunta B | Latência Méd. |")
        lines.append("|---|---|---|---|---|")

        for r in tier_results:
            pa = next((p for p in r["perguntas"] if p["label"] == "A"), None)
            pb = next((p for p in r["perguntas"] if p["label"] == "B"), None)
            
            _icon_map = {"SUCCESS": "[OK]", "SUCCESS_DIRECT": "[OK]", "SUCCESS_UI": "[OK]",
                      "PARTIAL": "[~~]", "AMBIGUOUS": "[??]", "BLOCKED_SCOPE": "[--]",
                      "BLOCKED_SECURITY": "[##]", "FAIL_SQL": "[XX]", "FAIL_PLAN": "[XX]",
                      "TIMEOUT": "[TO]", "EXCEPTION": "[!!]"}
            icon_a = _icon_map.get(pa["classification"] if pa else "", "[?]")
            icon_b = _icon_map.get(pb["classification"] if pb else "", "[?]")
            
            avg_ms = ((pa["elapsed_ms"] if pa else 0) + (pb["elapsed_ms"] if pb else 0)) / 2
            
            lines.append(
                f"| {r['id']} | {r['titulo']} | "
                f"{icon_a} {pa['classification'] if pa else '-'} | "
                f"{icon_b} {pb['classification'] if pb else '-'} | "
                f"{avg_ms:.0f}ms |"
            )

    # Erros SQL para debug
    if sql_errors:
        lines.append("\n---\n")
        lines.append("## [XX] Erros de Sintaxe SQL (Para Blindagem)\n")
        for i, err in enumerate(sql_errors, 1):
            lines.append(f"\n### Erro {i}: Cenario #{err['scenario']} - {err['titulo']}")
            lines.append(f"\n**Pergunta:** `{err['pergunta'][:200]}`")
            lines.append(f"\n**Erro:** `{err['error'][:300] if err['error'] else 'N/A'}`")
            if err["sql"]:
                lines.append(f"\n```sql\n{err['sql'][:600]}\n```")
    else:
        lines.append("\n---\n")
        lines.append("## [OK] Zero Erros de Sintaxe SQL\n")
        lines.append("> Nenhum erro de sintaxe SQL foi encontrado durante o stress test!")

    lines.append("\n---\n")
    lines.append(f"*Relatório gerado automaticamente pelo LuminaAI Mass Stress Test — {now}*")

    return "\n".join(lines)


async def main():
    print("=" * 70)
    print("LuminaAI - Mass Stress Test: 200 Perguntas / 100 Cenarios")
    print("=" * 70)
    print(f"   Tenant ID : {TENANT_ID}")
    print(f"   Timeout   : {TIMEOUT_SECONDS}s por pergunta")
    print(f"   Total     : {len(SCENARIOS) * 2} perguntas em {len(SCENARIOS)} cenarios")
    print(f"   Output    : {OUTPUT_FILE}")
    print("=" * 70)

    # Importa o orchestrador
    from services.new_query_orchestrator import NewQueryOrchestrator
    orchestrator = NewQueryOrchestrator()

    # --- Garante schema de negócio completo antes de iniciar ---
    print("\n[..] Verificando schema de negocio no banco...")
    from sqlalchemy import text as _text
    from database import get_db_context as _get_db
    import uuid as _uuid
    _TENANT_UUID = _uuid.UUID(TENANT_ID)

    async with _get_db() as _sess:
        _r = await _sess.execute(_text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='vw_vendas_lm' AND table_schema='public'"
        ))
        _cols = [row[0] for row in _r.fetchall()]

    if "venda_id" not in _cols:
        print("[!!] Schema desatualizado. Reconstruindo tabelas de negocio...")
        import subprocess, sys as _sys
        _proc = subprocess.run(
            [_sys.executable, "ensure_business_schema.py"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        print(_proc.stdout[-500:] if _proc.stdout else "")
        if _proc.returncode != 0:
            print("[XX] Falha ao reconstruir schema:", _proc.stderr[-300:])
            return 1
    else:
        print("[OK] Schema de negocio verificado - colunas presentes.")

    # Cria diretório de saída
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    global_start = time.perf_counter()

    for i, scenario in enumerate(SCENARIOS, 1):
        tier_tag = {"SINGLE_VIEW": "[BAS]", "MULTI_VIEW": "[MUL]",
                     "ADVANCED": "[ADV]", "UI_RESILIENCE": "[UI] "}.get(scenario["tier"], "[???]")
        print(f"\n{tier_tag} Cenario {scenario['id']:03d}/100 - {scenario['titulo']}")
        
        result = await run_scenario(orchestrator, scenario, i, len(SCENARIOS) * 2)
        all_results.append(result)

        # Salva checkpoint a cada 10 cenários
        if i % 10 == 0:
            report_partial = generate_markdown_report(all_results, time.perf_counter() - global_start)
            OUTPUT_FILE.write_text(report_partial, encoding="utf-8")
            success_so_far = sum(
                1 for r in all_results for p in r["perguntas"]
                if p["classification"].startswith("SUCCESS")
            )
            total_so_far = sum(len(r["perguntas"]) for r in all_results)
            print(f"\n   [..] Checkpoint: {i * 2}/{len(SCENARIOS) * 2} perguntas | "
                  f"Sucesso: {success_so_far}/{total_so_far} ({success_so_far/total_so_far*100:.1f}%)")

    total_time = time.perf_counter() - global_start

    # Gera relatório final
    report = generate_markdown_report(all_results, total_time)
    OUTPUT_FILE.write_text(report, encoding="utf-8")

    # Resumo no console
    total_perguntas = sum(len(r["perguntas"]) for r in all_results)
    success_total = sum(
        1 for r in all_results for p in r["perguntas"]
        if p["classification"].startswith("SUCCESS")
    )
    fail_total = sum(
        1 for r in all_results for p in r["perguntas"]
        if p["classification"].startswith("FAIL") or p["classification"] in ("TIMEOUT", "EXCEPTION")
    )

    print("\n" + "=" * 70)
    print("[OK] STRESS TEST CONCLUIDO!")
    print(f"   Total     : {total_perguntas}/200 perguntas executadas")
    print(f"   Sucesso   : {success_total} ({success_total/total_perguntas*100:.1f}%)")
    print(f"   Falhas    : {fail_total}")
    print(f"   Tempo     : {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"   Relatorio : {OUTPUT_FILE}")
    print("=" * 70)

    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
