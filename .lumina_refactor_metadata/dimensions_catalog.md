# Dimensions Catalog — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## Resumo das Dimensões Ativas

| Dimensão Lógica | Dimensão Física | View de Origem | Tipo Físico | Tipo de Dados de Negócio |
|-----------------|-----------------|----------------|-------------|-------------------------|
| Cliente | `nome` | VW_CLIENTES_CAD_LM | text | Razão Social / Nome do Cliente |
| Cidade | `nome_cidade` | VW_CLIENTES_CAD_LM | text | Cidade do Cliente |
| UF / Estado | `uf` | VW_CLIENTES_CAD_LM | text | Unidade Federativa |
| Status Cliente | `tpcli` | VW_CLIENTES_CAD_LM | text | Tipo/Status do Cliente |
| CNPJ/CPF | `cnpj_cpf` | VW_CLIENTES_CAD_LM | text | Documento Fiscal |
| Produto | `nome_produto` | VW_PRODUTOS_CAD_LM | text | Nome curto do Produto |
| Categoria | `familia` | VW_PRODUTOS_CAD_LM | text | Categoria / Família do Produto |
| Descrição Produto | `descricao` | VW_PRODUTOS_CAD_LM | text | Descrição Técnica do Produto |
| Vendedor | `nome_ved` | VW_VENDEDOR_CAD_LM | text | Nome do Vendedor/Representante |
| Cidade Vendedor | `muni_ved` | VW_VENDEDOR_CAD_LM | text | Cidade de Atuação do Vendedor |
| Data Emissão | `dtemissao_` | VW_VENDAS_LM | timestamp | Data da Venda / Emissão da Nota |
| Razão Nota | `razao_` | VW_VENDAS_LM | text | Razão Social gravada na Nota |
| Vendedor Nota | `nome_` | VW_VENDAS_LM | text | Nome do Vendedor gravado na Nota |
| Produto Nota | `descricao_` | VW_VENDAS_LM | text | Nome do Produto gravado na Nota |
| Status Pagamento | `status_pagamento` | VW_FINANCEIRO_LM | text | Status de Pagamento da Parcela |
| Vencimento | `data_vencimento` | VW_FINANCEIRO_LM | timestamp | Data de Vencimento da Parcela |

---

## 1. Dimensão: Cliente (Customer Dimension)

### Logical Entity: `Cliente`
Mapeia a entidade canônica "Cliente" para fins de análise geográfica, de status e segmentação.

### Colunas Relacionadas
- **`codigo`**: Chave primária. Usada para JOINs.
- **`nome`**: Nome principal / Razão Social do cliente. Mapeado via aliases `nome_cliente`, `cliente_nome`.
- **`nome_cidade`**: Mapeada via aliases `cidade`, `municipio`.
- **`uf`**: Mapeada via aliases `estado`, `localizacao`, `regiao`.
- **`tpcli`**: Mapeada via aliases `status`, `status_cliente`, `tipo_cliente`.
- **`cnpj_cpf`**: CNPJ ou CPF formatado.

---

## 2. Dimensão: Produto (Product Dimension)

### Logical Entity: `Produto`
Mapeia o cadastro de produtos.

### Colunas Relacionadas
- **`codigo`**: Chave primária (`text`). Usada para JOIN com a fato de vendas.
- **`nome_produto`**: Nome fantasia do produto. Mapeado via aliases `nome`, `produto_nome`, `produto`.
- **`familia`**: Classificação de agrupamento. Mapeada via aliases `categoria`, `categoria_produto`.
- **`descricao`**: Descrição do produto cadastrado. Mapeada via aliases `descr_produto`, `desc_produto`.

---

## 3. Dimensão: Vendedor (Seller Dimension)

### Logical Entity: `Vendedor`
Mapeia o cadastro de vendedores corporativos (RCA).

### Colunas Relacionadas
- **`codi_ved`**: Chave primária. Usada para JOIN.
- **`nome_ved`**: Nome completo do vendedor. Mapeado via aliases `nome`, `nome_vendedor`, `vendedor_nome`, `vendedor`.
- **`muni_ved`**: Município/região onde o vendedor atua. Mapeado via aliases `regiao`.

---

## 4. Dimensão: Tempo (Time Dimension)

### Logical Entity: `Tempo`
Mapeada dinamicamente sobre campos de data. O principal gerador temporal é `dtemissao_` da view de vendas.

### Colunas Relacionadas
- **`dtemissao_`** (`VW_VENDAS_LM`): Data em que a transação ocorreu. Mapeada via aliases `mes`, `ano`, `data`, `data_venda`, `dtemissao`, `data_pedido`, `dt_emissao`, `data_referencia`, `data_ref`, `trimestre`, `semestre`.

### Funções Temporais Extraídas no `translate_expression`
- **Trimestre**: `EXTRACT(QUARTER FROM VW_VENDAS_LM.dtemissao_)`
- **Mês**: `EXTRACT(MONTH FROM VW_VENDAS_LM.dtemissao_)`
- **Ano**: `EXTRACT(YEAR FROM VW_VENDAS_LM.dtemissao_)`
- **Dia**: `VW_VENDAS_LM.dtemissao_`

---

## 5. Dimensão: Financeiro (Financial Dimension)

### Logical Entity: `Financeiro`
Mapeia parcelas e pendências financeiras.

### Colunas Relacionadas
- **`status_pagamento`**: Status de pagamento (PAGO, PENDENTE, ATRASADO). Mapeado via aliases `status`.
- **`data_vencimento`**: Data de vencimento da parcela.

---

## ⚠️ ACHADOS & RISCOS DE AUDITORIA EM DIMENSÕES

1. **Denormalização na View de Fatos (`VW_VENDAS_LM`)**:
   As colunas `nome_` (vendedor), `descricao_` (produto) e `razao_` (cliente) vêm pré-joinadas na view física de fatos.
   - **Risco**: A IA pode usar estes campos diretamente em vez de fazer JOIN com as tabelas de cadastro (`VW_CLIENTES_CAD_LM`, `VW_PRODUTOS_CAD_LM`), o que mascara problemas de JOIN nos testes analíticos, mas causa inconsistência caso o cadastro mude retroativamente (nome atualizado vs nome gravado na nota).

2. **Diferenças de Tipos de Dados nos JOINs**:
   - `VW_VENDAS_LM.codprod_` é do tipo `numeric`.
   - `VW_PRODUTOS_CAD_LM.codigo` é do tipo `text`.
   - **Implicação**: Exige o cast implícito de tipo (`::text`) implementado em `query_optimizer_engine.py` para evitar `operator does not exist: text = numeric`.

3. **Aliases Redundantes/Falsos Positivos**:
   - `regiao` mapeia para `uf` em clientes, mas para `muni_ved` em vendedores. O resolvedor pode se confundir em queries sem qualificação explícita da entidade.

---

*Auditoria estática — nenhum arquivo modificado.*
