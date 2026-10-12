# Change Control (YBS, HPML, TRID and every other evaluator domain)

Every deterministic evaluator pack is a decision-support pilot and is intentionally review-gated.
Builder output (`python -m builders.build run`) is a proposal: it lands as `draft_engineering_review`
and goes through the same review as hand-written changes. The builders' `needs_human_review` list
is part of the PR description.

Changes to any of the following require an engineering code-owner review before
merge:

- regulatory source snapshots and their manifest provenance (`compliance_mcp/<domain>/pack/sources/`, `builders/sources.yaml`, `builders/sources.lock.yaml`);
- institution policy, thresholds, evaluator rules, or tool contracts;
- scenario/regression fixture inputs or expected outcomes.

The repository `.github/CODEOWNERS` identifies these paths. Repository
administrators must enable **Require a pull request before merging** and
**Require review from Code Owners** for the protected target branch in GitHub
branch-protection settings; CODEOWNERS alone only declares ownership and does
not block direct pushes. PR authors must explain the source/policy basis and
update relevant hash, schema, contract, and regression tests in the same PR.
