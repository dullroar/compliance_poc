#!/usr/bin/env bash
# Build and test a source snapshot of this Git worktree.
# Run me when: you need to run the offline compliance and context checks in Docker.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
cd -- "$(git rev-parse --show-toplevel)"

run_dir=$(mktemp -d "${TMPDIR:-/tmp}/compliance-poc-test.XXXXXXXXXX")
image="compliance-poc-test:${run_dir##*.}"
container="compliance-poc-test-${run_dir##*.}"
cleanup() {
    docker image rm "$image" >/dev/null 2>&1 || true
    rmdir -- "$run_dir"
}
trap cleanup EXIT

# Use current worktree contents without copying Git metadata or local files.
git ls-files --cached --deduplicate -z |
    while IFS= read -r -d '' path; do
        if [[ -f "$path" || -L "$path" ]]; then
            printf '%s\0' "$path"
        fi
    done |
    tar --create --file=- --no-recursion --null --files-from=- |
    docker build --tag "$image" -

docker run --rm --name "$container" --network none --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,mode=1777 "$image" bash -euc '
        output=$(mktemp -d /tmp/compliance-poc-output.XXXXXXXXXX)
        export TMPDIR="$output"
        export COMPLIANCE_LOG_DIR="$output/logs"
        export RUN_LIVE_ANTHROPIC_PARALLEL=0 RUN_LIVE_ANTHROPIC_PARITY=0
        export RUN_LIVE_OPENAI_TESTS=0 RUN_LIVE_OPENAI_PARALLEL=0 RUN_LIVE_OPENAI_PARITY=0
        export RUN_LIVE_APOR_TESTS=0 RUN_LIVE_EVERY_REGIME=0 RUN_LIVE_OLLAMA_TESTS=0
        python3 scripts/check_context.py
        python3 -m unittest discover -s tests -v
    '
