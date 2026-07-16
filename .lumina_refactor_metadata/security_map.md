# Security Map — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## 1. Isolamento Multi-Tenant (Multi-Tenancy Isolation)

O LuminaAI adota uma arquitetura de banco de dados híbrida para isolamento de dados:
1. **Dados Operacionais e Configuração (`luminaai_db`)**: Armazenados em tabelas compartilhadas no PostgreSQL principal. O isolamento é lógico (todas as queries SQL do SQLAlchemy contêm a cláusula `where(Model.tenant_id == current_user.tenant_id)`).
2. **Dados Analíticos (`luminaai_analytics_db`)**: Cada tenant possui seu próprio banco de dados PostgreSQL clonado fisicamente (`clone_db_name`). O isolamento é físico.

### Fluxo de Isolamento Analítico no Compilador SQL
- O `SecurityValidator` (em `security_and_normalization_engine.py`) inspeciona o SQL final gerado.
- Se a view física acessada possuir a coluna `tenant_id` no CKG, o validador exige a presença literal de `tenant_id = '{tenant_id}'` ou um parâmetro posicional `tenant_id = :tenant_id`. Caso contrário, a query é abortada lançando `SecurityValidationError` com a mensagem: `"Violacao de isolamento Multi-Tenant: tenant_id nao identificado na query física!"`.

---

## 2. Validação de Escopo e Proteção de Entrada (Context Guard)

O módulo `context_guard.py` realiza sanitização e validação de escopo em duas camadas lexicais:

### Camada 1: Parâmetros Extraídos pela IA (`validate_params`)
- **Regra**: Limita o comprimento das strings de parâmetros a 200 caracteres para evitar ataques de estouro/exfiltração.
- **Bloqueios**: Chaves e valores de parâmetros são escaneados contra expressões regulares proibidas:
  - *Dados médicos/pessoais*: `salario`, `folha`, `payroll`, `medic`, `saude`, `health`, `secret`, `senha`, `password`.
  - *Comandos DML/DDL*: `drop`, `delete`, `truncate`, `insert`, `update`, `alter`, `create`.
  - *SQL Injection básico*: `union`, `--`, `;`, `or 1=1`.

### Camada 2: Pergunta Bruta do Usuário (`validate_user_query`)
- **Regra**: Trunca a pergunta original do usuário para no máximo 1000 caracteres.
- **Bloqueios**: Escaneamento de prompt injection, data exfiltration, scripts XSS (`<script>`), cookies e comandos SQL arbitrários.

---

## 3. Segurança de Banco de Dados Físico (Security Validator)

O compilador e executor de SQL realizam as seguintes verificações de segurança:
- **Prevenção de Escrita**: Bloqueio total de qualquer instrução de escrita no banco de dados analítico através do scan de palavras-chaves: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`.
- **Parametrização Restrita**: O gerador de SQL utiliza parâmetros nomeados/posicionais (`:param_0`, `:tenant_id`) gerenciados pelo driver do banco de dados, neutralizando qualquer tentativa de injeção SQL clássica via concatenação de strings.

---

## 4. Criptografia de Credenciais de Integração

Todas as credenciais de acesso ao banco de dados Oracle de produção (`tenant.oracle_conn`) e ao banco clone PostgreSQL (`tenant.clone_db_conn`) são criptografadas em repouso.
- **Algoritmo**: Fernet (AES-128 sob modo CBC com HMAC SHA-256).
- **Chave**: Definida pela variável de ambiente `settings.ENCRYPTION_KEY` (chave base64).
- **Tratamento em Transmissão**: Os endpoints de retorno de configurações do tenant ocultam os dados sensíveis de credenciais substituindo os valores reais por máscaras (`••••••••`).

---

## ⚠️ ACHADOS & RISCOS DE SEGURANÇA DETECTADOS

1. **Vulnerabilidade de Bypass Lexical**:
   > [!WARNING]
   > O `ContextGuard` e o `SecurityValidator` baseiam-se em **listas de termos proibidos (blacklist)** usando expressões regulares.
   > Ataques de ofuscação de SQL (ex: usar concatenação de strings `DE` + `LETE`, ou codificação em hexadecimal / Unicode no prompt da IA) ou queries escritas em inglês/outros idiomas (como `remov` em vez de `delete`) podem contornar a detecção léxica, embora a ausência de permissões de escrita no usuário do banco de dados clone mitigue o risco de destruição física.

2. **Falta de RBAC / RLS na Camada Semântica**:
   - Não há controle de permissões por perfil (Administrador, Gestor, Vendedor) para acesso a campos específicos. Se um usuário do tipo Vendedor conseguir enganar a IA para gerar um plano que consulte o faturamento de outros vendedores, a query será executada, pois o isolamento de segurança é feito exclusivamente no nível do `tenant_id`, e não no nível de linha (RLS) por perfil de usuário.

---

*Auditoria estática — nenhum arquivo modificado.*
