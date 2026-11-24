---
gist: "Read me when: you run, change or roll back the pinned deterministic-controls adoption, or you need to know why the Dockerfile has a cache step."
---

# Controls adoption

This repository runs the pinned `deterministic-controls` library in advisory mode. The CI job `controls` is not a required check yet.

## How it works

- `scripts/check_context.py` is a shim. It runs the library `check` command with the `ci` profile.
- The shim keeps the old output lines (`ok  <script>` or `FAIL <script>`) and the exit codes `0` and `1`.
- `scripts/controls-requirements.txt` holds the pin: one install line with a full commit. The shim reads the commit from it.
- `controls.toml` lists the enabled checks.
- The shim runs the library from a cached virtual environment. The cache path is `$XDG_CACHE_HOME/deterministic-controls/<commit>/`. The default is `~/.cache/deterministic-controls/<commit>/`.
- The first run for a commit needs the network. The shim builds the cache then.
- If the library cannot run, the shim exits `2`. It never passes without a result. It never falls back to the old scripts.
- The old check scripts stay in `scripts/`. The shim does not call them.

## How the adoption was made

1. Audit: step `a01-audit` ran the read-only audit. The result is in `docs/controls-audit.json`.
2. Plan: `adopt plan` made a dry run for the pinned commit. A person read it.
3. Apply: `adopt apply` wrote the shim, the pin, `controls.toml` and the `controls` CI job. It ran on a clean tree, before any other edit.
4. By hand: the Dockerfile cache step, the standing rule in `AGENTS.md`, and this file.

## Where the tools did not fit

- **Docker run has no network.** The shim needs the network once for the pinned commit. The test run uses `--network none`. The `Dockerfile` now prepares the shim cache at image build time, as user `tester`, because the cache is under that user's home. The build has network. The run only reads the cache.
- **The image had no `git` program.** The shim setup needs `git` to install from the pinned commit. `tests/test_secret_guard.py` also needs it. The `Dockerfile` installs `git` with `apt-get` as root, before `USER tester`.
- **Read-only root file system.** The Docker run uses `--read-only` with a tmpfs `/tmp`. The cache must be complete at build time, so the shim writes nothing at run time. Whether the shim writes elsewhere is checked by the Docker gate. No write outside `/tmp` is known.
- **`adopt apply` changed a file outside the plan.** It rewrote `scripts/install_hooks.sh` (a `secretguard.path` fallback). That file is outside the scope of this step. It was restored from the commit before `apply`.
- **`adopt plan` does not cover the Dockerfile.** It gave no change for the Docker gate. The `Dockerfile` change was made by hand.
- **`adopt apply` did not commit.** The step made the commit.
- **The session could not run Docker.** The step ran the other parts of the gate. The driver runs the Docker gate.

## Probes

Step `a03-probes` ran each probe in a throwaway clone of the repository. Each clone was inside the worktree and was never tracked. Each run used `python3 -m deterministic_controls check --root <clone> --profile ci --format json`. The rule ID comes from the JSON. All runs were on 2026-11-24 (UTC).

| Probe | Expected rule | Rule ID found | Exit code | Result |
| --- | --- | --- | --- | --- |
| Broken relative link in a Markdown file | `markdown.local-links` | `markdown.local-links.missing-file` | 1 | pass: probe failed as expected |
| Stale generated index (script changed, index not rebuilt) | `context.index-freshness` | `context.index-freshness.stale` | 1 | pass: probe failed as expected |
| Plan step without `gate` | `plans.schema` | `plans.schema.missing-gate` | 1 | pass: probe failed as expected |
| Synthetic token in a committed Markdown file | `security.secrets` | `security.secrets.aws-access-key-id` | 1 | pass: probe failed as expected |
| Tracked `driver.out` file | `repo.forbidden-artifacts` | `repo.forbidden-artifacts.tracked` | 1 | pass: probe failed as expected |
| Internal error (unreadable `controls.toml`) | none: the check must not pass | none | 3 | pass: check did not pass |
| Old shim `python3 scripts/check_context.py` with the plan step without `gate` | `plans.schema` | `check_plan.py` reported FAIL | 1 | pass: shim exit code is 1 |
| Each clone restored | none | none | 0 | pass: all checks passed |

Notes:

- The shell built the synthetic token at run time. The token is not in any tracked file. The copy that held it was deleted.
- The token probe also raised a `security.personal-data` finding. That is expected for the same content.
- The unreadable-file probe printed an `internal error: PermissionError` line and exited `3`.

## Rollback

The rollback was tested on 2026-11-24 (UTC).

