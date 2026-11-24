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

## Secret guard exceptions

none
