# ベース更新で全レイヤーのキャッシュが不意に失効しないよう digest を固定する。
# セキュリティ更新時は digest を明示的に更新すること。
ARG PYTHON_IMAGE=python:3.11-slim@sha256:be1575ed968de893bd54f4c56315ff7c4736ce522c1bca08fd521731aafc0d76

FROM ${PYTHON_IMAGE} AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-client \
    fonts-noto-cjk \
    libreoffice-calc-nogui \
    && rm -rf /var/lib/apt/lists/*

# UID 1000 はデプロイ先の一般ユーザーと合わせ、Compose secretを読み取り可能にする。
RUN groupadd --system --gid 1000 appgroup && \
    useradd --system --uid 1000 --gid appgroup --no-create-home appuser && \
    mkdir -p /home/appuser && \
    chown appuser:appgroup /home/appuser

COPY --from=builder /install/ /usr/local/

WORKDIR /code
COPY --chown=appuser:appgroup . /code/
RUN chown appuser:appgroup /code

USER appuser

FROM runtime AS development

USER root
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt
USER appuser

FROM runtime AS production

USER root
COPY --chown=root:root docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
