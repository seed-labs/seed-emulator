FROM node:22-slim AS builder

RUN npm install -g pnpm
WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm i
COPY frontend/ .
RUN pnpm run build-test

FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends iproute2
COPY start.sh /
RUN chmod +x /start.sh
WORKDIR /usr/src/app
COPY . .
WORKDIR /usr/src/app/backend
RUN npm install
COPY --from=builder /build/frontend/dist ../frontend/dist
RUN ./node_modules/.bin/tsc
ENTRYPOINT ["sh", "/start.sh"]