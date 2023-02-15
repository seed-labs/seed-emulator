FROM handsonsecurity/seed-ubuntu:large

RUN apt-get update && apt-get install -y python3 pip
RUN pip3 install flask web3 docker
COPY start.sh /start.sh
RUN chmod +x /start.sh
COPY . .
ENTRYPOINT ["sh", "/start.sh"]
