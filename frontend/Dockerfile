# syntax=docker/dockerfile:1


# Use Bun's official image
FROM oven/bun:1 AS base

WORKDIR /app


# Install dependencies with bun (dev)
FROM base AS devdeps

COPY package.json bun.lock* ./

RUN bun install --no-save --frozen-lockfile


# Install dependencies with bun (prod)
FROM base AS proddeps

COPY package.json bun.lock* ./

RUN bun install --no-save --frozen-lockfile --production


# Rebuild the source code only when needed (only for production)
FROM base AS prodbuilder

WORKDIR /app

COPY --from=proddeps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

RUN bun run build


# Development image
FROM base AS dev

WORKDIR /app

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

RUN groupadd --system --gid 10001 nodejs && \
    useradd --system --uid 10001 --no-log-init -g nodejs nextjs && \
    chown nextjs:nodejs /app

COPY --from=devdeps /app/node_modules ./node_modules
COPY --chown=nextjs:nodejs . .

USER nextjs

EXPOSE 3000

ENV PORT=3000

CMD [ "bun", "run", "dev" ]


# Production image, copy all the files and run next
FROM base AS prod

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

RUN groupadd --system --gid 10001 nodejs && \
    useradd --system --uid 10001 --no-log-init -g nodejs nextjs

COPY --from=prodbuilder /app/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=prodbuilder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=prodbuilder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["bun", "./server.js"]