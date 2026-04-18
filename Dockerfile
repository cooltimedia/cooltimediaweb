FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for WebP and image processing
RUN apt-get update && apt-get install -y \
    libwebp-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.web.txt /app/requirements.web.txt
RUN pip install --no-cache-dir -r /app/requirements.web.txt

COPY . /app