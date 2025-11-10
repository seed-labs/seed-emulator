FROM node:22 AS node-image
COPY . .
WORKDIR /frontend
RUN npm install -g pnpm
RUN pnpm i
RUN pnpm run build-test

FROM handsonsecurity/seedemu-multiarch-base:buildx-latest
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /
RUN apt-get update && apt-get install -y python3 python3-pip mysql-server
RUN python3 -m pip install --upgrade pip
RUN pip3 install flask web3==5.31.1 docker Flask-Cors flask-apscheduler Flask-SQLAlchemy pymysql "Flask[async]" aiohttp
COPY start.sh /start.sh
RUN chmod +x /start.sh
COPY --from=node-image /server/static/frontend /server/static/frontend
COPY . .
EXPOSE 3306
ENTRYPOINT ["sh", "/start.sh"]
