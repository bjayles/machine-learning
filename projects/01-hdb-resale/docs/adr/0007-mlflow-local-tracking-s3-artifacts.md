# MLflow tracking runs locally, artifacts go to S3

Every pipeline run is logged to MLflow: its params, its metrics per backtest window and period, and its files. The **tracking store** (params, metrics, tags) is a local SQLite file, `mlflow.db`, kept out of git, browsed with `mlflow ui`. The **artifact store** (model, per-window metrics) is the project's prefix in the shared S3 bucket, `s3://bjayles-machine-learning/hdb-resale/mlflow/` (repo ADR-0001, ADR-0002). This costs nothing, needs no server, and keeps everything private in our AWS account, like the DVC remote (ADR-0003). The code reads the tracking URI from configuration and never hard-codes it, so moving to a server later means changing that setting and exporting past runs once.

Until then, the run history exists only on one laptop: losing it loses the history, but not the artifacts in S3, and `dvc repro` can rebuild any committed result.

## Considered Options

- **Self-hosted server on AWS** (EC2 or ECS, with S3). Reachable by CI, but about $5–15 a month and a server to patch and secure, for one user.
- **SageMaker managed MLflow.** No upkeep and stays in our account, but a provisioned tracking server costs about $0.60 an hour (around $430 a month).
- **Free tiers (Databricks Free Edition, DagsHub).** Free and reachable by CI, but runs and models sit on a third party's servers under non-commercial terms and usage caps that can change, artifacts leave our S3 bucket, and CI would authenticate with a long-lived token, which repo ADR-0002 rules out.

## Consequences

Revisit at step 7, when the monthly retraining on GitHub Actions has to log runs to a store it can reach: compare a small self-hosted server with a free tier (checking OIDC support and terms then).
