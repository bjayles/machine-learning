# Data storage: one S3 bucket in a dedicated workloads account

All projects store their DVC data (and later model artifacts) in one private S3
bucket, `bjayles-machine-learning` in `ap-southeast-1`, with one prefix per project
(e.g. `hdb-resale/`). The bucket lives in a member account, `bjayles-workloads`,
not in the AWS Organization's management account: the management account controls
billing, accounts and sign-in (IAM Identity Center), so we keep it free of
workloads and of the access paths they bring (laptop, CI, demo). An account
boundary is AWS's strongest isolation, so a leaked or misconfigured workload
credential can't reach those controls. Humans sign in through Identity Center with
short-lived credentials; no long-lived access keys exist anywhere, and CI will use
OIDC. Member-account root credentials are removed (centralized root access).

## Considered Options

- **Cloudflare R2.** S3-compatible and free at this scale, but it needs long-lived
  API tokens (no OIDC for GitHub Actions), and S3/IAM is the industry default.
  Cost didn't decide it: both are under $1/year here.
- **Bucket in the management account.** Zero extra setup, but goes against AWS
  guidance and would put CI and demo credentials next to the account's master
  controls.
