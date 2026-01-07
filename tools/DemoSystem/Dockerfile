FROM node:22

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG http_proxy
ARG https_proxy

# 设置环境变量
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}

# 设置 APT 代理（重要！）
RUN if [ -n "$HTTP_PROXY" ]; then \
    echo "Acquire::http::Proxy \"$HTTP_PROXY\";" > /etc/apt/apt.conf.d/proxy.conf && \
    echo "Acquire::https::Proxy \"$HTTPS_PROXY\";" >> /etc/apt/apt.conf.d/proxy.conf; \
    fi

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y \
    docker-ce-cli \
    docker-compose-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 999 docker && usermod -aG docker node

COPY start.sh /
RUN chmod +x /start.sh
WORKDIR /usr/src/app
COPY . .
WORKDIR /usr/src/app/frontend
RUN npm install -g pnpm
RUN pnpm i
RUN pnpm run build-dev
WORKDIR /usr/src/app/backend
RUN npm install
RUN npm install -D typescript @types/tar-fs
RUN ./node_modules/.bin/tsc
ENTRYPOINT ["sh", "/start.sh"]
