# LuminaAI V2 RC4 — Guia de Instalação e Primeiro Boot Nativo (Windows Server 2025)

Este manual descreve o passo a passo para implantar o **LuminaAI V2 RC4** nativamente no **Windows Server 2025 Standard** (`CASADOCAMPO` / `192.168.0.35`), utilizando PostgreSQL local, Python 3.12 e Node.js 24 sem Hyper-V ou Docker.

---

## 1. Pré-Requisitos no Servidor

Certifique-se de que os runtimes já estão instalados no Windows Server:
- **Python 3.12.10** (64-bit) com `pip`
- **Node.js 24.18.0** e **npm 11.16.0**
- **PostgreSQL 18.4** ativo em `localhost:5432` com banco `lumina_preprod` e usuário `lumina_preprod_user`

> [!IMPORTANT]
> **Portas Utilizadas:**
> - **Frontend Web:** `3002` (A porta `3000` é utilizada por outro sistema existente e não é alterada).
> - **Backend API:** `8000`
> - **PostgreSQL:** `5432` (apenas conexão local).

---

## 2. Procedimento de Instalação Rápida (9 Passos)

### Passo 1: Extrair o Pacote
Extraia o arquivo `lumina-v2-rc4-windows-server-deploy.zip` em uma pasta de sua escolha (ex: `C:\LuminaAI`).

```powershell
Expand-Archive -Path "lumina-v2-rc4-windows-server-deploy.zip" -DestinationPath "C:\LuminaAI"
cd C:\LuminaAI
```

---

### Passo 2: Configurar o Virtualenv Python (Backend)
No PowerShell:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
cd ..
```

---

### Passo 3: Gerar Chaves Criptográficas Seguras
Execute o gerador automático:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_keys_windows.ps1
```

---

### Passo 4: Criar e Preencher o Arquivo `backend/.env`
Copie o template de pré-produção:
```powershell
Copy-Item backend\.env.windows-preprod.example backend\.env
```
Abra o `backend\.env` no Bloco de Notas ou editor e preencha:
1. `DATABASE_URL`: Insira a senha real do usuário `lumina_preprod_user`.
2. `SECRET_KEY`: Cole a chave gerada no Passo 3.
3. `ENCRYPTION_KEY`: Cole a chave Fernet gerada no Passo 3.
4. `OPENAI_API_KEY`: Insira sua chave `sk-...` da OpenAI.
5. `INITIAL_ADMIN_PASSWORD`: Defina a senha para o usuário inicial `admin@luminaai.local`.

---

### Passo 5: Executar o Bootstrap do Banco de Dados
O script executa o schema base, a cadeia canônica de migrações (v4.1 até v26.0) e cria o tenant/admin inicial de forma segura:
```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\bootstrap_windows_preprod.py
```

---

### Passo 6: Instalar Dependências e Compilar o Frontend
No diretório raiz:
```powershell
cd frontend
npm ci
npm run build
cd ..
```

---

### Passo 7: Configurar o Windows Firewall (Opcional / Recomendado)
Abra o PowerShell como Administrador e libere o acesso LAN às portas 3002 e 8000:
```powershell
powershell -ExecutionPolicy Bypass -File configure-luminaai-firewall.ps1
```

---

### Passo 8: Iniciar o Sistema LuminaAI
Execute o script de inicialização segura:
```powershell
powershell -ExecutionPolicy Bypass -File start-luminaai-windows.ps1
```

O script inicializa o Backend e o Frontend em modo produção, salva os PIDs e valida as sondas `/health`, `/health/deep` e `/healthz`.

---

### Passo 9: Acessar a Aplicação
Abra no navegador de qualquer estação de trabalho na rede local:
👉 **`http://192.168.0.35:3002`** (ou `http://localhost:3002` no próprio servidor).

Login inicial:
- **Email:** `admin@luminaai.local`
- **Senha:** (a senha configurada em `INITIAL_ADMIN_PASSWORD` no `.env`)

---

## 3. Comandos Úteis de Operação

- **Verificar Status e Saúde:**
  ```powershell
  powershell -File status-luminaai-windows.ps1
  ```
- **Parar o LuminaAI com Segurança:**
  ```powershell
  powershell -File stop-luminaai-windows.ps1
  ```
- **Visualizar Logs de Runtime:**
  - Backend: `runtime-logs\backend.out.log` e `runtime-logs\backend.err.log`
  - Frontend: `runtime-logs\frontend.out.log` e `runtime-logs\frontend.err.log`
