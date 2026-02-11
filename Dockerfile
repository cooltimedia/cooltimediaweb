FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.web.txt /app/requirements.web.txt
RUN pip install --no-cache-dir -r /app/requirements.web.txt

COPY . /app
