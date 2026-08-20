"""Verifica e reconstrói o schema de negócio se necessário."""
import asyncio, sys
sys.path.insert(0, '.')
from sqlalchemy import text
from database import get_db_context
import uuid

TENANT_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")

async def rebuild():
    async with get_db_context() as s:
        # Verifica estado atual
        r = await s.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='vw_vendas_lm' AND table_schema='public' "
            "ORDER BY ordinal_position"
        ))
        cols = [row[0] for row in r.fetchall()]
        print("Colunas atuais em vw_vendas_lm:", cols)

        if "venda_id" not in cols:
            print("SCHEMA DESATUALIZADO - Reconstruindo tabelas...")

            for tbl in ["vw_vendas_lm", "vw_clientes_cad_lm", "vw_produtos_cad_lm", "vw_vendedor_cad_lm"]:
                await s.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))

            await s.execute(text("""
                CREATE TABLE vw_vendas_lm (
                    venda_id TEXT, tenant_id UUID, cliente_id TEXT,
                    produto_id TEXT, vendedor_id TEXT, valor_total NUMERIC(15,2),
                    data_venda TIMESTAMP, pedido_ TEXT, codcliente_ TEXT,
                    codprod_ TEXT, rca_ TEXT, ptotal_ NUMERIC(15,2),
                    dtemissao_ TIMESTAMP, periodo TEXT, receita NUMERIC(15,2), data_ref TIMESTAMP
                )
            """))
            await s.execute(text("""
                CREATE TABLE vw_clientes_cad_lm (
                    cliente_id TEXT, tenant_id UUID, nome TEXT, cidade TEXT,
                    estado TEXT, status_cliente TEXT, codigo TEXT, nome_cidade TEXT,
                    uf TEXT, classe TEXT, cnpj_cpf TEXT,
                    periodo TEXT, receita NUMERIC(15,2), data_ref TIMESTAMP
                )
            """))
            await s.execute(text("""
                CREATE TABLE vw_produtos_cad_lm (
                    produto_id TEXT, tenant_id UUID, nome TEXT, categoria TEXT,
                    custo NUMERIC(15,2), codigo TEXT, descr_produto TEXT,
                    periodo TEXT, receita NUMERIC(15,2), data_ref TIMESTAMP
                )
            """))
            await s.execute(text("""
                CREATE TABLE vw_vendedor_cad_lm (
                    vendedor_id TEXT, tenant_id UUID, nome TEXT, regiao TEXT,
                    codi_ved TEXT, nome_vendedor TEXT,
                    periodo TEXT, receita NUMERIC(15,2), data_ref TIMESTAMP
                )
            """))

            # Clientes
            await s.execute(text("""
                INSERT INTO vw_clientes_cad_lm
                (cliente_id,tenant_id,nome,cidade,estado,status_cliente,codigo,nome_cidade,uf,classe,cnpj_cpf,periodo,receita,data_ref)
                VALUES
                ('CLI001',:t,'Joao Silva','Sao Paulo','SP','ATIVO','CLI001','Sao Paulo','SP','A','12345678000','2026-06',50000,'2026-06-30'),
                ('CLI002',:t,'Marcos Oliveira','Rio de Janeiro','RJ','ATIVO','CLI002','Rio de Janeiro','RJ','B','98765432000','2026-06',35000,'2026-06-30'),
                ('CLI003',:t,'Ana Costa','Belo Horizonte','MG','ATIVO','CLI003','Belo Horizonte','MG','A','11122233000','2026-06',75000,'2026-06-30'),
                ('CLI004',:t,'Carlos Mendes','Porto Alegre','RS','INATIVO','CLI004','Porto Alegre','RS','C','44455566000','2026-06',12000,'2026-06-30'),
                ('CLI005',:t,'Fernanda Lima','Curitiba','PR','ATIVO','CLI005','Curitiba','PR','A','77788899000','2026-06',90000,'2026-06-30')
            """), {"t": TENANT_ID})

            # Vendedores
            await s.execute(text("""
                INSERT INTO vw_vendedor_cad_lm
                (vendedor_id,tenant_id,nome,regiao,codi_ved,nome_vendedor,periodo,receita,data_ref)
                VALUES
                ('VED001',:t,'Pedro Santos','Sudeste','VED001','Pedro Santos','2026-06',150000,'2026-06-30'),
                ('VED002',:t,'Mariana Torres','Sul','VED002','Mariana Torres','2026-06',120000,'2026-06-30'),
                ('VED003',:t,'Ricardo Alves','Nordeste','VED003','Ricardo Alves','2026-06',95000,'2026-06-30')
            """), {"t": TENANT_ID})

            # Produtos
            await s.execute(text("""
                INSERT INTO vw_produtos_cad_lm
                (produto_id,tenant_id,nome,categoria,custo,codigo,descr_produto,periodo,receita,data_ref)
                VALUES
                ('PRD001',:t,'Notebook Pro','Eletronicos',2500.00,'PRD001','Notebook Pro 15','2026-06',5000,'2026-06-30'),
                ('PRD002',:t,'Smartphone Plus','Eletronicos',1200.00,'PRD002','Smartphone Plus 5G','2026-06',8000,'2026-06-30'),
                ('PRD003',:t,'Tablet Flex','Eletronicos',800.00,'PRD003','Tablet Flex 10','2026-06',3500,'2026-06-30'),
                ('PRD004',:t,'Geladeira Duplex','Eletrodomesticos',2800.00,'PRD004','Geladeira Duplex 450L','2026-06',7000,'2026-06-30'),
                ('PRD005',:t,'Sofa Retratil','Moveis',1800.00,'PRD005','Sofa Retratil 3 Lugares','2026-06',4500,'2026-06-30')
            """), {"t": TENANT_ID})

            # Vendas junho + julho
            await s.execute(text("""
                INSERT INTO vw_vendas_lm
                (venda_id,tenant_id,cliente_id,produto_id,vendedor_id,valor_total,data_venda,
                 pedido_,codcliente_,codprod_,rca_,ptotal_,dtemissao_,periodo,receita,data_ref)
                VALUES
                ('VD001',:t,'CLI001','PRD001','VED001',12500.00,'2026-06-05','VD001','CLI001','PRD001','VED001',12500.00,'2026-06-05','2026-06',12500.00,'2026-06-30'),
                ('VD002',:t,'CLI002','PRD002','VED001',6000.00,'2026-06-07','VD002','CLI002','PRD002','VED001',6000.00,'2026-06-07','2026-06',6000.00,'2026-06-30'),
                ('VD003',:t,'CLI003','PRD004','VED002',28000.00,'2026-06-10','VD003','CLI003','PRD004','VED002',28000.00,'2026-06-10','2026-06',28000.00,'2026-06-30'),
                ('VD004',:t,'CLI005','PRD001','VED002',37500.00,'2026-06-12','VD004','CLI005','PRD001','VED002',37500.00,'2026-06-12','2026-06',37500.00,'2026-06-30'),
                ('VD005',:t,'CLI003','PRD005','VED003',9000.00,'2026-06-15','VD005','CLI003','PRD005','VED003',9000.00,'2026-06-15','2026-06',9000.00,'2026-06-30'),
                ('VD006',:t,'CLI001','PRD003','VED003',4000.00,'2026-06-18','VD006','CLI001','PRD003','VED003',4000.00,'2026-06-18','2026-06',4000.00,'2026-06-30'),
                ('VD007',:t,'CLI002','PRD004','VED001',14000.00,'2026-06-20','VD007','CLI002','PRD004','VED001',14000.00,'2026-06-20','2026-06',14000.00,'2026-06-30'),
                ('VD008',:t,'CLI004','PRD002','VED003',2400.00,'2026-06-22','VD008','CLI004','PRD002','VED003',2400.00,'2026-06-22','2026-06',2400.00,'2026-06-30'),
                ('VD009',:t,'CLI005','PRD005','VED002',9000.00,'2026-06-25','VD009','CLI005','PRD005','VED002',9000.00,'2026-06-25','2026-06',9000.00,'2026-06-30'),
                ('VD010',:t,'CLI003','PRD001','VED001',25000.00,'2026-06-28','VD010','CLI003','PRD001','VED001',25000.00,'2026-06-28','2026-06',25000.00,'2026-06-30'),
                ('VD011',:t,'CLI001','PRD002','VED001',3600.00,'2026-07-14','VD011','CLI001','PRD002','VED001',3600.00,'2026-07-14','2026-07',3600.00,'2026-07-14'),
                ('VD012',:t,'CLI003','PRD001','VED002',12500.00,'2026-07-14','VD012','CLI003','PRD001','VED002',12500.00,'2026-07-14','2026-07',12500.00,'2026-07-14'),
                ('VD013',:t,'CLI005','PRD004','VED003',8400.00,'2026-07-14','VD013','CLI005','PRD004','VED003',8400.00,'2026-07-14','2026-07',8400.00,'2026-07-14')
            """), {"t": TENANT_ID})

            await s.commit()

            for tbl in ["vw_vendas_lm","vw_clientes_cad_lm","vw_produtos_cad_lm","vw_vendedor_cad_lm"]:
                r = await s.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                print(f"  {tbl}: {r.scalar()} registros")

            print("Schema reconstruido com sucesso!")
        else:
            print("Schema OK - colunas de negocio presentes")

asyncio.run(rebuild())
