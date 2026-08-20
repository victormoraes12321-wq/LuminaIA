"""
LuminaAI — Seed do Oracle Database Simulado (mock_oracle_*)
-----------------------------------------------------------
Versão Agro Realista (v4.0):
- Cria e popula 9 tabelas prefixadas com 'mock_oracle_' no Postgres local.
- Gera 320 produtos do agronegócio (sementes, defensivos, fertilizantes, tratores).
- 10 vendedores ativos com metas e rankings.
- 1 ano completo de dados (02/07/2025 até 02/07/2026) baseados em 1200 transações diárias consistentes.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import random
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("luminaai.seed_mock_oracle")

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/luminaai_db"

# ── 1. GERADORES DE DADOS REALISTAS DO AGRO ────────────────────

VENDEDORES = [
    "Bruno Souza", "Carolina Lima", "Daniela Costa", "Eduardo Santos",
    "Fernanda Dias", "Gabriel Rocha", "Helena Azevedo", "Igor Martins",
    "Juliana Reis", "Lucas Pires"
]

CLIENTES_AGRO = [
    ("Fazenda Sol Nascente", "contato@solnascente.com.br", "(34) 99122-3344", "Uberlândia", "MG"),
    ("Agropecuária Vale Verde", "financeiro@valeverde.com.br", "(16) 98111-2233", "Ribeirão Preto", "SP"),
    ("Cooperativa AgroIndustrial", "suprimentos@coopagro.com.br", "(43) 99655-4433", "Londrina", "PR"),
    ("Fazenda Três Corações", "gerencia@trescoracoes.agr.br", "(66) 99200-8877", "Sorriso", "MT"),
    ("Grupo Agrícola Terra Nova", "compras@terranova.com.br", "(62) 99444-5566", "Rio Verde", "GO"),
    ("Sítio Santa Rita", "santarita@sitio.com.br", "(19) 98777-6655", "Piracicaba", "SP"),
    ("Fazenda Bela Vista", "contato@belavista.agr.br", "(67) 99111-9988", "Dourados", "MS"),
    ("Agro Pampa", "financeiro@agropampa.com.br", "(55) 98122-4455", "Passo Fundo", "RS"),
    ("Fazenda São Francisco", "saofrancisco@agro.com.br", "(84) 98833-2211", "Mossoró", "RN"),
    ("Fazenda Boa Esperança", "boaesperanca@gmail.com", "(77) 99911-3322", "Barreiras", "BA"),
    ("Agropecuária Cantagalo", "cantagalo@terra.com.br", "(35) 98822-1100", "Alfenas", "MG"),
    ("Fazenda Estrela do Sul", "estreladosul@hotmail.com", "(65) 99233-4455", "Lucas do Rio Verde", "MT"),
    ("Canaã Agronegócios", "comercial@canaaagro.com.br", "(17) 99144-5566", "São José do Rio Preto", "SP"),
    ("Fazenda Recanto Verde", "recantoverde@uol.com.br", "(44) 98877-2233", "Maringá", "PR"),
    ("Fazenda Primavera", "primavera@gmail.com", "(64) 99611-2233", "Jataí", "GO")
]

FORMAS_PAGAMENTO = ["Crédito Agrícola", "PIX", "Boleto 60 Dias", "Boleto 30 Dias", "Transferência Bancária"]
STATUS_VENDAS = ["APROVADO", "APROVADO", "APROVADO", "APROVADO", "CANCELADO"]

def gerar_catalogo_produtos() -> list[dict]:
    """Gera 320 produtos do agronegócio divididos em 6 subcategorias."""
    categorias = {
        "Sementes e Mudas": [
            ("Semente de Soja", 45.0, 95.0),
            ("Semente de Milho Híbrido", 65.0, 140.0),
            ("Semente de Algodão Transgênico", 90.0, 210.0),
            ("Semente de Trigo Selecionado", 30.0, 68.0),
            ("Mudas de Café Catuaí Vermelho", 12.0, 28.0),
            ("Semente de Sorgo Granífero", 22.0, 48.0),
            ("Semente de Arroz Irrigado", 25.0, 55.0),
            ("Semente de Capim Pastagem Brachiaria", 15.0, 35.0)
        ],
        "Fertilizantes e Adubos": [
            ("Fertilizante NPK 04-14-08 Bag 1t", 1500.0, 2400.0),
            ("Fertilizante NPK 20-00-20 Bag 1t", 1700.0, 2700.0),
            ("Ureia Agrícola Premium SC 50kg", 110.0, 185.0),
            ("Superfosfato Simples SC 50kg", 95.0, 160.0),
            ("Calcário Agrícola Dolemítico t", 80.0, 140.0),
            ("Gesso Agrícola Granulado t", 120.0, 210.0),
            ("Adubo Orgânico Compostado SC 40kg", 35.0, 65.0),
            ("Micronutrientes Quelatados SC 20kg", 180.0, 310.0)
        ],
        "Defensivos e Químicos": [
            ("Herbicida Glifosato Concentrado 20L", 320.0, 580.0),
            ("Inseticida Integrado Lagartas 5L", 450.0, 820.0),
            ("Fungicida Protetor Ferrugem 10L", 600.0, 1100.0),
            ("Acaricida de Contato Frasco 1L", 150.0, 280.0),
            ("Adjuvante Espalhador Adesivo 5L", 80.0, 150.0),
            ("Tratamento de Sementes Inseticida 5L", 380.0, 690.0),
            ("Desfolhante Regulador de Crescimento 5L", 210.0, 390.0),
            ("Fungicida Sistêmico Premium 5L", 520.0, 950.0)
        ],
        "Nutrição Animal": [
            ("Ração Bovino de Corte Engorda SC 40kg", 65.0, 115.0),
            ("Suplemento Mineral Fósforo SC 30kg", 90.0, 160.0),
            ("Ração Bovino de Leite Lactação SC 40kg", 70.0, 125.0),
            ("Sal Mineralizado Pastagem Seca SC 25kg", 55.0, 98.0),
            ("Ração Potros Crescimento Premium SC 30kg", 85.0, 150.0),
            ("Suplemento Vitamínico Aves SC 20kg", 120.0, 210.0),
            ("Ração Leitão Desmame SC 25kg", 75.0, 130.0),
            ("Núcleo Mineral Confinamento SC 25kg", 140.0, 240.0)
        ],
        "Equipamentos e Irrigação": [
            ("Pivô Central de Irrigação 50ha", 120000.0, 195000.0),
            ("Kit Irrigação por Gotejamento 1ha", 4500.0, 7800.0),
            ("Bomba Centrífuga Trifásica 15HP", 2800.0, 4900.0),
            ("Aspersor de Impacto Latão Unid", 35.0, 68.0),
            ("Mangueira PEBD Irrigação Rolo 100m", 150.0, 270.0),
            ("Filtro de Areia Limpeza de Água", 1800.0, 3200.0),
            ("Painel Eletrônico Controle Pivô", 3500.0, 6200.0),
            ("Kit Tubulação Alumínio Acoplamento Quick", 5200.0, 9100.0)
        ],
        "Máquinas e Tratores": [
            ("Trator Cabinada 110CV", 180000.0, 290000.0),
            ("Colheitadeira de Grãos Multicereais", 320000.0, 480000.0),
            ("Pulverizador Autopropelido 2000L", 150000.0, 245000.0),
            ("Semeadora Adubadora Mecânica 9 Linhas", 48000.0, 82000.0),
            ("Grade Aradora Controle Remoto 16 Discos", 18000.0, 31000.0),
            ("Ensiladeira Acoplada para Milho/Capim", 12000.0, 21500.0),
            ("Roçadeira Hidráulica Agrícola Pro", 4500.0, 7900.0),
            ("Carreta Agrícola Metálica 6 Toneladas", 9500.0, 16500.0)
        ]
    }

    random.seed(12345)
    catalogo = []
    prod_id = 1
    
    for cat_name, base_items in categorias.items():
        for base_name, preco_custo, preco_venda in base_items:
            marcas = ["Forte", "Ouro", "AgroMax", "Bio", "Cerrado", "Pampa", "Premium"]
            for i, marca in enumerate(marcas):
                nome_completo = f"{base_name} {marca}"
                
                fator = 0.85 + (i * 0.05)
                pc_var = round(preco_custo * fator, 2)
                pv_var = round(preco_venda * fator, 2)
                
                estoque_atual = random.randint(10, 800)
                if pv_var > 50000:
                    estoque_atual = random.randint(1, 8)
                
                estoque_min = max(int(estoque_atual * 0.25), 1)
                
                catalogo.append({
                    "id": str(prod_id),
                    "produto": nome_completo,
                    "categoria": cat_name,
                    "preco_custo": pc_var,
                    "preco_venda": pv_var,
                    "estoque_atual": estoque_atual,
                    "estoque_minimo": estoque_min
                })
                prod_id += 1
                
    return catalogo

async def run_seed():
    logger.info("Iniciando criação de tabelas simuladas do Oracle (Cenário Agro)...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        catalogo_produtos = gerar_catalogo_produtos()
        logger.info("Catalogo Agro gerado com sucesso: %d produtos", len(catalogo_produtos))
        
        random.seed(2026)
        start_date = datetime(2025, 7, 9)
        end_date = datetime(2026, 7, 9)
        dias_total = (end_date - start_date).days
        
        transacoes = []
        
        vendas_por_vendedor = {v: {"valor": 0.0, "pedidos": 0} for v in VENDEDORES}
        compras_por_cliente = {c[0]: {"gasto": 0.0, "compras": 0, "ultima": start_date} for c in CLIENTES_AGRO}
        vendas_por_produto = {p["produto"]: {"unidades": 0, "receita": 0.0, "custo": 0.0} for p in catalogo_produtos}
        faturamento_mensal = {}
        
        # Simula cerca de 20.000 vendas diárias consistentes no período de 1 ano
        for i in range(20000):
            dias_offset = random.randint(0, dias_total)
            data_venda = start_date + timedelta(days=dias_offset)
            vendedor = random.choice(VENDEDORES)
            cliente_info = random.choice(CLIENTES_AGRO)
            cliente = cliente_info[0]
            
            num_itens = random.randint(1, 3)
            itens_escolhidos = random.sample(catalogo_produtos, num_itens)
            
            for produto in itens_escolhidos:
                forma = random.choice(FORMAS_PAGAMENTO)
                status_v = random.choice(STATUS_VENDAS)
                
                if produto["preco_venda"] > 100000:
                    qtd = 1
                elif produto["preco_venda"] > 1000:
                    qtd = random.randint(1, 5)
                else:
                    qtd = random.randint(5, 50)
                
                valor_total = round(produto["preco_venda"] * qtd, 2)
                custo_total = round(produto["preco_custo"] * qtd, 2)
                
                if status_v == "CANCELADO":
                    valor_total = 0.0
                    custo_total = 0.0
                
                transacoes.append((
                    float(data_venda.month),
                    float(data_venda.year),
                    float(valor_total) if status_v != "CANCELADO" else 0.0,
                    float(qtd),
                    forma,
                    status_v,
                    vendedor,
                    cliente,
                    data_venda
                ))
                
                if status_v == "APROVADO":
                    vendas_por_vendedor[vendedor]["valor"] += valor_total
                    vendas_por_vendedor[vendedor]["pedidos"] += 1
                    
                    compras_por_cliente[cliente]["gasto"] += valor_total
                    compras_por_cliente[cliente]["compras"] += 1
                    if data_venda > compras_por_cliente[cliente]["ultima"]:
                        compras_por_cliente[cliente]["ultima"] = data_venda
                    
                    vendas_por_produto[produto["produto"]]["unidades"] += qtd
                    vendas_por_produto[produto["produto"]]["receita"] += valor_total
                    vendas_por_produto[produto["produto"]]["custo"] += custo_total
                    
                    key = (data_venda.month, data_venda.year)
                    if key not in faturamento_mensal:
                        faturamento_mensal[key] = {
                            "valor": 0.0,
                            "custo": 0.0,
                            "transacoes": 0,
                            "qtd_total": 0,
                            "data": datetime(data_venda.year, data_venda.month, 1)
                        }
                    faturamento_mensal[key]["valor"] += valor_total
                    faturamento_mensal[key]["custo"] += custo_total
                    faturamento_mensal[key]["transacoes"] += 1
                    faturamento_mensal[key]["qtd_total"] += qtd

        async with conn.transaction():
            
            # ── 1. TABELA mock_oracle_vw_vendas_mensais ──
            logger.info("Criando e populando mock_oracle_vw_vendas_mensais...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_vendas_mensais CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_vendas_mensais (
                    mes NUMERIC,
                    ano NUMERIC,
                    venda_valor NUMERIC,
                    venda_quantidade NUMERIC,
                    forma_pagamento TEXT,
                    status TEXT,
                    vendedor TEXT,
                    cliente TEXT,
                    data_referencia TIMESTAMP
                );
            """)
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_vendas_mensais 
                (mes, ano, venda_valor, venda_quantidade, forma_pagamento, status, vendedor, cliente, data_referencia)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
            """, transacoes)

            # ── 2. TABELA mock_oracle_vw_performance_vendedores ──
            logger.info("Criando e populando mock_oracle_vw_performance_vendedores...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_performance_vendedores CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_performance_vendedores (
                    vendedor TEXT,
                    valor_vendido NUMERIC,
                    meta_valor NUMERIC,
                    atingimento NUMERIC,
                    comissao NUMERIC,
                    pedidos_qtd NUMERIC,
                    ranking NUMERIC
                );
            """)
            
            sorted_vendedores = sorted(
                VENDEDORES, 
                key=lambda v: vendas_por_vendedor[v]["valor"], 
                reverse=True
            )
            
            perf_vendedores_data = []
            for rk, v in enumerate(sorted_vendedores, 1):
                vendido = vendas_por_vendedor[v]["valor"]
                meta = round(random.uniform(800000.0, 1500000.0), 2)
                atingimento = round((vendido / meta) * 100, 2)
                comissao = round(vendido * 0.025, 2)
                pedidos = vendas_por_vendedor[v]["pedidos"]
                
                perf_vendedores_data.append((
                    v,
                    float(vendido),
                    float(meta),
                    float(atingimento),
                    float(comissao),
                    float(pedidos),
                    float(rk)
                ))
            
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_performance_vendedores 
                (vendedor, valor_vendido, meta_valor, atingimento, comissao, pedidos_qtd, ranking)
                VALUES ($1, $2, $3, $4, $5, $6, $7);
            """, perf_vendedores_data)

            # ── 3. TABELA mock_oracle_vw_historico_clientes ──
            logger.info("Criando e populando mock_oracle_vw_historico_clientes...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_historico_clientes CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_historico_clientes (
                    cliente TEXT,
                    email TEXT,
                    telefone TEXT,
                    cidade TEXT,
                    estado TEXT,
                    total_gasto NUMERIC,
                    compras_qtd NUMERIC,
                    ticket_medio NUMERIC,
                    ultima_compra TIMESTAMP
                );
            """)
            
            clientes_data = []
            for c_info in CLIENTES_AGRO:
                nome, email, tel, cidade, estado = c_info
                gasto = compras_por_cliente[nome]["gasto"]
                compras = compras_por_cliente[nome]["compras"]
                ticket = round(gasto / compras, 2) if compras > 0 else 0.0
                ultima = compras_por_cliente[nome]["ultima"]
                
                clientes_data.append((
                    nome,
                    email,
                    tel,
                    cidade,
                    estado,
                    float(gasto),
                    float(compras),
                    float(ticket),
                    ultima
                ))
                
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_historico_clientes 
                (cliente, email, telefone, cidade, estado, total_gasto, compras_qtd, ticket_medio, ultima_compra)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
            """, clientes_data)

            # ── 4. TABELA mock_oracle_vw_ranking_produtos ──
            logger.info("Criando e populando mock_oracle_vw_ranking_produtos...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_ranking_produtos CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_ranking_produtos (
                    produto TEXT,
                    categoria TEXT,
                    unidades_vendidas NUMERIC,
                    receita_total NUMERIC,
                    estoque_atual NUMERIC,
                    preco_medio NUMERIC,
                    margem_media NUMERIC
                );
            """)
            
            ranking_prod_data = []
            for p in catalogo_produtos:
                p_name = p["produto"]
                unidades = vendas_por_produto[p_name]["unidades"]
                receita = vendas_por_produto[p_name]["receita"]
                custo = vendas_por_produto[p_name]["custo"]
                estoque = p["estoque_atual"] - unidades
                
                if estoque < 0:
                    estoque = random.randint(5, 20)
                
                margem = round(((receita - custo) / receita * 100), 2) if receita > 0 else 30.0
                preco_med = p["preco_venda"]
                
                ranking_prod_data.append((
                    p_name,
                    p["categoria"],
                    float(unidades),
                    float(receita),
                    float(estoque),
                    float(preco_med),
                    float(margem)
                ))
            
            ranking_prod_data = sorted(ranking_prod_data, key=lambda x: x[3], reverse=True)
            
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_ranking_produtos 
                (produto, categoria, unidades_vendidas, receita_total, estoque_atual, preco_medio, margem_media)
                VALUES ($1, $2, $3, $4, $5, $6, $7);
            """, ranking_prod_data)

            # ── 5. TABELA mock_oracle_vw_estoque_produtos ──
            logger.info("Criando e populando mock_oracle_vw_estoque_produtos...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_estoque_produtos CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_estoque_produtos (
                    produto TEXT,
                    categoria TEXT,
                    estoque_atual NUMERIC,
                    estoque_minimo NUMERIC,
                    preco_custo NUMERIC,
                    preco_venda NUMERIC,
                    dias_cobertura NUMERIC,
                    status_alerta TEXT
                );
            """)
            
            estoque_data = []
            for p in catalogo_produtos:
                p_name = p["produto"]
                unidades_vend = vendas_por_produto[p_name]["unidades"]
                estoque = p["estoque_atual"] - unidades_vend
                if estoque < 0:
                    estoque = random.randint(5, 20)
                
                demanda_diaria = unidades_vend / 365
                dias_cob = round(estoque / demanda_diaria) if demanda_diaria > 0 else 999
                
                est_min = p["estoque_minimo"]
                status_alerta = "ESTÁVEL"
                if estoque < est_min:
                    status_alerta = "ESTOQUE CRÍTICO"
                elif estoque < (est_min * 1.5):
                    status_alerta = "ALERTA"
                
                estoque_data.append((
                    p_name,
                    p["categoria"],
                    float(estoque),
                    float(est_min),
                    float(p["preco_custo"]),
                    float(p["preco_venda"]),
                    float(dias_cob),
                    status_alerta
                ))
                
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_estoque_produtos 
                (produto, categoria, estoque_atual, estoque_minimo, preco_custo, preco_venda, dias_cobertura, status_alerta)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
            """, estoque_data)

            # ── 6. TABELA mock_oracle_vw_metas_vendedores ──
            logger.info("Criando e populando mock_oracle_vw_metas_vendedores...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_metas_vendedores CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_metas_vendedores (
                    vendedor TEXT,
                    mes NUMERIC,
                    ano NUMERIC,
                    meta_valor NUMERIC,
                    valor_atingido NUMERIC,
                    status TEXT
                );
            """)
            
            metas_data = []
            for ano in [2025, 2026]:
                meses = range(7, 13) if ano == 2025 else range(1, 8)
                for mes in meses:
                    vendas_no_mes = {v: 0.0 for v in VENDEDORES}
                    for tx in transacoes:
                        if tx[0] == mes and tx[1] == ano and tx[5] == "APROVADO":
                            vendas_no_mes[tx[6]] += tx[2]
                    
                    for v in VENDEDORES:
                        meta = round(random.uniform(70000.0, 130000.0), 2)
                        realizado = round(vendas_no_mes[v], 2)
                        status_m = "METAS ATINGIDAS" if realizado >= meta else "PENDENTE"
                        
                        metas_data.append((
                            v,
                            float(mes),
                            float(ano),
                            float(meta),
                            float(realizado),
                            status_m
                        ))
                        
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_metas_vendedores 
                (vendedor, mes, ano, meta_valor, valor_atingido, status)
                VALUES ($1, $2, $3, $4, $5, $6);
            """, metas_data)

            # ── 7. TABELA mock_oracle_vw_faturamento_mensal ──
            logger.info("Criando e populando mock_oracle_vw_faturamento_mensal...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_faturamento_mensal CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_faturamento_mensal (
                    mes NUMERIC,
                    ano NUMERIC,
                    faturamento_realizado NUMERIC,
                    meta_mensal NUMERIC,
                    atingimento_meta NUMERIC,
                    crescimento_vs_anterior NUMERIC,
                    transacoes_qtd NUMERIC,
                    ticket_medio NUMERIC,
                    data_referencia TIMESTAMP
                );
            """)
            
            faturamento_mensal_data = []
            ordenado_meses = sorted(faturamento_mensal.keys(), key=lambda x: (x[1], x[0]))
            
            fat_anterior = None
            for idx, key in enumerate(ordenado_meses):
                mes, ano = key
                valor = faturamento_mensal[key]["valor"]
                transacoes_qtd = faturamento_mensal[key]["transacoes"]
                data_ref = faturamento_mensal[key]["data"]
                
                meta_global = 900000.0
                atingimento = round((valor / meta_global) * 100, 2)
                ticket = round(valor / transacoes_qtd, 2) if transacoes_qtd > 0 else 0.0
                
                crescimento = 0.0
                if idx > 0 and fat_anterior > 0:
                    crescimento = round(((valor - fat_anterior) / fat_anterior) * 100, 2)
                
                faturamento_mensal_data.append((
                    float(mes),
                    float(ano),
                    float(round(valor, 2)),
                    float(meta_global),
                    float(atingimento),
                    float(crescimento),
                    float(transacoes_qtd),
                    float(ticket),
                    data_ref
                ))
                fat_anterior = valor
                
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_faturamento_mensal 
                (mes, ano, faturamento_realizado, meta_mensal, atingimento_meta, crescimento_vs_anterior, transacoes_qtd, ticket_medio, data_referencia)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
            """, faturamento_mensal_data)

            # ── 8. TABELA mock_oracle_vw_kpi_executivo ──
            logger.info("Criando e populando mock_oracle_vw_kpi_executivo...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_kpi_executivo CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_kpi_executivo (
                    metrica TEXT,
                    valor NUMERIC,
                    valor_formatado TEXT,
                    tendencia TEXT,
                    trend_label TEXT,
                    comparativo_anterior TEXT
                );
            """)
            
            receita_total = sum(v["receita"] for v in vendas_por_produto.values())
            custo_total = sum(v["custo"] for v in vendas_por_produto.values())
            transacoes_totais = len([t for t in transacoes if t[5] == "APROVADO"])
            t_medio = receita_total / transacoes_totais if transacoes_totais > 0 else 0.0
            margem_global = round(((receita_total - custo_total) / receita_total) * 100, 2) if receita_total > 0 else 35.0
            
            kpis_agro = [
                ("Receita Total", receita_total, f"R$ {receita_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "up", "+15.8% vs ano anterior", "R$ 11.240.500,00"),
                ("Ticket Médio", t_medio, f"R$ {t_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "up", "+6.2% vs ano anterior", "R$ 9.230,00"),
                ("Pedidos Atendidos", float(transacoes_totais), f"{transacoes_totais}", "up", "+9.4% vs ano anterior", "1.900"),
                ("Margem Global", margem_global, f"{margem_global}%", "stable", "estável", "36.5%")
            ]
            
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_kpi_executivo 
                (metrica, valor, valor_formatado, tendencia, trend_label, comparativo_anterior)
                VALUES ($1, $2, $3, $4, $5, $6);
            """, [(m, float(v), vf, t, tl, ca) for m, v, vf, t, tl, ca in kpis_agro])

            # ── 9. TABELA mock_oracle_vw_lojas_regioes ──
            logger.info("Criando e populando mock_oracle_vw_lojas_regioes...")
            await conn.execute("DROP TABLE IF EXISTS mock_oracle_vw_lojas_regioes CASCADE;")
            await conn.execute("""
                CREATE TABLE mock_oracle_vw_lojas_regioes (
                    loja TEXT,
                    cidade TEXT,
                    regiao TEXT,
                    faturamento NUMERIC,
                    meta NUMERIC,
                    atingimento NUMERIC
                );
            """)
            
            polos_agro = [
                ("Pólo Cerrado (Rio Verde)", "Rio Verde", "Centro-Oeste", receita_total * 0.45, receita_total * 0.42),
                ("Pólo Sudeste (Ribeirão Preto)", "Ribeirão Preto", "Sudeste", receita_total * 0.30, receita_total * 0.32),
                ("Pólo Sul (Passo Fundo)", "Passo Fundo", "Sul", receita_total * 0.25, receita_total * 0.24)
            ]
            
            lojas_data = []
            for loja, cidade, regiao, fat, met in polos_agro:
                ating = round((fat / met) * 100, 2)
                lojas_data.append((
                    loja,
                    cidade,
                    regiao,
                    float(round(fat, 2)),
                    float(round(met, 2)),
                    float(ating)
                ))
                
            await conn.executemany("""
                INSERT INTO mock_oracle_vw_lojas_regioes 
                (loja, cidade, regiao, faturamento, meta, atingimento)
                VALUES ($1, $2, $3, $4, $5, $6);
            """, lojas_data)

        logger.info("✅ Todas as 9 tabelas do Oracle Simulado (Cenário Agro) criadas e populadas com sucesso!")
        
    except Exception as exc:
        logger.exception("❌ Erro ao rodar sementes do Oracle Simulado: %s", exc)
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_seed())
