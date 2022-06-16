FROM cfee3a34e9c68ac1d16035a81a926786
ARG DEBIAN_FRONTEND=noninteractive
RUN echo 'exec zsh' > /root/.bashrc
RUN apt-get update && apt-get install -y --no-install-recommends curl dnsutils ipcalc iproute2 iputils-ping jq mtr-tiny nano netcat tcpdump termshark vim-nox zsh
RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN add-apt-repository ppa:ethereum/ethereum
RUN apt-get update && apt-get install --yes geth bootnode
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
COPY d18858afc6bb66ec3a19d872077acfd2 /seedemu_sniffer
COPY 17ac2d812a99a91e7f747e1defb72a29 /seedemu_worker
RUN chmod +x /start.sh
RUN chmod +x /seedemu_sniffer
RUN chmod +x /seedemu_worker
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY f4d556a844298d3911e6d250e4a2d93b /tmp/eth-genesis.json
COPY 0bf749f51915d190035e14f6afa9a371 /tmp/eth-nodes
COPY 427fecb1e0b6c8dc8f669b5b71b8db71 /tmp/eth-bootstrapper
COPY 7ceba19a156a4786ab0dcabf6c1d215e /tmp/keystore/UTC--2022-06-16T05-44-18.755502000Z--fa9a6efe9c6b694565c41ab59f3fb248222ad564
COPY 19b2a648ad0a7e229411a6cc8fcf1001 /tmp/keystore/UTC--2022-06-16T05-44-20.188086000Z--7d9a717fd368a0ea4d194a9bc0b0cda553ab0994
COPY d2cdff8371aa6af79bb63954a87ac69f /tmp/eth-password
CMD ["/start.sh"]

