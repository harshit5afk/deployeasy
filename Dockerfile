FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first, so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --from=frontend-build /app/app/static/dist ./app/static/dist
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# The pipeline passes the commit SHA so /version shows what is running
ARG GIT_SHA=dev
ENV GIT_SHA=${GIT_SHA} PORT=8080

# Do not run as root
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser:appuser /app/data
USER appuser

EXPOSE 8080

# Python standard library instead of curl (curl is not in the slim image)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health',timeout=3)"

# One worker so the in-memory counters make sense. Render provides PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
