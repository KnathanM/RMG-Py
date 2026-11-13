---
name: rmg-contributing
description: Helps users get help with RMG and contribute back. It searches existing GitHub issues, gathers everything a good RMG bug report needs (RMG-Py and RMG-database commits, version, OS and install mode, input.py, RMG.log tail, exact error) and drafts the issue for the user to approve. It also covers the developer workflow: fork/branch, small PRs, unit, functional and database tests, regression tests and CI, and building the docs. Use when the user says "RMG crashed, help me report it", "file an issue", "ask the RMG developers", "is this a known RMG bug", "contribute to RMG", "open a pull request", "run the RMG tests", "add a regression test", or "build the RMG docs".
---

# Getting help and contributing to RMG

Based on the 2025 RMG Workshop talk “Contributing to RMG and GitHub Resources” and RMG-Py 3.3.0.

**Hard rule: never post an issue, comment or PR, or push to GitHub, without the user's explicit approval of the final text and the target repo.** Draft it, show it, and wait.

## 1. Pick the right place

Repos live under github.com/ReactionMechanismGenerator (see `RMG-Py/CONTRIBUTING.md`):

| Problem is about | Repo |
|---|---|
| RMG or Arkane code, crashes, install, CLI | **RMG-Py** issues |
| Families, rate rules, groups, thermo/kinetics libraries, wrong data | **RMG-database** issues |
| rmg.mit.edu website tools | **RMG-website** issues |
| RMS (Julia) simulator | ReactionMechanismSimulator.jl |

The `.github/ISSUE_TEMPLATE/` folder has three templates: `bug-report.md`, `feature.md` and `question.md`.

You can also email **rmg_dev@mit.edu** (in `CONTRIBUTING.md` and the FAQ).

## 2. Search before you report

There are well over 1,000 closed issues, and many install and Docker problems are already solved there. If the user has `gh` and agrees, search read-only:

```bash
gh search issues --repo ReactionMechanismGenerator/RMG-Py "<key phrase from the error>" --state all --limit 20
gh issue view <N> --repo ReactionMechanismGenerator/RMG-Py --comments
```

Otherwise, give the user search URLs of the form `https://github.com/ReactionMechanismGenerator/RMG-Py/issues?q=<terms>`.

Search with the **exception name plus a distinctive phrase**, for example `UndeterminableKineticsError`, `InvalidMicrocanonicalRateError`, `ForbiddenStructureException`, "Jupyter notebook Docker", or "conda env create Mac".

Also check `RMG-Py/documentation/source/users/rmg/faq.rst` and the rmg-install known-errors table.

## 3. Good bug report procedure (agent gathers, user posts)

1. **Collect the facts** with the bundled read-only script:

   ```bash
   PY=<rmg_env python> bash .claude/skills/rmg-contributing/templates/gather_bug_info.sh /path/to/job_dir $RMG_PY > /tmp/rmg_bug_info.txt
   ```

   It extracts the following:

   - **RMG-Py and RMG-database commits and the version**, from the top of `RMG.log`: the `Version:` banner and the lines after `The current git HEAD for RMG-Py is:` and `...RMG-database is:`.
   - `git describe --tags`, and whether there are local edits or local commits. Forked or modified code must be disclosed.
   - OS, install mode (Docker tag / conda+source / conda binary), Python, Cantera, and whether RMS is installed.
   - The **exact error** (traceback lines) and the **last 100 lines of `RMG.log`**.
   - The **`input.py`** that was actually run.

   Without the script, take the same items by hand: `head -40 RMG.log`, `tail -n 100 RMG.log`, `git describe --tags` in both repos, and `uname -a`. In Docker, also record the image tag from `docker ps -a`.

2. **Minimize, if cheap.** A smaller `input.py`, or `-i N`, that still reproduces the failure helps developers. Ask the user before spending compute on this.
3. **Fill in `templates/bug_report.md`.** It mirrors `.github/ISSUE_TEMPLATE/bug-report.md`.
   - Paste the logs verbatim inside `<details>` blocks.
   - **Include everything.** The maintainers asked for it: it is easier for them to skip text than to ask for it across time zones.
   - Redact private paths or proprietary species only if the user asks.
4. **Show the draft** and say which repo it targets. Only after the user explicitly approves, post it, either via `gh issue create --repo ReactionMechanismGenerator/<repo> --title ... --body-file ...` or by having the user paste it.
5. For a **question** or **feature** rather than a bug, use `question.md` or `feature.md` (Topic / Context / Question; Motivation / Desired Solution / Alternatives).

## 4. Developer workflow (code or database changes)

Source install (see the rmg-install skill), then:

