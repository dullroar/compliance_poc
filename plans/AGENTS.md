# Plans index

<!-- IMMUTABLE HEADER: do not edit the text above the BEGIN marker. -->

This folder holds the plans for agents. Humans read `docs/` instead.

- One plan is one folder: `plans/<plan-name>/`. Copy `for-each-plan/` to start a plan.
- `goal.md` holds the goal and Ralph loop prompt. `plan.md` holds the high-level plan and starts with a `gist` in front matter.
- `spec.md` holds requirements and protected checks. Each file in `steps/` lists the requirement IDs it covers.
- A step is small. A small model or agent can implement, test and verify it alone.
- Run a plan in its own Git worktree and on its own branch. Give each step its own branch and worktree when using Ralph. Never commit to `master`.
- Steps that run at the same time must not touch the same files (see `touches` in the step front matter).
- A plan must survive a stop at any time. Another agent must be able to continue from the files in the repository. Record status and evidence in the step files.
- Keep runtime output, including logs, temporary usage records and locks, outside the repository. Use `~/repo-work/<repo>/<plan>/` on Unix or `%USERPROFILE%\repo-work\<repo>\<plan>\` on Windows. Keep durable spending ledgers at the paths specified in the [root contract](../AGENTS.md#safety).
- Never put PII, secrets or personal paths in a plan.
- Write in Simplified Technical English (ASD-STE100).
- This file is generated. Run `python3 scripts/build_indexes.py` after any change. Do not edit the list below by hand.

Read the list. Open only the plans whose "Read me when" line matches your task.

See [archived plans](./archive/) for completed work and the [legacy template](./archive/legacy-template/spec.md) for the old plan format.

<!-- BEGIN GENERATED INDEX -->

* [adopt-controls/plan.md](./adopt-controls/plan.md)
  Read me when: you adopt the pinned deterministic-controls library and the secret guard in compliance_poc, in advisory mode, with the existing Docker gate kept.
* [for-each-plan/plan.md](./for-each-plan/plan.md)
  Read me when: you want to see the format of a plan. (Template only. Copy this folder to start a plan.)
* [ralphify/plan.md](./ralphify/plan.md)
  Read me when: you are bringing this repository onto the template or reproducing its Docker test.

<!-- END GENERATED INDEX -->
