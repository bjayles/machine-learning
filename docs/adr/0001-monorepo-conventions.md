# Monorepo conventions: independent projects, root environment for learning only

This repo holds `learning/` exercises and several `projects/`, each deployed
on its own. Every project is an independent Python package with its own
`pyproject.toml`, `uv.lock`, DVC setup (`dvc init --subdir`), ADRs and
glossary, and its own CI workflow (in the root `.github/workflows/`,
triggered only by changes under the project's folder). The root
`pyproject.toml` is a plain environment (`package = false`) serving
`learning/` only; projects never depend on it, and shared code is copied
deliberately. This is the monorepo equivalent of "one repo per service": a
project's Docker image carries only what it needs, and its folder can be
extracted into its own repo without breaking. Projects share one private
data-storage bucket, with one prefix per project.

## Considered Options

- **Add project dependencies to the root environment.** Rejected: deployed
  images would carry Jupyter and plotting libraries, and `learning/` would
  pick up MLOps tooling it doesn't need.
- **uv workspace (one shared lockfile).** Rejected: forces compatible
  versions across all projects and `learning/`, coupling things that should
  evolve separately. Worth revisiting only if projects start sharing code.
- **Keep a root `src/` package for shared code.** Removed: it held only the
  `uv init` stub, nothing imported it, and projects may not depend on it.
  Recreate it if two `learning/` modules ever need a shared helper.
