# Dockerfile — FastAPI + MySQL (compatible con SQLite en local)
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Paquetes mínimos (wget para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends wget \
 && rm -rf /var/lib/apt/lists/*

# Dependencias de Python del backend
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Código del backend
COPY backend/ /app/

# Puerto
EXPOSE 8000

# Healthcheck simple
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8000/health || exit 1

# Arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
