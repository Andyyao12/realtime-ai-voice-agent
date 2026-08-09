FROM node:22.18.0-alpine AS base
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

FROM base AS dependencies
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:22.18.0-alpine AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup --system --gid 10001 showcase \
    && adduser --system --uid 10001 --ingroup showcase showcase
WORKDIR /app
COPY --from=builder --chown=showcase:showcase /app/public ./public
COPY --from=builder --chown=showcase:showcase /app/.next/standalone ./
COPY --from=builder --chown=showcase:showcase /app/.next/static ./.next/static
USER showcase
EXPOSE 3000
CMD ["node", "server.js"]
