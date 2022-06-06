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
COPY f0a340dd70bff86b472d6f0d0d1b41d2 /tmp/keystore/UTC--2022-06-01T23-16-06.305523000Z--0404758da6ca2dc5a3c2b3b6279653056f8706d4
COPY e161d84351ba5aa5d07cf34fbcedad64 /tmp/keystore/UTC--2022-06-01T23-16-07.118000000Z--916921cd9ff491a63d26d4cacbbda5e49ab423c9
COPY f4d556a844298d3911e6d250e4a2d93b /tmp/eth-genesis.json
COPY 0bf749f51915d190035e14f6afa9a371 /tmp/eth-nodes
COPY 427fecb1e0b6c8dc8f669b5b71b8db71 /tmp/eth-bootstrapper
COPY d2cdff8371aa6af79bb63954a87ac69f /tmp/eth-password
CMD ["/start.sh"]

