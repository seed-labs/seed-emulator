FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get install -y --no-install-recommends nginx-light python3 git cmake python3-dev gcc g++ make python3-pip
RUN git clone https://github.com/malwaredllc/byob.git /tmp/byob/
RUN pip3 install -r /tmp/byob/byob/requirements.txt
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
RUN chmod +x /start.sh
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY b2b2108b9cb798f4d00a3d186c1dad5d /var/www/html/index.html
COPY b4496baf4c2b06bbf99c556ef50347df /etc/nginx/sites-available/default
COPY 20e4ef7d7678461ec042443ffc0d08d8 /tmp/BotClient.py
CMD ["/start.sh"]

