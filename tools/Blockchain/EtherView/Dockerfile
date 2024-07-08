FROM handsonsecurity/seedemu-multiarch-base:buildx-latest 

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install flask web3==5.31.1 docker
COPY start.sh /start.sh
RUN chmod +x /start.sh
COPY . .
ENTRYPOINT ["sh", "/start.sh"]
