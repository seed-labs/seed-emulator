FROM node:22-slim AS builder

WORKDIR /build
COPY . .
WORKDIR /build/frontend
RUN npm install -g pnpm
RUN pnpm i
RUN pnpm run build-dev

FROM node:22-slim
WORKDIR /usr/src/app
COPY . .
COPY --from=builder /build/frontend/dist ./frontend/dist
WORKDIR /usr/src/app/backend
RUN npm install
RUN npm install -D typescript @types/tar-fs js-yaml @types/js-yaml
RUN ./node_modules/.bin/tsc
COPY start.sh /
RUN chmod +x /start.sh
ENTRYPOINT ["sh", "/start.sh"]