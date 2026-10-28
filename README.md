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
Dockerfile
load_env.ps1

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
- **Fail fast:** cheap source checks run before dbt, so broken input stops the
  pipeline before expensive transformations.
- **Severity is a decision, not a default:** each test is deliberately set to
  error or warn depending on whether it makes the data unusable.
- **Secrets are never baked into the image:** `.env` is excluded via
  `.dockerignore` and credentials are injected as environment variables at runtime.
- **Layer caching:** dependencies are installed before the code is copied, so
  code-only changes rebuild in seconds.
- **Non-root container user** to follow least-privilege practice.
- **Build on merge requests, push only from `main`:** broken Dockerfiles are
  caught early, but only reviewed code is published.
- **Immutable commit-SHA tags** alongside `latest` make every release traceable.


## Data quality

Quality is enforced in three layers, each catching a different class of problem:

| Layer | Tool | Examples |
|-------|------|----------|
| Source checks | `ingestion/check_raw.py` | Tables not empty, no orphan order items, no non-positive quantities |
| Model tests | dbt tests | Unique/not-null keys, referential integrity, accepted statuses, positive prices, revenue reconciliation between marts and staging, no future-dated orders, minimum row volume |
| Freshness | `dbt source freshness` | Warns if raw data is older than 24h, fails after 72h |


### Error vs. warning

- **Error** (blocks the merge): the data would mislead reports, e.g. duplicate
  order IDs, negative prices, totals that do not reconcile.
- **Warning** (reported only): a real issue that does not invalidate the
  pipeline, e.g. missing emails, or orders placed before the customer's signup
  date (a known limitation of the synthetic generator).

Custom tests live in `dbt_project/tests/`: a reusable generic test
(`positive_value`) and singular tests for specific business rules.


## Docker image

The project is packaged as a single image (Python, dbt, ingestion code) and
published to the GitLab Container Registry.

```bash
docker build -t egypt-ecommerce-pipeline:local .
docker run --rm --env-file .env -e POSTGRES_HOST=host.docker.internal \
  egypt-ecommerce-pipeline:local                     # load data
docker run --rm --env-file .env -e POSTGRES_HOST=host.docker.internal \
  -w /app/dbt_project egypt-ecommerce-pipeline:local \
  dbt build --profiles-dir .                         # run dbt
```

Image tags: `latest` (current `main`) and the commit SHA (for reproducible
rollbacks).


## CI/CD

| package | `build_image` | Builds the Docker image on every merge request; pushes it to the registry from `main` only |


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