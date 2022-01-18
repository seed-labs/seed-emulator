FROM node:14
COPY start.sh /
WORKDIR /usr/src/app/blockchain-client/src
COPY . .
RUN npm i
ENTRYPOINT ["sh", "/start.sh"]