1. **Fork** the repo on GitHub and add the fork as a remote. **Branch off an up-to-date `main`**, and rebase onto `main` before you start, to avoid conflicts.
2. **Keep the PR small** with focused commits. Commit messages should say *why* the change is needed. Follow PEP8.
3. Open a **draft PR** for work in progress. Fill in `.github/PULL_REQUEST_TEMPLATE.md` (Motivation, Description of Changes, Testing, Reviewer Tips).
4. **Requirements for merging:**
   - Unit tests, regression tests and coverage pass.
   - At least one reviewer approves.
   - New features need unit tests under `test/rmgpy/` or `test/arkane/`.
5. **Recompile after editing `.pyx`/`.pxd` files:** run `make`.

**Before opening a PR, check the following:**

- If the change spans both repos, CI must be pointed at the database branch. `.github/workflows/CI.yml` has `RMG_DATABASE_BRANCH: main` for that purpose.
- Database-only edits go in an RMG-database PR. See the rmg-add-data skill for the formats.
- Never commit to, or push from, the user's shared checkout without asking.

### Tests (from `Makefile` and `pytest.ini`)

Run these from `RMG-Py` with `rmg_env` active:

| Command | Runs |
|---|---|
| `make test` (alias `make test-unittests`) | `python -m pytest -m "not functional and not database"` (unit tests) |
| `make test-functional` | `pytest -m "functional"` |
| `make test-database` | `pytest -m "database"` (checks that RMG-database groups, rules and libraries are well formed; run this after any database edit) |
| `make test-all` | Everything (what CI runs) |
| `python -m pytest test/rmgpy/speciesTest.py -k "name_pattern" --no-cov` | One file or test, quickly |

`pytest.ini` settings:

- Test files are `*Test.py`, and classes are `*Test` or `Test*`.
- `testpaths = test`, and `--ignore test/regression`.
- Markers are `functional` and `database`; unmarked tests are unit tests.
- Coverage HTML is written by default (`--cov ... --cov-report html`). Add `--no-cov` for speed, or when using a debugger.
- `pytest-xdist` (`-n auto`) is not in `environment.yml`, and the docs say it doesn't work well with Julia. Developers keep a second env without RMS for fast parallel tests.

The full suites take a long time. Ask before running `make test-all`, and run long suites in the background.

### Regression tests and CI

- CI (`.github/workflows/CI.yml`) does three things:
  - Builds RMG on several platforms and Python versions and runs `make test-all` (about 2,000 unit tests).
  - Runs every input in a fixed list of `test/regression/*/input.py` files.
  - Compares the resulting mechanisms against the "stable" results from `main`, using `scripts/checkModels.py` and `rmgpy/tools/regression.py`. Stable results are regenerated daily and on every push to `main`.
- **Adding a regression test** for a significant feature (`CONTRIBUTING.md`):
  1. Write an `input.py` that exercises the feature, with `saveEdgeSpecies=True`. It must finish in **15 minutes or less**; raise `toleranceMoveToCore` to shorten it.
  2. Put it in `test/regression/<name>/input.py`.
  3. Add `<name>` to **both** loops in `CI.yml`: the "Regression Tests - Execution" step and the "Regression Tests - Compare to Baseline" step.
  4. Expect CI to fail on the first PR, because no baseline exists yet. Maintainers merge it by bypassing protection.
- Regression differences are not always real. Thermo for fused-ring species is non-deterministic, so the regression report can flag spurious changes. Ask reviewers to help interpret it.

### Documentation

- Docs are Sphinx `.rst` files under `RMG-Py/documentation/source/`. They are published to the `gh-pages` branch on pushes to `main`.
- Build them with `make documentation`, or `make html` inside `documentation/`. The output starts at `documentation/build/html/index.html`.
- Sphinx is **not** in `environment.yml`; install it first with `conda install sphinx`, after asking the user.

## Gotchas

- **ARM Macs** are poorly tested, because most developers use Linux on x86. The maintainers explicitly want those failures reported.
- A crash in a run on modified code must be reported as such. Check `git status`, and in RMG-Py `git log @{u}..HEAD`.
- `CoreError: ... isomorphic to species ... in the core` and other "should never happen" errors are worth reporting with the full input.
- Don't paste huge files inline. Attach `RMG.log` or `chem_annotated.inp`, or link a gist, if the user approves.

When unsure, check:

- `RMG-Py/CONTRIBUTING.md`
- `RMG-Py/.github/ISSUE_TEMPLATE/*.md` and `RMG-Py/.github/PULL_REQUEST_TEMPLATE.md`
- `RMG-Py/.github/workflows/CI.yml`
- `RMG-Py/Makefile` and `RMG-Py/pytest.ini`
- `RMG-Py/documentation/source/users/rmg/installation/anacondaDeveloper.rst` (Test Suite, Debugging)
