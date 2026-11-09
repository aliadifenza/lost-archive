#!/usr/bin/env bash
# Offline verification of the Lost Archive V1.3 repository. No network, no API calls.
#   bash scripts/verify.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
step() { printf '\n== %s\n' "$1"; }

step "1. File checksums (CHECKSUMS.sha256)"
sha256sum --quiet -c CHECKSUMS.sha256 && echo "all files match"

step "2. Frozen prompts"
echo "0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630  config/prompts/system_prompt.txt
3c2fcc1814b829a1df9722cdb35b031529cc47c2b7e47131b15df44c8353f848  config/prompts/repair_message.txt" | sha256sum -c

if git rev-parse --git-dir >/dev/null 2>&1 && git rev-parse -q --verify v1.3-expansion-ready >/dev/null; then
  step "3. Specs, prompts, config and simulator unchanged since the code the experiment ran on (v1.3-expansion-ready)"
  CHANGED="$(git --no-optional-locks diff --name-only v1.3-expansion-ready HEAD -- spec config \
      lostarchive/engine.py lostarchive/world.py lostarchive/llm.py lostarchive/probe.py \
      lostarchive/metrics.py lostarchive/properties.py lostarchive/policies.py lostarchive/experiment.py \
      lostarchive/cost.py lostarchive/replay.py lostarchive/analyze.py)"
  if [ -n "$CHANGED" ]; then echo "CHANGED: $CHANGED"; exit 1; else echo "unchanged"; fi
else
  step "3. (skipped: no git history or tags; checksums in step 1 cover the files)"
fi

step "4. Unit tests"
python3 -m unittest discover -s tests 2>&1 | tail -3

step "5. Exact replay of every run and recomputed analysis"
python3 -m lostarchive.expansion_report --runs results/raw --out "$TMP/exp" | tail -5
cmp <(python3 -m json.tool --sort-keys "$TMP/exp/results.json") \
    <(python3 -m json.tool --sort-keys results/expansion/results.json) && echo "results.json reproduced"

step "6. Review packet and annotation layer"
python3 -m lostarchive.review_packet --runs results/raw --out "$TMP/rev" >/dev/null
for f in messages_for_review.csv s6_C1_episode_trace.md; do cmp "$TMP/rev/$f" "results/expansion/review/$f" && echo "$f reproduced"; done
python3 -m lostarchive.annotate_messages --runs results/raw --out "$TMP/ann.csv" >/dev/null
cmp "$TMP/ann.csv" results/expansion/review/message_annotations_claude.csv && echo "message_annotations_claude.csv reproduced"

printf '\nALL CHECKS PASSED\n'
