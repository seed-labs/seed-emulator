FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get install -y --no-install-recommends bridge-utils openvpn
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
RUN chmod +x /start.sh
COPY 8f49340551a793900659860539f591e9 /ovpn-server.conf
COPY b69be66a4c20bed77569a2c06cd589bb /ovpn_startup
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
CMD ["/start.sh"]

