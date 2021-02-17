FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
RUN mkdir -p /usr/share/doc/bird2/examples/
RUN touch /usr/share/doc/bird2/examples/bird.conf
RUN apt-get install -y --no-install-recommends bird2
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
RUN chmod +x /start.sh
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY 2b0ae038330eccd43095538618caee7d /etc/bird/bird.conf
CMD ["/start.sh"]

