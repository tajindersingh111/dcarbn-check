FROM node:22-alpine3.23 AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine3.23 AS builder

WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build && \
    npm prune --omit=dev --no-audit --no-fund

FROM node:22-alpine3.23 AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

RUN apk upgrade --no-cache && \
    addgroup -g 10001 appuser && \
    adduser -D -u 10001 -G appuser appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/package.json ./package.json
COPY --from=builder --chown=appuser:appuser /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appuser /app/.next ./.next

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:3000/ >/dev/null 2>&1 || exit 1

CMD ["npm", "run", "start"]
