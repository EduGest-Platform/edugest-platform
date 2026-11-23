# Contexto de build: la raíz del repositorio (ver infra/compose.yaml y render.yaml).
FROM python:3.12-slim
WORKDIR /srv/api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY api/pyproject.toml ./
COPY api/app ./app
COPY api/alembic ./alembic
COPY api/alembic.ini ./
COPY api/docker-entrypoint.sh ./
RUN pip install --no-cache-dir .
# La semilla sintética se comparte con el prototipo web. Compose la monta encima en local;
# en despliegue (Render) viaja dentro de la imagen.
COPY src/gistar/seed.json /data/seed.json
ENV GISTAR_SEED_PATH=/data/seed.json
# Documentos sintéticos del RAG (KAN-130). Igual que la semilla: Compose los monta encima en local
# y en despliegue viajan dentro de la imagen.
COPY evals/rag/corpus /data/corpus
ENV GISTAR_CORPUS_PATH=/data/corpus
EXPOSE 8000
CMD ["sh", "/srv/api/docker-entrypoint.sh"]
