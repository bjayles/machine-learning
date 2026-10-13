# Workflow

How changes reach `main`, and which credentials to use.

## Branches and PRs

Every change lives on its own branch and reaches `main` through a PR that Bertrand reviews and merges himself. Commit in small, self-contained steps on that branch; the `no-commit-to-branch` hook refuses commits made on `main`.

## Pre-commit hooks

Every commit runs the hooks in `.pre-commit-config.yaml` (Ruff for each project, secret scanning, large-file and syntax checks). After a fresh clone, enable them with `pre-commit install` (see the root `README.md`, Setup).

When a hook modifies files (Ruff fixes, formatting, whitespace), the commit stops on purpose: review the diff, `git add` the fixed files, and commit again. A hook that fails without fixing anything points at a real problem: fix the cause and keep every commit going through the hooks (no `--no-verify`).

## Project commands

Each project is independent (repo ADR-0001): run its commands from its folder (`projects/<project>/`), or from the root with `uv run --directory projects/<project> ...`.

## AWS profiles

Sign in with `aws sso login --profile <profile>`; credentials are short-lived and no long-lived access keys exist (repo ADR-0002).

- `bjayles-workloads-admin`: project work (S3 data, DVC, anything a project runs). The default choice.
- `bjayles-admin`: management account, for account administration only (Organizations, IAM Identity Center, billing).
