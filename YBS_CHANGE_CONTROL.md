# YBS Change Control

The YBS pack is a decision-support pilot and is intentionally review-gated.

Changes to any of the following require an engineering code-owner review before
merge:

- regulatory source extracts and their manifest provenance;
- institution policy, thresholds, evaluator rules, or tool contracts;
- scenario/regression fixture inputs or expected outcomes.

The repository `.github/CODEOWNERS` identifies these paths. Repository
administrators must enable **Require a pull request before merging** and
**Require review from Code Owners** for the protected target branch in GitHub
branch-protection settings; CODEOWNERS alone only declares ownership and does
not block direct pushes. PR authors must explain the source/policy basis and
update relevant hash, schema, contract, and regression tests in the same PR.
