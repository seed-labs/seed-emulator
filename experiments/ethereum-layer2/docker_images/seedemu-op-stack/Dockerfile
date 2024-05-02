FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-batcher:v1.4.3 as batcher
FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:v1.4.3 as node
FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-proposer:v1.4.3 as proposer
FROM us-docker.pkg.dev/oplabs-tools-artifacts/images/op-geth:v1.101308.0 as geth

FROM alpine:3.14

COPY --from=batcher /usr/local/bin/op-batcher /usr/local/bin/op-batcher
COPY --from=node /usr/local/bin/op-node /usr/local/bin/op-node
COPY --from=proposer /usr/local/bin/op-proposer /usr/local/bin/op-proposer
COPY --from=geth /usr/local/bin/geth /usr/local/bin/geth

RUN apk --no-cache add bash jq iproute2 curl openssl