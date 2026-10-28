FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements change
COPY requirements.txt requirements-dbt.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dbt.txt

# Project code
COPY ingestion/ ./ingestion/
COPY dbt_project/ ./dbt_project/

# Run as a non-root user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

CMD ["python", "ingestion/generate_and_load.py"]