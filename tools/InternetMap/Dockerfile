FROM node:14
RUN npm config set registry https://registry.npmmirror.com
COPY start.sh /
WORKDIR /usr/src/app
COPY . .
WORKDIR /usr/src/app/frontend
RUN npm install
RUN npm install -D webpack-cli
RUN ./node_modules/.bin/webpack --mode production
WORKDIR /usr/src/app/backend
RUN npm install
RUN npm install -D typescript @types/tar-fs
RUN ./node_modules/.bin/tsc
ENTRYPOINT ["sh", "/start.sh"]
