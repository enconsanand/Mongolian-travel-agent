FROM ghcr.io/pnpm/pnpm:12 AS base
RUN pnpm runtime set node 24 -g

ENV TZ=Asia/Tokyo
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=${FRONT_PORT:-3000}

RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./front/package.json ./front/pnpm-lock.yaml ./front/pnpm-workspace.yaml ./

FROM base AS deps
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

FROM base AS builder
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile
COPY ./front/ ./
RUN pnpm run build

FROM base AS dev
COPY --from=deps /app/node_modules /app/node_modules

ARG FRONT_PORT
ENV FRONT_PORT=${FRONT_PORT}

EXPOSE ${FRONT_PORT}

FROM base AS prod

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.output ./.output

CMD ["pnpm start"]
