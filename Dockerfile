# API PAC Qualidade DELPI — build a partir da raiz `projetos/` (irmão de delpi-central)

FROM python:3.11-slim

WORKDIR /app

COPY api-pac-quality/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY delpi-central/shared /shared
RUN pip install --no-cache-dir -e /shared[fastapi]

COPY api-pac-quality /app

RUN chmod +x /app/docker-entrypoint.sh

ENV API_PAC_QUALITY_PORT=8010
ENV API_PAC_ROOT_PATH=

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=3)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
