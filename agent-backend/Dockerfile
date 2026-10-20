FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DEBUG=false \
    APP_LOG_LEVEL=INFO \
    APP_LOG_DIR=/tmp/ir-agent-logs \
    APP_CORS_ALLOW_ORIGINS= \
    NACOS_ENABLED=false \
    IR_FEISHU_ENABLED=false \
    IR_SPOT_ENABLED=false \
    IR_SPOT_DAILY_UPDATE_ENABLED=false

WORKDIR /srv/ir-agent

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt \
    && groupadd --gid 10001 ir-agent \
    && useradd --uid 10001 --gid 10001 --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin ir-agent

# Whitelist only runtime Python sources; local .env and application.yml never enter the build context.
COPY app/ ./app/
COPY tools/policy_ask.py tools/policy_refs.py tools/source_cache.py ./tools/
COPY container-entrypoint.sh ./container-entrypoint.sh

RUN mkdir -p /tmp/ir-agent-logs tools/_tmp_download tools/_cache \
    && chown -R 10001:10001 /tmp/ir-agent-logs tools/_tmp_download tools/_cache \
    && chmod 0555 container-entrypoint.sh

USER 10001:10001
EXPOSE 9089
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:9089/health', timeout=2).close()" || exit 1

ENTRYPOINT ["./container-entrypoint.sh"]
