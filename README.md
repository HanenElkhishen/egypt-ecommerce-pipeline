# Egypt E-commerce Analytics Pipeline

An end-to-end data engineering project: synthetic e-commerce data is generated
with Python, loaded into PostgreSQL, transformed with dbt, and every change is
validated automatically by GitLab CI/CD.

## Architecture

```
Python (Faker) -> PostgreSQL (raw) -> dbt (staging -> marts) -> GitLab CI/CD
```

## Tech stack

Python, PostgreSQL 16, Docker Compose, dbt, GitLab CI/CD, ruff, pytest.

## Project structure

| Path | Purpose |
|------|---------|
| `ingestion/` | Generates fake data and loads it into the `raw` schema |
| `docker/init/` | SQL that creates the `raw`, `staging`, `marts` schemas on first start |
| `dbt_project/` | dbt staging and marts models, tests and docs |
| `tests/` | Unit tests for the ingestion logic |
| `.gitlab-ci.yml` | CI pipeline definition |

## Getting started

```bash
cp .env.example .env          # then fill in the values
docker compose up -d
pip install -r requirements-dev.txt -r requirements-dbt.txt
python ingestion/generate_and_load.py
cd dbt_project && dbt build
```

## Data model

| Layer | Schema | Materialization | Purpose |
|-------|--------|-----------------|---------|
| Raw | `raw` | table | Data exactly as loaded, never modified |
| Staging | `staging` | view | Cleaned and typed data |
| Marts | `marts` | table | Analytics-ready: `fct_orders`, `dim_customers`, `daily_sales` |

### Cleaning rules applied in staging

- Duplicate customers are removed with `row_number()` over `customer_id`.
- Order statuses are lowercased and trimmed to a consistent set of four values.
- Emails are lowercased; missing emails stay `NULL` and raise a warning.

### Data tests

Uniqueness and not-null on primary keys, referential integrity between orders,
customers and items, and accepted values for order status. Missing emails raise
a **warning** instead of failing the build, because they are a data-quality
signal and not a pipeline-breaking error.

## Design decisions

- **Layered warehouse:** raw data is kept as received, so cleaning logic lives
  in one place and the source is always recoverable.
- **Idempotent ingestion:** the load script truncates before inserting, so
  running it twice gives the same result.
- **Deterministic fake data:** seeded generators make tests reproducible.
- **Intentional data quality issues** (null emails, duplicate customers,
  mixed-case statuses) give the data tests real problems to catch.
- **Secrets stay out of Git:** credentials live in `.env`, which is git-ignored.
  dbt reads connection details from environment variables.
- **Ephemeral CI database:** a PostgreSQL service container is created per
  pipeline, so tests are isolated and reproducible.
- **Merge-request pipelines only:** avoids duplicate pipelines and keeps
  `main` protected by required checks.

## CI/CD

The pipeline runs on every merge request and on `main`:

| Stage | Job | What it checks |
|-------|-----|----------------|
| lint | `ruff check` / `ruff format --check` | Code errors and formatting |
| test | `pytest` | Unit tests for data generation |
| dbt | `dbt_build` | Full end-to-end run: starts a throwaway PostgreSQL service, creates the schemas, loads generated data, then runs `dbt build` (models + tests) |

Each run uses a fresh, disposable database, so results never depend on previous
runs. A failing dbt test fails the pipeline and blocks the merge, so bad data
logic cannot reach `main`. Warnings (such as missing emails) are reported
without failing the build.

The `dbt_build` job saves `run_results.json` and logs as artifacts for debugging.

## Workflow

Feature branch -> Merge Request -> pipeline passes -> merge to `main`.