FROM node:20-alpine AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY components ./components
COPY context ./context
COPY engines ./engines
COPY hooks ./hooks
COPY lib ./lib
COPY public ./public
COPY styles ./styles
COPY types ./types
COPY next.config.ts postcss.config.mjs proxy.ts tailwind.config.ts tsconfig.json ./
RUN npm run build

FROM node:20-alpine AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup -S -g "$APP_GID" lumina \
    && adduser -S -D -H -u "$APP_UID" -G lumina lumina

COPY --from=builder --chown=10001:10001 /app/package.json /app/package-lock.json ./
COPY --from=builder --chown=10001:10001 /app/node_modules ./node_modules
COPY --from=builder --chown=10001:10001 /app/.next ./.next
COPY --from=builder --chown=10001:10001 /app/public ./public

RUN npm prune --omit=dev \
    && mkdir -p /app/.next/cache \
    && chown -R "$APP_UID:$APP_GID" /app/.next/cache

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:3000/healthz"]

CMD ["node", "node_modules/next/dist/bin/next", "start"]
