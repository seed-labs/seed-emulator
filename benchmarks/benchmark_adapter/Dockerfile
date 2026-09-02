FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY benchmark_adapter benchmark_adapter
ENV PYTHONPATH=/srv
EXPOSE 8101
CMD ["python", "-m", "benchmark_adapter", "--host", "0.0.0.0", "--port", "8101"]
