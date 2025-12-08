FROM node:22 AS node-image
COPY start.sh /
WORKDIR /usr/src/app
COPY . .
WORKDIR /usr/src/app/frontend
RUN npm install -g pnpm
RUN pnpm i
RUN pnpm run build-test
WORKDIR /usr/src/app/backend
RUN npm install
RUN npm install -D typescript @types/tar-fs
RUN ./node_modules/.bin/tsc
ENTRYPOINT ["sh", "/start.sh"]
