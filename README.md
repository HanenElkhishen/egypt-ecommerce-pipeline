# Egypt E-commerce Analytics Pipeline

An end-to-end data engineering project: synthetic e-commerce data is generated
with Python, loaded into PostgreSQL, transformed with dbt, packaged in Docker,
and deployed to dev and prod environments by GitLab CI/CD.

## Architecture

```
Python (Faker) -> PostgreSQL (raw) -> dbt (staging -> marts)
                                          |
        GitLab CI/CD: lint -> test -> dbt build -> Docker image
                                          |
                     Neon Postgres: dev (automatic) -> prod (manual approval)
```

## Tech stack

Python, PostgreSQL 16, Docker, dbt, GitLab CI/CD, GitLab Container Registry,
GitLab Pages, Neon (hosted Postgres), ruff, pytest.

## Project structure

| Path | Purpose |
|------|---------|
| `ingestion/` | `generate_and_load.py` creates fake data and loads the `raw` schema; `check_raw.py` validates it |
| `dbt_project/` | dbt staging and marts models, tests and docs |
| `docker/init/` | SQL that creates the schemas on first start of the local database |
| `tests/` | Unit tests for the ingestion logic |
| `Dockerfile` | Packages Python, dbt and the project code into one image |
| `docker-compose.yml` | Local PostgreSQL |
| `.gitlab-ci.yml` | CI/CD pipeline definition |

## Getting started

```bash
# 1. copy .env.example to .env and fill in the values
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

Cleaning rules applied in staging:

- Duplicate customers are removed with `row_number()` over `customer_id`.
- Order statuses are lowercased and trimmed to four consistent values.
- Emails are lowercased; missing emails stay `NULL` and raise a warning.

## Data quality

Quality is enforced in three layers:

| Layer | Tool | Examples |
|-------|------|----------|
| Source checks | `ingestion/check_raw.py` | Tables not empty, no orphan order items, no non-positive quantities |
| Model tests | dbt tests | Unique and not-null keys, referential integrity, accepted statuses, positive prices, revenue reconciliation between marts and staging, no future-dated orders, minimum row volume |
| Freshness | `dbt source freshness` | Warns if raw data is older than 24h, fails after 72h |

**Errors vs. warnings:** an error blocks the merge when the data would mislead
reports (duplicate order IDs, negative prices, totals that do not reconcile).
A warning is reported without failing the build when the issue is real but not
pipeline-breaking (missing emails, orders placed before the customer signed up,
a known limitation of the synthetic generator).

## CI/CD

| Stage | Job | What it does |
|-------|-----|--------------|
| lint | `lint` | `ruff check` and `ruff format --check` |
| test | `test` | Unit tests for data generation |
| dbt | `dbt_build` | Throwaway PostgreSQL service, loads data, source checks, `dbt build`, `dbt docs generate` |
| package | `build_image` | Builds the Docker image; pushes it to the registry from `main` only |
| package | `pages` | Publishes the dbt docs site (`main` only) |
| deploy_dev | `deploy_dev` | Runs the built image against the dev database (automatic) |
| deploy_prod | `deploy_prod` | Same image against production, after manual approval |

Merge requests cannot be merged unless the pipeline passes. `main` is protected:
the only way in is a merge request.

### Docker image

The project is packaged as one image and published to the GitLab Container
Registry, tagged `latest` and with the commit SHA. Secrets are excluded via
`.dockerignore` and injected as variables at runtime.

### Deployment

Both environments run the **same image** (build once, deploy many) against
separate Neon Postgres databases (`ecommerce_dev`, `ecommerce_prod`).
Connection details are environment-scoped CI/CD variables: passwords are masked
and production variables are protected. `deploy_prod` waits for manual approval,
and GitLab Environments keep the deployment history for rollbacks.

### Automation and documentation

- A **scheduled pipeline** refreshes the dev environment every day at 06:00
  (Cairo time): reload data, check source freshness, run `dbt build`.
  Production is never touched automatically.
- The **dbt docs and lineage graph** are published to GitLab Pages on every
  merge to `main`: https://egypt-ecommerce-pipeline-968e58.gitlab.io/#!/overview?g_v=1

## Design decisions

- **Layered warehouse:** raw data is kept as received, so cleaning logic lives in
  one place and the source is always recoverable.
- **Idempotent ingestion:** the load script truncates before inserting, and
  creates the `raw` schema if missing, so running it twice (or on a new
  database) gives the same result.
- **Deterministic fake data:** seeded generators make tests reproducible.
- **Intentional data quality issues** (null emails, duplicate customers,
  mixed-case statuses) give the data tests real problems to catch.
- **Fail fast:** cheap source checks run before dbt, so broken input stops the
  pipeline early.
- **Severity is a decision, not a default:** each test is deliberately set to
  error or warn.
- **Ephemeral CI database:** a PostgreSQL service is created per pipeline, so
  tests are isolated and reproducible.
- **Build once, deploy many:** dev and prod run the exact image that was tested.
- **Secrets never live in the repository or the image:** only masked,
  environment-scoped CI/CD variables.
- **Scheduled runs skip CI jobs:** nightly pipelines only refresh dev.
- **Docs come from the same run that passed the tests**, so published
  documentation always matches validated code.

## Workflow

Feature branch -> merge request -> pipeline passes -> merge to `main` ->
automatic deploy to dev -> manual approval -> deploy to prod.