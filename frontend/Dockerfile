# Frontend Next.js de Label Collectes : image de production (sortie « standalone »).
#
#   docker build -t label-frontend --build-arg API_URL=http://157.173.103.147:8001 .
#   docker run -p 3000:3000 -e API_URL=http://web:8001 label-frontend
#
# API_URL sert deux fois : au build, pour precalculer les pages publiques (si l'API ne
# repond pas, elles se remplissent a la premiere visite) ; a l'execution, pour tous les
# appels. Dans docker-compose, l'execution passe par le reseau interne (http://web:8001).

FROM node:24-alpine AS base
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

FROM base AS dependances
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# La version de pnpm est celle de package.json (packageManager).
RUN npm install -g --no-audit --no-fund "$(node -p 'require("./package.json").packageManager')"
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile

FROM dependances AS construction
COPY . .
ARG API_URL=http://web:8001
ARG SITE_URL=http://localhost:3000
ENV API_URL=$API_URL SITE_URL=$SITE_URL
RUN pnpm build

FROM base AS production
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S app && adduser -S app -G app
COPY --from=construction --chown=app:app /app/.next/standalone ./
COPY --from=construction --chown=app:app /app/.next/static ./.next/static
COPY --from=construction --chown=app:app /app/public ./public
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD wget -qO /dev/null http://127.0.0.1:3000/connexion || exit 1
CMD ["node", "server.js"]
