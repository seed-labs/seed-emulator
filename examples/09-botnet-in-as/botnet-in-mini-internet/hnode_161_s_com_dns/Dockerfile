FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get install -y --no-install-recommends bind9 nginx-light php7.4-fpm
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
RUN chmod +x /start.sh
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY 9fa3998da182b9c5f98cb4ba6ea96a2e /etc/bind/named.conf.options
COPY d1d6e45586ee6eb2c0c2925330f556bb /etc/bind/zones/com.
COPY 10012e957e1896df5bbcc7fc8f43d0cb /etc/bind/named.conf.zones
COPY 7466e88d4595f86b0d5454f3d91d5769 /var/www/html/index.php
COPY 0f61fed50491bac578e1a047ff3bcaab /var/www/html/domain.php
COPY b4496baf4c2b06bbf99c556ef50347df /etc/nginx/sites-available/default
CMD ["/start.sh"]

