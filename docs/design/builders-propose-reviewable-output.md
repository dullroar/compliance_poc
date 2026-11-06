---
gist: "Read when: changing builder agents, the source registry and lock file, snapshots, path guards, version bumps or rollback."
---

# Builders produce reviewable proposals

- Builders are agents with a deterministic harness: the registry of canonical sources and a lock file decide what is rebuilt; the harness owns snapshots, manifest provenance, path guards, version bumps, test runs and rollback. Builder output is always a reviewable proposal.
