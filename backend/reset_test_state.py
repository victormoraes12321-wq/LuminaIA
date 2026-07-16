"""
Reseta o estado do admin para o estado inicial de testes:
- must_change_password = TRUE
- password_hash = hash de AdminLumina@2026
Remove usuario de teste joao.consulta se existir.
"""
import sys
import asyncio
sys.path.insert(0, '.')

from database import engine
from sqlalchemy import text
from services.auth_service import get_password_hash

SENHA_INICIAL = "AdminLumina@2026"

async def reset_test_state():
    hash_admin = get_password_hash(SENHA_INICIAL)
    hash_ti = get_password_hash("H0llyw00d26")
    
    async with engine.begin() as conn:
        # Garantir/Resetar o admin@luminaai.demo de teste
        await conn.execute(text("""
            INSERT INTO users (tenant_id, nome, email, password_hash, role, must_change_password)
            VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Administrador Demo', 'admin@luminaai.demo', :hash, 'ADMIN', TRUE)
            ON CONFLICT (email, tenant_id)
            DO UPDATE SET password_hash = EXCLUDED.password_hash,
                          must_change_password = TRUE,
                          atualizado_em = NOW()
        """), {"hash": hash_admin})
        
        # Garantir/Resetar o ti@casadocampo.vet.br de produção/homologação
        await conn.execute(text("""
            INSERT INTO users (tenant_id, nome, email, password_hash, role, must_change_password)
            VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Administrador LuminaAI', 'ti@casadocampo.vet.br', :hash, 'ADMIN', FALSE)
            ON CONFLICT (email, tenant_id)
            DO UPDATE SET password_hash = EXCLUDED.password_hash,
                          must_change_password = FALSE,
                          atualizado_em = NOW()
        """), {"hash": hash_ti})
        
        # Remove o usuario de teste se existir
        await conn.execute(text("""
            DELETE FROM users WHERE email = 'joao.consulta@luminaai.demo'
        """))
        
        # Remove a view de teste de integracao se existir
        await conn.execute(text("""
            DELETE FROM view_catalog WHERE nome_view_oracle = 'VW_TESTE_INTEGRACAO'
        """))
        
        # Reset tenant para estado inicial
        await conn.execute(text("""
            UPDATE tenants 
            SET nome = 'LuminaAI Demo Corp',
                logo_url = 'https://cdn.luminaai.com/logos/demo-corp.png',
                atualizado_em = NOW()
            WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
        """))
        
        # Confirma o estado
        result = await conn.execute(text("""
            SELECT email, must_change_password FROM users WHERE email = 'admin@luminaai.demo'
        """))
        row = result.fetchone()
        print(f"Admin: email={row[0]}, must_change_password={row[1]}")
        print("Estado de teste restaurado com sucesso!")

if __name__ == '__main__':
    asyncio.run(reset_test_state())
