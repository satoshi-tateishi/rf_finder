FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    default-mysql-client \
    build-essential \
    pkg-config \
    fonts-noto-cjk \
    libreoffice-calc-nogui \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 非 root ユーザーを作成（UID 1000 はホストの一般ユーザーと一致させる）
RUN groupadd --system --gid 1000 appgroup && \
    useradd --system --uid 1000 --gid appgroup --no-create-home appuser

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . /code/

# /code の所有権を appuser に変更
RUN chown -R appuser:appgroup /code

USER appuser
