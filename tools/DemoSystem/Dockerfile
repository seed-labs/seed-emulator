FROM node:22-slim AS builder

RUN npm install -g pnpm
WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm i
COPY frontend/ .
RUN pnpm run build-dev

FROM node:22-slim
COPY start.sh /
RUN chmod +x /start.sh
WORKDIR /usr/src/app/backend
COPY backend/package.json backend/pnpm-lock.yaml* ./
RUN npm install
COPY backend/ .
COPY --from=builder /build/frontend/dist ../frontend/dist
RUN ./node_modules/.bin/tsc
ENTRYPOINT ["sh", "/start.sh"]