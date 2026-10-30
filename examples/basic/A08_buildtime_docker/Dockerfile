FROM python:slim

WORKDIR /app

# Install minimal build tools required to build native dependencies (e.g., ckzg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN PYTHONDONTWRITEBYTECODE=1 pip install --progress-bar off --no-cache-dir eth-account

ENTRYPOINT [ "python", "-c", "import eth_account; print(eth_account.__version__)" ]
