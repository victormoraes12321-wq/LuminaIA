# ── Stage 1: Build ──────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copia arquivos de configuração e instala dependências
COPY package*.json ./
RUN npm ci

# Copia o código-fonte e compila em modo produção
COPY . .
RUN npm run build

# ── Stage 2: Runner ─────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

# Copia artefatos compilados e dependências do estágio anterior
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Pruna dependências de desenvolvimento para otimizar espaço em disco
RUN npm prune --omit=dev

EXPOSE 3000

# Health Check do Next.js utilizando wget
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/login || exit 1

# Comando padrão para rodar a aplicação em produção
CMD ["npm", "run", "start"]
