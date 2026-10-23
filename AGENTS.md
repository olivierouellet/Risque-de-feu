# Agent instructions

For AI coding assistants (Claude Code, GitHub Copilot, Codex, Cursor and others) working in this repository.
People should start with [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

A Home Assistant custom integration (`custom_components/risque_de_feu`, distributed through HACS) for SOPFEU's
forest fire danger in Québec: danger sensors for three days, an open-fire ban sensor, and an *Alert* binary
sensor that drives card visibility. The companion card is
[Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte).

## Before you finish

```bash
uv venv --python 3.13 && uv pip install -r requirements_test.txt   # once
ruff check && ruff format --check
pytest
```

All must pass; CI runs the same, plus HACS and hassfest validation.

## Conventions

* **French first.** Every document is bilingual, French section first; a change users see goes in both.
* `strings.json` is English and is copied unchanged to `translations/en.json`; `translations/fr.json` has
  the same keys. A test enforces both.
* **Tests never call the real service.** They use responses recorded in `tests/fixtures/`; record new ones
  with `test=true`, which returns all five levels and every measure type.
* The day rules in `danger.py` are mirrored in Risque-de-feu-Carte's `src/danger.ts`: change one, change the
  other.
* The danger is SOPFEU's: never compute or correct it.
* SOPFEU's API differs from its Swagger page, and these are deliberate in the code:
  * `danger-incendie` answers `[[zones], {"DateDernierCalculDanger": …}]`, not the documented object; both
    shapes are parsed.
  * A point lookup always returns the nearest zone, even outside Québec. `contour-municipalite` (empty
    outside Québec) is what tells.
  * `mesures-preventives` excludes every measure type unless its flag (`ifco=true`, …) is set.
  * A municipality can span several zones: the place's level is the highest.
* The manifest has no `requirements`; keep it that way. Python 3.13, Home Assistant 2025.1 or later.
* A release bumps `version` in `manifest.json` in a commit titled `[Integration] Version X.Y.Z`, then a
  GitHub release tagged `vX.Y.Z`.
* The icon's source is `assets/icon.svg`; `brand/icon.png` (256 px) and `brand/icon@2x.png` (512 px) are
  exported from it.

## Commits and publishing

* Commit titles read `[Topic] What changed`, one topic per commit. Topics in use: `[Integration]`, `[Tests]`, `[Tooling]`, `[Docs]`.
* **Never commit, push, tag, publish a release, or open an issue or pull request unless asked.** Approval for
  one of these is not approval for the next.
* `main` is protected against force-pushes and deletion: never rewrite history that is already pushed.
* Never post comments on issues or pull requests on the user's behalf without their review.

## AI policy

This project follows its [AI policy](AI_POLICY.md): a person reviews and understands every change, no
autonomous contributions, and nothing is posted on someone's behalf without their review.
