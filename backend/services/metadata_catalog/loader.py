import logging
from typing import List, Dict, Any
from services.metadata_catalog.models import (
    CorporateCatalog, ViewMetadata, ColumnMetadata, ViewType, ColumnDataType,
    AggregationType, RelationshipMetadata, BusinessEntityMetadata, MetricMetadata,
    DimensionMetadata, AliasMetadata
)
from services.metadata_catalog.catalog import set_corporate_catalog

logger = logging.getLogger("luminaai.services.metadata_catalog.loader")

def load_corporate_catalog() -> CorporateCatalog:
    """
    Carrega estaticamente todas as views, colunas, chaves, relacionamentos,
    entidades de negócio, métricas, dimensões e aliases do LuminaAI de forma estruturada.
    Fácil de estender e consumir por planners analíticos.
    """
    logger.info("Iniciando carregamento do Corporate Knowledge Catalog (CKC)...")
    
    # 1. Definição das Views
    views: Dict[str, ViewMetadata] = {}

    # 1.1 VW_CLIENTES_CAD_LM
    vw_clientes_cols = {
        "codigo": ColumnMetadata(
            physical_name="codigo", friendly_name="Código Cliente", description="Identificador único do cliente",
            data_type=ColumnDataType.NUMERIC, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "cnpj_cpf": ColumnMetadata(
            physical_name="cnpj_cpf", friendly_name="CNPJ/CPF", description="Documento do cliente",
            data_type=ColumnDataType.TEXT, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "nome": ColumnMetadata(
            physical_name="nome", friendly_name="Nome Cliente", description="Razão social do cliente",
            data_type=ColumnDataType.TEXT, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "nome_cidade": ColumnMetadata(
            physical_name="nome_cidade", friendly_name="Cidade Cliente", description="Cidade do cliente",
            data_type=ColumnDataType.TEXT, business_entity="Cidade", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "uf": ColumnMetadata(
            physical_name="uf", friendly_name="UF Cliente", description="Estado do cliente",
            data_type=ColumnDataType.TEXT, business_entity="Estado", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "tpcli": ColumnMetadata(
            physical_name="tpcli", friendly_name="Status Cliente", description="Status do cliente (ativo/inativo)",
            data_type=ColumnDataType.TEXT, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        )
    }
    views["VW_CLIENTES_CAD_LM"] = ViewMetadata(
        name="VW_CLIENTES_CAD_LM",
        functional_description="Cadastro de clientes da empresa",
        business_description="Cadastro contendo informações de localização, documentos e status de clientes",
        purpose="Dimensão de Clientes",
        granularity="Um registro por cliente (codigo)",
        view_type=ViewType.CADASTRAL,
        columns=vw_clientes_cols,
        primary_key="codigo",
        foreign_keys={},
        related_views=["VW_VENDAS_LM", "VW_FINANCEIRO_LM"],
        relationships=[],
        required_permissions=[]
    )

    # 1.2 VW_VENDAS_LM
    vw_vendas_cols = {
        "nota_": ColumnMetadata(
            physical_name="nota_", friendly_name="Número Nota", description="Número da nota fiscal de venda",
            data_type=ColumnDataType.NUMERIC, business_entity="Venda", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "pedido_": ColumnMetadata(
            physical_name="pedido_", friendly_name="Número Pedido", description="Número do pedido comercial",
            data_type=ColumnDataType.NUMERIC, business_entity="Venda", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "codcliente_": ColumnMetadata(
            physical_name="codcliente_", friendly_name="Código Cliente", description="FK para o cliente da venda",
            data_type=ColumnDataType.NUMERIC, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "codprod_": ColumnMetadata(
            physical_name="codprod_", friendly_name="Código Produto", description="FK para o produto vendido",
            data_type=ColumnDataType.NUMERIC, business_entity="Produto", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "rca_": ColumnMetadata(
            physical_name="rca_", friendly_name="Código Vendedor", description="FK para o vendedor (RCA)",
            data_type=ColumnDataType.NUMERIC, business_entity="Vendedor", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "ptotal_": ColumnMetadata(
            physical_name="ptotal_", friendly_name="Valor Total", description="Valor total da venda do item",
            data_type=ColumnDataType.NUMERIC, business_entity="Venda", is_dimension=False, is_metric=True,
            filterable=True, groupable=False, sortable=True, chartable=True, supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX]
        ),
        "p_unit_": ColumnMetadata(
            physical_name="p_unit_", friendly_name="Preco Unitario", description="Preco unitario praticado no item da venda",
            data_type=ColumnDataType.NUMERIC, business_entity="Venda", is_dimension=False, is_metric=True,
            filterable=True, groupable=False, sortable=True, chartable=True, supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX]
        ),
        "dtemissao_": ColumnMetadata(
            physical_name="dtemissao_", friendly_name="Data Emissão", description="Data de emissão da nota fiscal",
            data_type=ColumnDataType.TIMESTAMP, business_entity="Venda", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "qtde_": ColumnMetadata(
            physical_name="qtde_", friendly_name="Quantidade", description="Quantidade vendida do produto",
            data_type=ColumnDataType.NUMERIC, business_entity="Venda", is_dimension=False, is_metric=True,
            filterable=True, groupable=False, sortable=True, chartable=True, supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX]
        ),
        "nome_": ColumnMetadata(
            physical_name="nome_", friendly_name="Nome Vendedor (Nota)", description="Nome do vendedor gravado na nota",
            data_type=ColumnDataType.TEXT, business_entity="Vendedor", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "descricao_": ColumnMetadata(
            physical_name="descricao_", friendly_name="Descrição Produto (Nota)", description="Descrição do produto gravado na nota",
            data_type=ColumnDataType.TEXT, business_entity="Produto", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "razao_": ColumnMetadata(
            physical_name="razao_", friendly_name="Razão Social (Nota)", description="Razão social do cliente gravado na nota",
            data_type=ColumnDataType.TEXT, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        )
    }
    views["VW_VENDAS_LM"] = ViewMetadata(
        name="VW_VENDAS_LM",
        functional_description="Fatos de transações de vendas de mercadorias",
        business_description="Notas fiscais e itens de pedido faturados com detalhamento de cliente, vendedor, produto, data e valores",
        purpose="Fatos de Vendas",
        granularity="Um registro por item de nota fiscal (nota_ + codprod_)",
        view_type=ViewType.TRANSACTONAL,
        columns=vw_vendas_cols,
        primary_key="nota_",
        foreign_keys={
            "Cliente": "codcliente_",
            "Produto": "codprod_",
            "Vendedor": "rca_"
        },
        related_views=["VW_CLIENTES_CAD_LM", "VW_PRODUTOS_CAD_LM", "VW_VENDEDOR_CAD_LM"],
        relationships=[],
        required_permissions=[]
    )

    # 1.3 VW_PRODUTOS_CAD_LM
    vw_produtos_cols = {
        "codigo": ColumnMetadata(
            physical_name="codigo", friendly_name="Código Produto", description="Código físico do produto",
            data_type=ColumnDataType.TEXT, business_entity="Produto", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "nome_produto": ColumnMetadata(
            physical_name="nome_produto", friendly_name="Nome Produto", description="Nome comercial curto do produto",
            data_type=ColumnDataType.TEXT, business_entity="Produto", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "familia": ColumnMetadata(
            physical_name="familia", friendly_name="Família Produto", description="Categoria/Família de agrupamento do produto",
            data_type=ColumnDataType.TEXT, business_entity="Categoria", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "descricao": ColumnMetadata(
            physical_name="descricao", friendly_name="Descrição Detalhada", description="Descrição detalhada do produto",
            data_type=ColumnDataType.TEXT, business_entity="Produto", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "estoque": ColumnMetadata(
            physical_name="estoque", friendly_name="Estoque", description="Quantidade de unidades física no estoque",
            data_type=ColumnDataType.NUMERIC, business_entity="Produto", is_dimension=False, is_metric=True,
            filterable=True, groupable=False, sortable=True, chartable=True, supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX]
        )
    }
    views["VW_PRODUTOS_CAD_LM"] = ViewMetadata(
        name="VW_PRODUTOS_CAD_LM",
        functional_description="Cadastro e estoque de produtos",
        business_description="Informações cadastrais dos produtos, sua família e estoque físico atual",
        purpose="Dimensão de Produtos",
        granularity="Um registro por produto (codigo)",
        view_type=ViewType.CADASTRAL,
        columns=vw_produtos_cols,
        primary_key="codigo",
        foreign_keys={},
        related_views=["VW_VENDAS_LM"],
        relationships=[],
        required_permissions=[]
    )

    # 1.4 VW_VENDEDOR_CAD_LM
    vw_vendedor_cols = {
        "codi_ved": ColumnMetadata(
            physical_name="codi_ved", friendly_name="Código Vendedor", description="Código identificador do vendedor",
            data_type=ColumnDataType.NUMERIC, business_entity="Vendedor", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "nome_ved": ColumnMetadata(
            physical_name="nome_ved", friendly_name="Nome Vendedor", description="Nome completo do vendedor",
            data_type=ColumnDataType.TEXT, business_entity="Vendedor", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "muni_ved": ColumnMetadata(
            physical_name="muni_ved", friendly_name="Município Atuação", description="Cidade/Município de atuação do vendedor",
            data_type=ColumnDataType.TEXT, business_entity="Cidade", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        )
    }
    views["VW_VENDEDOR_CAD_LM"] = ViewMetadata(
        name="VW_VENDEDOR_CAD_LM",
        functional_description="Cadastro de vendedores (RCA)",
        business_description="Informações cadastrais de vendedores e representantes de vendas",
        purpose="Dimensão de Vendedores",
        granularity="Um registro por vendedor (codi_ved)",
        view_type=ViewType.CADASTRAL,
        columns=vw_vendedor_cols,
        primary_key="codi_ved",
        foreign_keys={},
        related_views=["VW_VENDAS_LM"],
        relationships=[],
        required_permissions=[]
    )

    # 1.5 VW_FINANCEIRO_LM
    vw_financeiro_cols = {
        "financeiro_id": ColumnMetadata(
            physical_name="financeiro_id", friendly_name="ID Financeiro", description="Identificador único da parcela",
            data_type=ColumnDataType.NUMERIC, business_entity="Financeiro", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[AggregationType.COUNT, AggregationType.COUNT_DISTINCT]
        ),
        "cliente_id": ColumnMetadata(
            physical_name="cliente_id", friendly_name="Código Cliente", description="FK para o cliente devedor",
            data_type=ColumnDataType.NUMERIC, business_entity="Cliente", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "valor_parcela": ColumnMetadata(
            physical_name="valor_parcela", friendly_name="Valor Parcela", description="Valor da parcela financeira",
            data_type=ColumnDataType.NUMERIC, business_entity="Financeiro", is_dimension=False, is_metric=True,
            filterable=True, groupable=False, sortable=True, chartable=True, supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX]
        ),
        "status_pagamento": ColumnMetadata(
            physical_name="status_pagamento", friendly_name="Status Pagamento", description="Situação do pagamento (PAGO/PENDENTE/ATRASADO)",
            data_type=ColumnDataType.TEXT, business_entity="Financeiro", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        ),
        "data_vencimento": ColumnMetadata(
            physical_name="data_vencimento", friendly_name="Data Vencimento", description="Data de vencimento da parcela",
            data_type=ColumnDataType.TIMESTAMP, business_entity="Financeiro", is_dimension=True, is_metric=False,
            filterable=True, groupable=True, sortable=True, chartable=True, supported_aggregations=[]
        )
    }
    views["VW_FINANCEIRO_LM"] = ViewMetadata(
        name="VW_FINANCEIRO_LM",
        functional_description="Registros financeiros e parcelas",
        business_description="Demonstrativo de parcelas a receber por cliente com vencimentos e status de pagamento",
        purpose="Fatos Financeiros",
        granularity="Um registro por parcela (financeiro_id)",
        view_type=ViewType.TRANSACTONAL,
        columns=vw_financeiro_cols,
        primary_key="financeiro_id",
        foreign_keys={
            "Cliente": "cliente_id"
        },
        related_views=["VW_CLIENTES_CAD_LM"],
        relationships=[],
        required_permissions=[]
    )

    # 2. Definição dos Relacionamentos Físicos do Grafo (Relationships Graph)
    relationships = [
        RelationshipMetadata(
            source_view="VW_VENDAS_LM", source_column="codcliente_",
            target_view="VW_CLIENTES_CAD_LM", target_column="codigo",
            cardinality="N:1", is_forbidden=False, is_indirect=False, distance=1,
            description="Junção física Venda -> Cliente por código"
        ),
        RelationshipMetadata(
            source_view="VW_VENDAS_LM", source_column="codprod_",
            target_view="VW_PRODUTOS_CAD_LM", target_column="codigo",
            cardinality="N:1", is_forbidden=False, is_indirect=False, distance=1,
            description="Junção física Venda -> Produto por código (com cast de tipo)"
        ),
        RelationshipMetadata(
            source_view="VW_VENDAS_LM", source_column="rca_",
            target_view="VW_VENDEDOR_CAD_LM", target_column="codi_ved",
            cardinality="N:1", is_forbidden=False, is_indirect=False, distance=1,
            description="Junção física Venda -> Vendedor (RCA) por código"
        ),
        RelationshipMetadata(
            source_view="VW_FINANCEIRO_LM", source_column="cliente_id",
            target_view="VW_CLIENTES_CAD_LM", target_column="codigo",
            cardinality="N:1", is_forbidden=False, is_indirect=False, distance=1,
            description="Junção física Financeiro -> Cliente por código"
        )
    ]
    
    # Adiciona os relacionamentos de volta às views
    for rel in relationships:
        views[rel.source_view].relationships.append(rel)
        # O JOIN também é bidirecional de forma lógica (aresta reversa)
        reverse_rel = RelationshipMetadata(
            source_view=rel.target_view, source_column=rel.target_column,
            target_view=rel.source_view, target_column=rel.source_column,
            cardinality="1:N" if rel.cardinality == "N:1" else "N:1",
            is_forbidden=rel.is_forbidden, is_indirect=rel.is_indirect,
            distance=rel.distance, description=f"Reverso: {rel.description}"
        )
        views[rel.target_view].relationships.append(reverse_rel)

    # 3. Definição das Entidades de Negócio (Business Entities)
    entities: Dict[str, BusinessEntityMetadata] = {
        "Cliente": BusinessEntityMetadata(
            name="Cliente",
            views=["VW_CLIENTES_CAD_LM", "VW_VENDAS_LM", "VW_FINANCEIRO_LM"],
            columns=["VW_CLIENTES_CAD_LM.codigo", "VW_CLIENTES_CAD_LM.nome", "VW_CLIENTES_CAD_LM.tpcli", "VW_VENDAS_LM.codcliente_", "VW_VENDAS_LM.razao_"],
            relationships=["Venda", "Financeiro"],
            metrics=[],
            dimensions=["nome", "tpcli", "razao_"]
        ),
        "Produto": BusinessEntityMetadata(
            name="Produto",
            views=["VW_PRODUTOS_CAD_LM", "VW_VENDAS_LM"],
            columns=["VW_PRODUTOS_CAD_LM.codigo", "VW_PRODUTOS_CAD_LM.nome_produto", "VW_VENDAS_LM.codprod_", "VW_VENDAS_LM.descricao_"],
            relationships=["Venda"],
            metrics=["estoque"],
            dimensions=["nome_produto", "descricao", "descricao_"]
        ),
        "Venda": BusinessEntityMetadata(
            name="Venda",
            views=["VW_VENDAS_LM"],
            columns=["VW_VENDAS_LM.nota_", "VW_VENDAS_LM.pedido_", "VW_VENDAS_LM.ptotal_", "VW_VENDAS_LM.p_unit_", "VW_VENDAS_LM.qtde_", "VW_VENDAS_LM.dtemissao_"],
            relationships=["Cliente", "Produto", "Vendedor"],
            metrics=["ptotal_", "qtde_", "p_unit_"],
            dimensions=["dtemissao_", "nota_"]
        ),
        "Vendedor": BusinessEntityMetadata(
            name="Vendedor",
            views=["VW_VENDEDOR_CAD_LM", "VW_VENDAS_LM"],
            columns=["VW_VENDEDOR_CAD_LM.codi_ved", "VW_VENDEDOR_CAD_LM.nome_ved", "VW_VENDAS_LM.rca_", "VW_VENDAS_LM.nome_"],
            relationships=["Venda"],
            metrics=[],
            dimensions=["nome_ved", "nome_"]
        ),
        "Financeiro": BusinessEntityMetadata(
            name="Financeiro",
            views=["VW_FINANCEIRO_LM"],
            columns=["VW_FINANCEIRO_LM.financeiro_id", "VW_FINANCEIRO_LM.valor_parcela", "VW_FINANCEIRO_LM.status_pagamento", "VW_FINANCEIRO_LM.data_vencimento"],
            relationships=["Cliente"],
            metrics=["valor_parcela"],
            dimensions=["status_pagamento", "data_vencimento"]
        ),
        "Cidade": BusinessEntityMetadata(
            name="Cidade",
            views=["VW_CLIENTES_CAD_LM", "VW_VENDEDOR_CAD_LM"],
            columns=["VW_CLIENTES_CAD_LM.nome_cidade", "VW_VENDEDOR_CAD_LM.muni_ved"],
            relationships=["Cliente", "Vendedor"],
            metrics=[],
            dimensions=["nome_cidade", "muni_ved"]
        ),
        "Estado": BusinessEntityMetadata(
            name="Estado",
            views=["VW_CLIENTES_CAD_LM"],
            columns=["VW_CLIENTES_CAD_LM.uf"],
            relationships=["Cliente"],
            metrics=[],
            dimensions=["uf"]
        ),
        "Categoria": BusinessEntityMetadata(
            name="Categoria",
            views=["VW_PRODUTOS_CAD_LM"],
            columns=["VW_PRODUTOS_CAD_LM.familia"],
            relationships=["Produto"],
            metrics=[],
            dimensions=["familia"]
        )
    }

    # 4. Catálogo de Métricas Canônicas (Metrics Catalog)
    metrics: Dict[str, MetricMetadata] = {
        "Receita": MetricMetadata(
            canonical_name="Receita",
            description="Faturamento bruto total em vendas",
            metric_type="Currency",
            supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX],
            physical_column="ptotal_",
            physical_view="VW_VENDAS_LM",
            unit="BRL"
        ),
        "Quantidade": MetricMetadata(
            canonical_name="Quantidade",
            description="Quantidade de itens físicos vendidos",
            metric_type="Quantity",
            supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX],
            physical_column="qtde_",
            physical_view="VW_VENDAS_LM",
            unit="un"
        ),
        "Estoque": MetricMetadata(
            canonical_name="Estoque",
            description="Posição de estoque atual física cadastrada do produto",
            metric_type="Quantity",
            supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX],
            physical_column="estoque",
            physical_view="VW_PRODUTOS_CAD_LM",
            unit="un"
        ),
        "Valor Parcela": MetricMetadata(
            canonical_name="Valor Parcela",
            description="Valor unitário ou total de parcelas financeiras em aberto/pagas",
            metric_type="Currency",
            supported_aggregations=[AggregationType.SUM, AggregationType.AVG, AggregationType.MIN, AggregationType.MAX],
            physical_column="valor_parcela",
            physical_view="VW_FINANCEIRO_LM",
            unit="BRL"
        ),
        "Ticket Médio": MetricMetadata(
            canonical_name="Ticket Médio",
            description="Valor médio de vendas realizadas",
            metric_type="Currency",
            supported_aggregations=[AggregationType.AVG],
            physical_column="ptotal_",
            physical_view="VW_VENDAS_LM",
            unit="BRL"
        ),
        "Desconto": MetricMetadata(
            canonical_name="Desconto",
            description="Valor total de desconto derivado da diferenca entre preco bruto (quantidade vezes preco unitario) e valor faturado",
            metric_type="Currency",
            supported_aggregations=[AggregationType.SUM],
            physical_column="ptotal_",
            physical_view="VW_VENDAS_LM",
            unit="BRL"
        ),
        "Desconto MÃ©dio": MetricMetadata(
            canonical_name="Desconto MÃ©dio",
            description="Desconto medio por pedido derivado da diferenca entre preco bruto (quantidade vezes preco unitario) e valor faturado",
            metric_type="Currency",
            supported_aggregations=[AggregationType.AVG],
            physical_column="ptotal_",
            physical_view="VW_VENDAS_LM",
            unit="BRL"
        ),
        "Desconto Medio": MetricMetadata(
            canonical_name="Desconto Medio",
            description="Desconto medio por pedido derivado da diferenca entre preco bruto (quantidade vezes preco unitario) e valor faturado",
            metric_type="Currency",
            supported_aggregations=[AggregationType.AVG],
            physical_column="ptotal_",
            physical_view="VW_VENDAS_LM",
            unit="BRL"
        )
    }

    # 5. Catálogo de Dimensões Canônicas (Dimensions Catalog)
    dimensions: Dict[str, DimensionMetadata] = {
        "Cliente": DimensionMetadata(
            name="Cliente", dimension_type="Entity", physical_column="nome", physical_view="VW_CLIENTES_CAD_LM", hierarchy=[]
        ),
        "Produto": DimensionMetadata(
            name="Produto", dimension_type="Entity", physical_column="nome_produto", physical_view="VW_PRODUTOS_CAD_LM", hierarchy=["familia"]
        ),
        "Vendedor": DimensionMetadata(
            name="Vendedor", dimension_type="Entity", physical_column="nome_ved", physical_view="VW_VENDEDOR_CAD_LM", hierarchy=[]
        ),
        "Cidade": DimensionMetadata(
            name="Cidade", dimension_type="Geography", physical_column="nome_cidade", physical_view="VW_CLIENTES_CAD_LM", hierarchy=["uf"]
        ),
        "Estado": DimensionMetadata(
            name="Estado", dimension_type="Geography", physical_column="uf", physical_view="VW_CLIENTES_CAD_LM", hierarchy=[]
        ),
        "Categoria": DimensionMetadata(
            name="Categoria", dimension_type="Entity", physical_column="familia", physical_view="VW_PRODUTOS_CAD_LM", hierarchy=[]
        ),
        "Data": DimensionMetadata(
            name="Data", dimension_type="Time", physical_column="dtemissao_", physical_view="VW_VENDAS_LM", hierarchy=["Mês", "Ano"]
        )
    }

    # 6. Aliases Semânticos (Aliases Catalog)
    # ReutilizaAliases estáticos mapeados nas engines para garantir consistência
    aliases_list = [
        # Aliases de Venda / Faturamento
        AliasMetadata(alias="faturamento", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento total", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento bruto", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento bruto total", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento liquido", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento líquido", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="faturamento liquido total", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="receita", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="receita total", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="valor venda", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="valor total", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="revenue", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="billing", canonical_name="Receita", category="Metric"),
        AliasMetadata(alias="desconto", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="descontos", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="total desconto", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="total de desconto", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="desconto total", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="nosso desconto", canonical_name="Desconto", category="Metric"),
        AliasMetadata(alias="desconto medio", canonical_name="Desconto Medio", category="Metric"),
        AliasMetadata(alias="desconto médio", canonical_name="Desconto Medio", category="Metric"),
        AliasMetadata(alias="venda", canonical_name="Venda", category="Entity"),
        AliasMetadata(alias="vendas", canonical_name="Venda", category="Entity"),

        # Aliases de Cliente
        AliasMetadata(alias="comprador", canonical_name="Cliente", category="Entity"),
        AliasMetadata(alias="compradores", canonical_name="Cliente", category="Entity"),
        AliasMetadata(alias="cliente", canonical_name="Cliente", category="Entity"),
        AliasMetadata(alias="clientes", canonical_name="Cliente", category="Entity"),
        
        # Aliases de Vendedor
        AliasMetadata(alias="rca", canonical_name="Vendedor", category="Entity"),
        AliasMetadata(alias="rcas", canonical_name="Vendedor", category="Entity"),
        AliasMetadata(alias="vendedor", canonical_name="Vendedor", category="Entity"),
        AliasMetadata(alias="vendedores", canonical_name="Vendedor", category="Entity"),
        AliasMetadata(alias="representante", canonical_name="Vendedor", category="Entity"),
        AliasMetadata(alias="representantes", canonical_name="Vendedor", category="Entity"),
        
        # Aliases de Produto
        AliasMetadata(alias="produto", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="produtos", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="item", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="itens", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="sku", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="skus", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="mercadoria", canonical_name="Produto", category="Entity"),
        AliasMetadata(alias="mercadorias", canonical_name="Produto", category="Entity"),

        # Aliases de Geografia (Estado / Cidade)
        AliasMetadata(alias="estado", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="estados", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="uf", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="ufs", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="regiao", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="regioes", canonical_name="Estado", category="Dimension"),
        AliasMetadata(alias="cidade", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="cidades", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="municipio", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="municipios", canonical_name="Cidade", category="Dimension"),

        # Aliases de Filial / Loja (mapeados para Cidade Cliente)
        AliasMetadata(alias="filial", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="filiais", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="loja", canonical_name="Cidade", category="Dimension"),
        AliasMetadata(alias="lojas", canonical_name="Cidade", category="Dimension")
    ]
    aliases = {a.alias: a for a in aliases_list}

    # 7. Consolidação
    catalog = CorporateCatalog(
        views=views,
        entities=entities,
        metrics=metrics,
        dimensions=dimensions,
        aliases=aliases,
        relationships=relationships
    )
    
    set_corporate_catalog(catalog)
    logger.info("Corporate Knowledge Catalog (CKC) carregado e inicializado com sucesso!")
    return catalog
