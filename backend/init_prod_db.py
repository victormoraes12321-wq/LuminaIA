import os
import sys
import asyncio
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

# Adiciona o diretório atual ao path para importar as configurações e o hashing
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from services.auth_service import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("luminaai.init_prod_db")


async def init_database():
    logger.info("Iniciando processo de inicialização do Banco de Dados de Produção...")
    
    # 1. Carrega a string de conexão
    db_url = settings.DATABASE_URL
    if not db_url or "luminaai_test" in db_url:
        logger.warning("ALERTA: O DATABASE_URL atual aponta para o banco de testes.")
    
    logger.info("Conectando ao banco de dados: %s", db_url.split("@")[-1])
    
    # 2. Cria a engine assíncrona
    engine = create_async_engine(db_url, echo=False)
    
    # 3. Carrega o script init.sql
    init_sql_path = Path(__file__).parent / "database" / "init.sql"
    if not init_sql_path.exists():
        logger.error("Arquivo SQL de inicialização não encontrado: %s", init_sql_path)
        sys.exit(1)
        
    with open(init_sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    # 4. Executa a DDL/DML no banco de dados
    try:
        async with engine.begin() as conn:
            logger.info("Executando o script DDL/DML (init.sql) no banco de dados...")
            # PostgreSQL suporta a execução de múltiplos comandos em bloco pelo protocolo simples
            await conn.execute(text(sql_content))
            logger.info("✅ DDL do banco de dados criada com sucesso!")
            
            # 5. Gera o hash dinâmico do admin para ti@casadocampo.vet.br
            logger.info("Gerando hash seguro Bcrypt para a senha padrão do Admin...")
            admin_password = "H0llyw00d26"
            admin_hash = get_password_hash(admin_password)
            
            # 6. Atualiza o banco com a senha correta criptografada
            logger.info("Salvando credenciais criptografadas do administrador no banco...")
            update_stmt = text("""
                UPDATE users 
                SET password_hash = :hash_val,
                    must_change_password = FALSE
                WHERE email = 'ti@casadocampo.vet.br';
            """)
            await conn.execute(update_stmt, {"hash_val": admin_hash})
            logger.info("✅ Administrador ti@casadocampo.vet.br configurado com sucesso (Troca de senha obrigatória desativada).")
            
    except Exception as exc:
        logger.critical("❌ Erro fatal durante a inicialização do banco de dados: %s", exc)
        sys.exit(1)
    finally:
        await engine.dispose()
        
    logger.info("================================================================")
    logger.info("🎉 BANCO DE DADOS DE PRODUÇÃO INICIALIZADO COM SUCESSO!")
    logger.info("================================================================")


if __name__ == "__main__":
    asyncio.run(init_database())
