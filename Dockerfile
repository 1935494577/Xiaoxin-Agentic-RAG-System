FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    poppler-utils \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app/enterprise_rag/src
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

COPY enterprise_rag/ /app/enterprise_rag/

EXPOSE 8010

HEALTHCHECK --interval=15s --timeout=8s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=5)"

# Lite / BM25 为进程内文件状态：容器内保持单 worker
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8010", "--proxy-headers", "--forwarded-allow-ips", "*", "--app-dir", "/app/enterprise_rag/src"]
