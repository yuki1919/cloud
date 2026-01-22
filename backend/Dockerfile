# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt /app/requirements.txt
# 优先安装 CPU 版 Torch，避免拉取 CUDA 依赖（可在国内加速站点缓存）
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.2+cpu && \
    pip install --no-cache-dir -r /app/requirements.txt

# 将后端代码放入包目录 /app/backend
COPY . /app/backend
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
