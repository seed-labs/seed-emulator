FROM handsonsecurity/seedemu-multiarch-base:buildx-latest
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip
RUN curl -fsSL https://deb.nodesource.com/setup_21.x | bash - && apt update -y && apt install -y nodejs
RUN npm install -g serve
RUN pip install web3
# RUN python3 -c 'from solcx import install_solc;install_solc(version="0.8.15")'
RUN mkdir -p /volumes
ADD ./volumes /volumes
WORKDIR /volumes/kubo-dapp
RUN npm install
WORKDIR /

