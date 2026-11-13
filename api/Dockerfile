FROM python:3.12-slim
WORKDIR /srv/api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN pip install --no-cache-dir .
# The synthetic seed is shared with the web prototype and mounted by compose at /data/seed.json
ENV GISTAR_SEED_PATH=/data/seed.json
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
