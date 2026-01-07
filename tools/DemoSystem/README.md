### Demo System Manual

1. 切换到 Demo System 项目根目录下
2. 修改配置文件 `docker-compose.yml`，请根据实际情况配置
    - http_proxy/https_proxy/HTTP_PROXY/HTTPS_PROXY，clash代理地址
    - HOST，主机IP地址（即 `Demo System` 容器所在主机），目的是访问同主机的 `Internet Map`
3. build 构建镜像。(e.g., `docker compose build`)
4. 启动容器。(e.g., `docker compose up`)


注：
   `Demo System` 会使用到 `handsonsecurity/seedemu-internetmap:2.0` 镜像，请提前到 tools/InternetMap2 路径下构建