FROM handsonsecurity/seedemu-multiarch-base:buildx-latest

# Install software-properties-common, python3, python3-pip, and required tools
RUN apt-get update && \
    apt-get install -y software-properties-common python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install web3

# Copy remaining binaries to /usr/local/bin
COPY binaries/lighthouse /usr/local/bin/
COPY binaries/geth /usr/local/bin/
COPY binaries/devp2p /usr/local/bin/
COPY binaries/eth-beacon-genesis /usr/local/bin/
COPY binaries/eth2-val-tools /usr/local/bin/

# Ensure binaries are executable
RUN chmod +x /usr/local/bin/lighthouse && \
    chmod +x /usr/local/bin/geth && \
    chmod +x /usr/local/bin/devp2p && \
    chmod +x /usr/local/bin/eth-beacon-genesis && \
    chmod +x /usr/local/bin/eth2-val-tools
