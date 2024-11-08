FROM python:slim

WORKDIR /app

RUN PYTHONDONTWRITEBYTECODE=1 pip install --progress-bar off --no-cache-dir eth-account

ENTRYPOINT [ "python", "-c", "import eth_account; print(eth_account.__version__)" ]
