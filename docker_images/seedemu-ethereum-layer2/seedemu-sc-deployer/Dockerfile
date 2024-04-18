FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:v1.4.3 as node

FROM ghcr.io/foundry-rs/foundry:latest

ARG SOLC_VERSIONS="0.5.17 0.8.15 0.8.19"

RUN apk --no-cache add bash jq iproute2 curl openssl python3

COPY --from=node /usr/local/bin/op-node /usr/local/bin/op-node

COPY l2.tar.gz /l2.tar.gz
RUN tar -xzf /l2.tar.gz && rm /l2.tar.gz

# Compile the smart contracts
RUN cd /l2 && forge build
