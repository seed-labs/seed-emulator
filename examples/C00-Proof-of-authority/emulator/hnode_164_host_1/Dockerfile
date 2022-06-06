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
COPY 634b5208db5d7f4f91eed8257564f8cd /tmp/keystore/UTC--2022-06-01T23-16-02.272707000Z--b726b6a63fd5fd27a4deee9b8edf02e13b1f7add
COPY fdcac5620aa2316a4ec1b0501cd32361 /tmp/keystore/UTC--2022-06-01T23-16-03.071590000Z--a3ee1fe7e006a213a47846775d9eed29cfa705d8
COPY f4d556a844298d3911e6d250e4a2d93b /tmp/eth-genesis.json
COPY 0bf749f51915d190035e14f6afa9a371 /tmp/eth-nodes
COPY 427fecb1e0b6c8dc8f669b5b71b8db71 /tmp/eth-bootstrapper
COPY d2cdff8371aa6af79bb63954a87ac69f /tmp/eth-password
CMD ["/start.sh"]

