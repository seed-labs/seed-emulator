FROM ubuntu:20.04 AS builder1

ENV DEBIAN_FRONTEND=noninteractive
ENV GOLANG_VERSION=1.24.0
ENV PATH="/usr/local/go/bin:$PATH"

WORKDIR /

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget git build-essential curl make python3 python3-pip ca-certificates \
    && apt-get clean

# Install Go manually
RUN curl -OL https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz && \
    rm go${GOLANG_VERSION}.linux-amd64.tar.gz

RUN go version  # Just to confirm installation

# Build devp2p from go-ethereum source
RUN go install github.com/ethereum/go-ethereum/cmd/devp2p@latest

# Intalling eth-beacon-genesis and eth2-val-tools
RUN git clone https://github.com/ethpandaops/eth-beacon-genesis.git  \
    && cd eth-beacon-genesis && make \
    && go install github.com/protolambda/eth2-val-tools@latest

# Downloading geth 
RUN wget https://gethstore.blob.core.windows.net/builds/geth-linux-amd64-1.15.11-36b2371c.tar.gz \
    && tar -xzf geth-linux-amd64-1.15.11-36b2371c.tar.gz 

# Downloading lighthouse
RUN wget https://github.com/sigp/lighthouse/releases/download/v7.0.1/lighthouse-v7.0.1-x86_64-unknown-linux-gnu.tar.gz \
    && tar -xzf lighthouse-v7.0.1-x86_64-unknown-linux-gnu.tar.gz



# Final image    

FROM handsonsecurity/seedemu-base

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common python3 python3-pip
RUN pip install web3

COPY --from=builder1 /eth-beacon-genesis/bin/eth-beacon-genesis /usr/local/bin/eth-beacon-genesis
COPY --from=builder1 /root/go/bin/eth2-val-tools /usr/local/bin/eth2-val-tools
COPY --from=builder1 /root/go/bin/devp2p /usr/local/bin/devp2p
COPY --from=builder1 /geth-linux-amd64-1.15.11-36b2371c/geth /usr/local/bin/geth
COPY --from=builder1 /lighthouse /usr/local/bin/lighthouse