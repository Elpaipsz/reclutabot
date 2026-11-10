FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy
WORKDIR /app
RUN pip install --no-cache-dir playwright==1.49.0 httpx==0.27.*
COPY common ./common
COPY rpa/worker.py .
CMD ["python", "worker.py"]
