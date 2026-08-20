# Modelo de Segurança e Hardening — LuminaAI V2 RC4

Este documento estabelece o modelo de segurança, isolamento, controle de acesso e hardening de infraestrutura do **LuminaAI V2 RC4**.

---

## 1. Princípios Fundamentais de Segurança

1. **Fail-Closed por Padrão:** Qualquer falha de autenticação, violação de tenant, incompatibilidade de schema ou inconsistência contratual resulta em bloqueio imediato da requisição (`HTTP 401`, `HTTP 403` ou `HTTP 422`).
2. **Autoridade Server-Side:** Nenhuma decisão de privilégio, filtro de tenant, papel de usuário (RBAC) ou ativação de feature flag é aceita a partir de headers de cliente, parâmetros de URL ou corpo de requisição não assinado.
3. **Isolamento Estrito Multi-Tenant:** Toda operação é escopada pelo `tenant_id` derivado exclusivamente do token JWT do usuário autenticado.
4. **Proteção Contra Injeção e SQL Seguro:** Consultas ao PostgreSQL analítico são construídas via catálogo governado e parâmetros tipados (*bind variables*). A IA nunca gera SQL livre diretamente para execução em banco de dados.

---

## 2. Hardening de Contêineres e Runtime

| Camada | Configuração | Objetivo |
| :--- | :--- | :--- |
| **Identidade de Execução** | UID `10001` / GID `10001` (`lumina:lumina`) | Execução estritamente não-root no backend e frontend. |
| **Sistema de Arquivos** | `read_only: true` | Impede escrita não autorizada no filesystem do contêiner. |
| **Descarte de Capacidades** | `cap_drop: ALL` | Remove todas as capacidades Linux desnecessárias do kernel. |
| **Privilégios de Processo** | `no-new-privileges: true` | Impede elevação de privilégios via binários SUID/SGID. |
| **Armazenamento Efêmero** | `tmpfs` montado em `/tmp`, logs e cache | Garante diretórios temporários em memória volátil e limpa. |
| **Isolamento de Rede** | Bridge network interna sem exposição de portas do DB | Apenas o Nginx expõe portas 80/443 externamente. |

---

## 3. Controle de Acesso Baseado em Papéis (RBAC)

O LuminaAI implementa três níveis hierárquicos de acesso:

- **`ADMIN` (Administrador do Sistema):**
  - Gerenciamento de tenants, usuários, configurações globais e políticas de segurança.
  - Acesso completo ao Inspector, centro de diagnósticos técnicos, telemetria e gerenciamento de SVR.
  - Aprovação e publicação de artefatos da Base de Conhecimento e Dashboards V2.
- **`GESTOR` (Gestor de Negócios / Analista BI):**
  - Gestão e edição de catálogos semânticos, dicionário empresarial e Dashboard Studio.
  - Criação e autoria de propostas de dashboards e visualizações analíticas.
- **`CONSULTA` (Usuário Final / Consumidor de BI):**
  - Consulta analítica via chat em linguagem natural e visualização de dashboards publicados.
  - Acesso ao histórico pessoal de conversas, favoritos e preferências individuais.
  - **Restrições:** Sem acesso a traces, diagnósticos de backend, SQL, configurações SaaS ou administração.

---

## 4. Gestão de Segredos e Chaves Criptográficas

- **`SECRET_KEY`:** Chave criptográfica forte (mínimo 64 caracteres hexadecimais) usada exclusivamente para assinatura e validação de tokens JWT (HS256).
- **`ENCRYPTION_KEY`:** Chave simétrica Fernet (32 bytes url-safe base64) para cifragem de credenciais sensíveis em repouso.
- **`OPENAI_API_KEY`:** Credencial de API segregada por ambiente (nunca usar credenciais de produção em pré-produção ou desenvolvimento).
- **Isolamento:** Segredos são injetados exclusivamente via variáveis de ambiente ou Secret Manager, nunca versionados em repositório ou expostos em logs/respostas HTTP.

---

## 5. Kill Switches e Mecanismos de Emergência

O LuminaAI V2 possui um sistema de contenção de incidentes com desativação instantânea de subsistemas:

- `V2_GLOBAL_EMERGENCY_DISABLE=true`: Desativa globalmente todas as rotas e execuções V2, retornando ao pipeline clássico seguro.
- `KILL_SWITCH_DASHBOARD_V2_READ`: Bloqueia acesso a dashboards V2 em caso de inconsistência de exibição.
- `KILL_SWITCH_DASHBOARD_V2_AUTHORING`: Bloqueia criação/edição de novos dashboards.
- `KILL_SWITCH_DASHBOARD_AI`: Interrompe a assistência e geração de propostas de dashboards por IA.
- `KILL_SWITCH_POST_SYNC_INSIGHTS`: Desativa o motor de geração de insights pós-sincronização.
- `KILL_SWITCH_WORK_QUEUE_V2`: Interrompe o processamento de novos jobs assíncronos da fila.
