FROM node:22 AS node-image
WORKDIR /frontend
RUN npm install -g pnpm
RUN pnpm i
RUN pnpm run build-test

FROM handsonsecurity/seedemu-multiarch-base:buildx-latest
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install flask web3==5.31.1 docker Flask-Cors flask-apscheduler Flask-SQLAlchemy pymysql
COPY start.sh /start.sh
RUN chmod +x /start.sh
COPY . .
ENTRYPOINT ["sh", "/start.sh"]
