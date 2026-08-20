ARG NODE_BASE_IMAGE=node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293

FROM ${NODE_BASE_IMAGE} AS patched-base

ARG ALPINE_OPENSSL_VERSION=3.5.7-r0
RUN apk add --no-cache \
    "libcrypto3=${ALPINE_OPENSSL_VERSION}" \
    "libssl3=${ALPINE_OPENSSL_VERSION}" \
    && rm -f /var/log/apk.log

FROM patched-base AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG LUMINA_BUILD_ID

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
RUN SOURCE_BUILD_ID="$( (find app components context engines hooks lib public styles types -type f -exec sha256sum {} +; sha256sum package.json package-lock.json next.config.ts postcss.config.mjs proxy.ts tailwind.config.ts tsconfig.json) | sort | sha256sum | cut -d ' ' -f 1 )" \
    && EFFECTIVE_BUILD_ID="${LUMINA_BUILD_ID:-$SOURCE_BUILD_ID}" \
    && SERVER_ACTIONS_KEY="$(node -e "process.stdout.write(require('crypto').createHash('sha256').update(process.argv[1] + ':server-actions').digest('base64'))" "$EFFECTIVE_BUILD_ID")" \
    && PREVIEW_ID="$(printf '%s' "$EFFECTIVE_BUILD_ID:preview-id" | sha256sum | cut -c1-32)" \
    && PREVIEW_SIGNING_KEY="$(printf '%s' "$EFFECTIVE_BUILD_ID:preview-signing" | sha256sum | cut -c1-64)" \
    && PREVIEW_ENCRYPTION_KEY="$(printf '%s' "$EFFECTIVE_BUILD_ID:preview-encryption" | sha256sum | cut -c1-64)" \
    && rm -f /.dockerenv \
    && mkdir -p .next/cache \
    && node -e "require('fs').writeFileSync('.next/cache/.previewinfo', JSON.stringify({previewModeId:process.argv[1],previewModeSigningKey:process.argv[2],previewModeEncryptionKey:process.argv[3],expireAt:4102444800000}))" "$PREVIEW_ID" "$PREVIEW_SIGNING_KEY" "$PREVIEW_ENCRYPTION_KEY" \
    && LUMINA_BUILD_ID="$EFFECTIVE_BUILD_ID" NEXT_SERVER_ACTIONS_ENCRYPTION_KEY="$SERVER_ACTIONS_KEY" npm run build

FROM patched-base AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN addgroup -S -g "$APP_GID" lumina \
    && adduser -S -D -H -u "$APP_UID" -G lumina lumina

COPY --from=builder --chown=10001:10001 /app/.next/standalone ./
COPY --from=builder --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=builder --chown=10001:10001 /app/public ./public

RUN mkdir -p /app/.next/cache \
    && chown -R "$APP_UID:$APP_GID" /app/.next/cache

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:3000/healthz"]

CMD ["node", "server.js"]
