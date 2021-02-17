FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get install -y --no-install-recommends curl dnsutils ipcalc iproute2 iputils-ping jq mtr-tiny nano tcpdump termshark vim-nox
RUN apt-get install -y --no-install-recommends bind9
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
RUN chmod +x /start.sh
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY 9fa3998da182b9c5f98cb4ba6ea96a2e /etc/bind/named.conf.options
COPY 0fa0266c76e2bc23a785c50d623d4fc2 /etc/bind/zones/as152.net.
COPY 10012e957e1896df5bbcc7fc8f43d0cb /etc/bind/named.conf.zones
COPY c70b265e18f104c9c410ba4b2979ce35 /dnssec_zones.txt
COPY e464e553725cafe22842348a2e0f3ed0 /enable_dnssec
CMD ["/start.sh"]

