# Contributing to Montage

Montage is a small project maintained by volunteers. Contributions are welcome — please read this before opening a PR.

We follow the [Wikimedia technical spaces Code of Conduct](https://www.mediawiki.org/wiki/Code_of_Conduct).

## Getting started

Check the [open issues](https://github.com/hatnote/montage/issues) for something to pick up. Issues tagged [`good-first-issue`](https://github.com/hatnote/montage/issues?q=is%3Aissue+is%3Aopen+label%3Agood-first-issue) are a good starting point.

Before writing any code, leave a comment on the issue to let maintainers know you're working on it and to confirm the approach. If no issue exists for what you want to do, open one first. **Do not open a PR without a corresponding issue that has received a response from a maintainer** — especially if you are a new contributor. This avoids wasted effort on both sides.

See [dev.md](dev.md) for local setup instructions.

## Before opening a PR

Follow the setup instructions in [dev.md](dev.md), including installing pre-commit hooks and running tests locally. Make sure tests pass before opening a PR.

## Pull request expectations

- CI must pass
- One focused change per PR — link the issue it addresses (`Fixes #NNN`)
- If your PR adds or changes database columns, include the SQL migration and flag it in the PR description
- Do not commit screenshots, generated files, or large binaries

## Code quality

- Follow existing patterns in the file you're editing
- Backend: read `montage/rdb.py` before writing queries — column names are authoritative there. Note that `.filter()` and `.order_by()` return new objects — always reassign
- Backend: write code that works with both MySQL (production) and SQLite (tests) — no MySQL-only syntax
- Frontend: use Composition API with `<script setup>` — no Options API
- All user-facing strings must go in `frontend/src/i18n/en.json` and use `t('key')` — TranslateWiki handles other locales, do not edit them manually

## When to open a PR for review

Only open a PR for review when you consider it ready to merge. If your work is still in progress, open it as a **draft PR** — maintainers will not review draft PRs.

A PR is ready for review when:
- It does one thing and does it completely
- CI passes
- You have tested it yourself and are confident it works
- You would be comfortable if it were merged as-is

Do not open a PR to ask for direction or feedback on an approach — use the issue for that conversation first.

When you are a new contributor to this codebase (e.g. not part of the maintainer team) we kindly ask you to make a screen recording of the platform with human voice-over that reproduces the issue locally, and shows the change after the implemented changes. Please also make sure to be explicit about your testing approach and the logic used. 

## Deployment

Only maintainers have access to the three Toolforge environments:

| Environment | Purpose |
|-------------|---------|
| montage-dev | Flexible test environment — maintainers can deploy any branch here |
| montage-beta | Tracks `master` — used by volunteers to catch bugs before production |
| montage-prod | Stable production — promoted manually when beta is stable |

Contributors do not need Toolforge access. Push your branch to GitHub and open a PR against `master`. A maintainer can then deploy your branch to montage-dev to test it — either in isolation or combined with other PRs to check interaction effects.

## Questions

Leave a comment on the relevant GitHub issue, or reach out on [Commons talk:Montage](https://commons.wikimedia.org/wiki/Commons_talk:Montage).
