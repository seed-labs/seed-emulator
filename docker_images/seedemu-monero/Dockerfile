FROM handsonsecurity/seedemu-multiarch-base:buildx-latest

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ENV MONERO_VERSION=v0.18.3.3 \
    MONERO_SHA256_AMD64=47c7e6b4b88a57205800a2538065a7874174cd087eedc2526bee1ebcce0cc5e3 \
    MONERO_SHA256_ARM64=eb3f924c085ae5df85f5bf9ee27faaa20acd309835684e27e3fbb98b9666b649 \
    BUILDKIT_SANDBOX_UID=0 \
    BUILDKIT_SANDBOX_GID=0

# Pin the CLI bundle to v0.18.3.3 to keep the emulator reproducible.

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl bzip2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/monero

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) MONERO_PLATFORM=linux-x64; MONERO_SHA256="${MONERO_SHA256_AMD64}" ;; \
      arm64) MONERO_PLATFORM=linux-armv8; MONERO_SHA256="${MONERO_SHA256_ARM64}" ;; \
      "") MONERO_PLATFORM=linux-x64; MONERO_SHA256="${MONERO_SHA256_AMD64}" ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    archive="monero-${MONERO_PLATFORM}-${MONERO_VERSION}.tar.bz2"; \
    url="https://downloads.getmonero.org/cli/${archive}"; \
    curl -L --fail --retry 3 "$url" -o "/tmp/${archive}"; \
    echo "${MONERO_SHA256}  /tmp/${archive}" | sha256sum -c -; \
    tar -xf "/tmp/${archive}" --strip-components=1; \
    rm "/tmp/${archive}"; \
    ln -sf /opt/monero/monerod /usr/local/bin/monerod; \
    ln -sf /opt/monero/monero-wallet-cli /usr/local/bin/monero-wallet-cli; \
    ln -sf /opt/monero/monero-wallet-rpc /usr/local/bin/monero-wallet-rpc

CMD ["/bin/bash"]
