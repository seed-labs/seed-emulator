FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:v1.4.3 as node

FROM ghcr.io/foundry-rs/foundry:latest as foundry

ARG SOLC_VERSIONS="0.5.17 0.8.15 0.8.19"

FROM handsonsecurity/seedemu-base

COPY --from=node /usr/local/bin/op-node /usr/local/bin/op-node
COPY --from=foundry /usr/local/bin/forge /usr/local/bin/forge
COPY --from=foundry /usr/local/bin/chisel /usr/local/bin/chisel
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/cast
COPY --from=foundry /usr/local/bin/anvil /usr/local/bin/anvil

COPY l2.tar.gz /l2.tar.gz
RUN tar -xzf /l2.tar.gz && rm /l2.tar.gz

# Compile the smart contracts
RUN cd /l2 && forge build
