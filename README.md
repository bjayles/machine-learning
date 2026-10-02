# Applied Machine Learning

## Context

This repository aims to build solid, broadly applicable machine learning
skills. Foundational understanding comes from Andrew Ng's Machine Learning
Specialization, offered by Stanford Online and DeepLearning.AI.

The repo has two parts: `learning/`, a set of self-contained machine learning
exercises, and `projects/`, a collection of polished, standalone builds
developed once a concept from `learning/` is solid.

The goal of this work is to develop a solid command of machine learning:
which algorithm to apply to what problem, under what conditions, and how to
judge whether a model is good. It also means knowing how to take those
skills from a notebook to something deployed and usable.

The focus is therefore on deep understanding rather than on code itself,
which is a prompt away with modern AI-aided coding.

## `learning/` logic

Each module takes one exercise and works it the way a machine-learning task
would actually get handled inside a company: a brief (context, objective,
what's been handed over), a decision about the right first approach, then
the work itself.

That framing is deliberate: it forces the same judgment calls a real ML
role would require (scoping the problem, picking a metric, deciding what to
try first), rather than following a tutorial's prescribed steps.

Each notebook states its approach — the reasoning behind the chosen method —
before any modeling code is written, and keeps narrating that reasoning as
the module progresses: why a given check comes first, why a decision is
deferred until there's evidence to justify it, why one metric is trusted
over another. That reasoning is as much a part of the notebook as the code
itself.

This stays deliberately low-ceremony (minimal process overhead) compared to
`projects/`. The point here is moving through problems quickly, not
maintaining production infrastructure for every exercise.

## `projects/` logic

Each project takes a concept already proven out in `learning/` and brings it
to the standard an actual deployed product would need: tests, CI,
reproducible packaging, and a working interface in place of a notebook.

That shift is deliberate too, and it forces a different kind of judgment:
not just whether a model performs well, but whether it is reliable, maintainable, and usable by someone other than its author.

Concretely, that means: experiment tracking to compare training runs instead
of trusting memory, a CI pipeline that gates on model quality and not just
passing tests, and a deployment target: a live, clickable demo rather than
a result sitting in a notebook. The standard shifts from "did the model
converge" to "would this hold up if someone else depended on it."

## Repository structure

```
learning/   self-contained ML exercises, one module per directory
projects/   polished, standalone builds (none yet; see `projects/` logic above)
src/        reusable code promoted out of notebooks once it stabilizes
```

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
and targets Python 3.12.

```bash
uv sync
```

Select the resulting `.venv` as the Jupyter kernel to run any notebook.

## Usage

Each `learning/` module is a single notebook, meant to be read top to
bottom: the brief, the reasoning behind each decision, and the code that
implements it, in that order.

Start here: `learning/01-regression-housing/notebook.ipynb`.