- Base commit: the parent of the `adopt apply` commit, `ebbef46`. Its `python3 scripts/check_context.py` ran the four old scripts on a clean clone. Result: pass (exit `0`).
- Adopted `HEAD`: the new shim ran on a clean clone. Result: pass (exit `0`).

Files of the adoption:

- Added: `controls.toml`, `scripts/controls-requirements.txt`, `docs/controls-adoption.md`.
- Changed: `scripts/check_context.py` (now the shim), `.github/workflows/context.yml` (new `controls` job), `Dockerfile` (git and cache step), `AGENTS.md` (standing rule), `scripts/AGENTS.md` and `docs/README.md` (indexes), `scripts/build_indexes.py`, `scripts/anthropic_cost_estimator.py` and `scripts/openai_cost_estimator.py` (index alignment and `Run me when:` lines).
- Kept (from the earlier secret guard step, not changed by the adoption): `scripts/secret_guard.py`, `scripts/install_hooks.sh`. The old check scripts also stay in `scripts/`.

Steps to roll back:

1. Option A, change the pin: edit `scripts/controls-requirements.txt` and put the previous commit in the install line. Run `python3 scripts/check_context.py` once to build its environment. There is no earlier pin now, so use option B for a full rollback.
2. Option B, revert: create a new branch. Run `git revert` on the adoption commits. Or restore the changed files from the base commit with `git checkout ebbef46 -- <file>` and delete the added files.
3. Run `python3 scripts/check_context.py`. The old scripts must pass.

The cache under `$XDG_CACHE_HOME/deterministic-controls/<commit>/` is safe to delete. The shim builds it again when it is needed.

## Receipt

The receipt came from `python3 -m deterministic_controls adopt receipt --root <clean clone> --commit 3a2e9f3d95136958c54f73c831e84b971fc9a054`. The run was on 2026-11-24 (UTC), in a clean clone of `HEAD`.

- `repository` is the name of the temporary clone, not of this repository.
- `files_added` and `files_changed` are empty in a clean clone. This is a known library defect. The Rollback section lists the files.
- `enforcement_state` is `advisory`.

```json
{
  "base_revision": "1c777e68aa0b1f2629c2dc21205209f648636ff5",
  "checks_run": [
    {"check_id": "context.index-freshness", "status": "passed"},
    {"check_id": "markdown.local-links", "status": "passed"},
    {"check_id": "plans.graph", "status": "passed"},
    {"check_id": "plans.schema", "status": "passed"},
    {"check_id": "repo.forbidden-artifacts", "status": "passed"},
    {"check_id": "security.personal-data", "status": "passed"},
    {"check_id": "security.secrets", "status": "passed"}
  ],
  "commands_kept": [
    "scripts/anthropic_cost_estimator.py",
    "scripts/build_context_indexes.py",
    "scripts/build_indexes.py",
    "scripts/check_links.py",
    "scripts/check_plan.py",
    "scripts/ctx_common.py",
    "scripts/openai_cost_estimator.py",
    "scripts/scan_context_secrets.py",
    "scripts/scan_secrets.py",
    "scripts/test_docker.sh",
    "test: python3 -m unittest discover -s tests",
    "test: docker build (Dockerfile)",
    "ci-job: check"
  ],
  "control_pin": "3a2e9f3d95136958c54f73c831e84b971fc9a054",
  "date": "2026-11-24",
  "enabled_checks": [
    "context.index-freshness",
    "markdown.local-links",
    "plans.graph",
    "plans.schema",
    "repo.forbidden-artifacts",
    "security.personal-data",
    "security.secrets"
  ],
  "enforcement_state": "advisory",
  "files_added": [],
  "files_changed": [],
  "profile": "ci",
  "repository": "head",
  "rollback": [
    "To restore the previous pin: edit scripts/controls-requirements.txt, put the previous commit in the install line, and run scripts/check_context.py once to build its environment.",
    "To remove the adoption: run 'git revert' on the adoption commit, or restore these files from the base revision 1c777e68aa0b1f2629c2dc21205209f648636ff5 with 'git checkout 1c777e68aa0b1f2629c2dc21205209f648636ff5 -- <file>' and delete the files that were added: scripts/check_context.py, scripts/controls-requirements.txt, controls.toml, scripts/secret_guard.py, scripts/install_hooks.sh, .github/workflows/context.yml.",
    "The cached environment is in the user cache directory under deterministic-controls/<commit>/. It is safe to delete."
  ],
  "schema_version": 1
}
```

The `rollback` text in the receipt names the wrong base revision and the wrong added files. Use the Rollback section above.

## Secret guard exceptions

none
