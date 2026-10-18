# Notebooks

Conventions for every notebook, in `learning/` and in `projects/`. They're written for two readers: Bertrand re-reading them later as his own reference, and reviewers (recruiters included) reading them on GitHub.

## Structure

- **Title** names the analysis (`# Exploratory data analysis`). The folder carries the project and the file name the number (`projects/01-hdb-resale/notebooks/01-eda.ipynb`), so the title repeats neither.
- **Header cell** under the title: goal, output, data source, and any rule the notebook follows (e.g. which months it may not use).
- **Table of Contents**: one linked entry per numbered section, `- [1. Load and structure](#toc-1)`. List sub-sections only when a section has several, labelled (a), (b), (c) like their headings: `  - [(a) Predict the mean](#toc-3a)`.
- **Anchors**: each linked heading's cell starts with `<a id="toc-N"></a>` (or `toc-Na` for a sub-section), then a blank line, then the heading. Explicit ids, because VS Code, GitHub and nbconvert generate heading slugs differently; the blank line, because without it Markdown treats the heading as part of the HTML block.
- **After editing a notebook from outside VS Code** (a script, nbconvert, an agent), VS Code keeps a stale rendering in which TOC links land in the wrong place or nowhere. Ask Bertrand to **close the notebook tab and reopen it** before testing links: the file is correct, the view isn't.
- **Analysis notebooks** end each section with a `### Findings (section N)` cell and the notebook with a summary turning the findings into decisions.

## Public-facing wording

State expectations before a result as **Hypotheses**, then report results neutrally. The learning back-and-forth (predictions, misses, corrections) stays in the conversation.

## Code

- In `projects/`, notebooks are for exploration only: reusable code goes into the project's package, and the notebook imports it. Ruff lints and formats project notebooks through the pre-commit hooks.
- A project notebook runs on **that project's environment** (`projects/<project>/.venv`, kernel named after the project), never the root `machine-learning` one (repo ADR-0001). The kernel's name is saved in the notebook's `metadata.kernelspec.display_name`: check it.
- In `learning/`, notebooks are hand-aligned and not run through Ruff.
- Edit notebooks through their JSON structure (or `NotebookEdit`), never by raw text replacement, which can break the JSON.
- Report notebooks are committed **with their outputs**: readers see the charts and numbers behind each finding on GitHub, and can't re-run them (the data sits in a private DVC remote). Size stays under the 1 MB large-file hook.
- A commit takes the file on disk: after a re-run in VS Code, the notebook must be saved before committing.
