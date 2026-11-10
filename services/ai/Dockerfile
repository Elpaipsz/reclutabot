FROM python:3.12-slim
WORKDIR /app
COPY ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY ai/ .
CMD ["python", "worker.py"]
