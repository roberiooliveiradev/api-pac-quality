# API PAC Qualidade DELPI — build a partir da raiz `projetos/` (irmão de delpi-central)

FROM python:3.11-slim

WORKDIR /app

COPY api-pac-quality/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY delpi-central/shared /shared
RUN pip install --no-cache-dir -e /shared[fastapi]

COPY api-pac-quality /app

EXPOSE 8010

CMD ["python", "-m", "uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8010", "--root-path", "/apps/api-pac-quality"]
