# Servidor de seguimiento MLflow para desarrollo y demo (no es una instalación de producción).
FROM python:3.12-slim
ARG MLFLOW_VERSION=3.1.1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir "mlflow==${MLFLOW_VERSION}" "sqlalchemy==2.0.41"
WORKDIR /mlflow
EXPOSE 5000
# Los artefactos se suben por HTTP (--serve-artifacts), así los clientes no necesitan acceso al volumen.
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", "--port", "5000", \
     "--backend-store-uri", "sqlite:////mlflow/mlflow.db", \
     "--artifacts-destination", "/mlflow/artifacts", \
     "--serve-artifacts"]
