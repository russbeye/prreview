#!/usr/bin/env bash
# Runs every prreview eval case headless with `claude -p`, once per configuration,
# all in parallel. Each run gets its own fresh fixture repo, so runs cannot see
# each other's review files.
#
# Usage: run_evals.sh <iteration-dir> <config>=<skill-dir> [<config>=<skill-dir> ...]
# Example: run_evals.sh ../prreview-workspace/iteration-1 with_skill=. old_skill=../prreview-workspace/skill-snapshot
set -u
here="$(cd "$(dirname "$0")" && pwd)"
iter="$(realpath -m "$1")"; shift
cases=$(python3 -c "import json;print(' '.join(e['name'] for e in json.load(open('$here/evals.json'))['evals']))")
# CASES="a b" limits the run to those eval names.
cases="${CASES:-$cases}"

run_one() {
	local name="$1" config="$2" skill="$3"
	local dir="$iter/eval-$name/$config"
	local repo="$dir/repo" out="$dir/outputs"
	mkdir -p "$out"
	python3 "$here/fixtures/build_fixtures.py" "$name" "$repo" >/dev/null
	local user_prompt
	user_prompt=$(python3 -c "import json,sys;print(next(e['prompt'] for e in json.load(open('$here/evals.json'))['evals'] if e['name']=='$name'))")
	local prompt="Use the skill at $skill: read $skill/SKILL.md and follow it. Ignore any other installed skill named prreview.

$user_prompt"
	local start end
	start=$(date +%s%3N)
	(cd "$repo" && claude -p "$prompt" --output-format json --permission-mode bypassPermissions \
		--add-dir "$skill" >"$out/claude.json" 2>"$out/stderr.txt")
	end=$(date +%s%3N)
	python3 - "$out" "$start" "$end" <<'PY'
import json, sys
out, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
try:
    r = json.load(open(f"{out}/claude.json"))
except Exception:
    r = {}
open(f"{out}/terminal.txt", "w").write(r.get("result", ""))
u = r.get("usage", {}) or {}
tokens = sum(u.get(k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
ms = r.get("duration_ms", end - start)
json.dump({"total_tokens": tokens, "duration_ms": ms, "total_duration_seconds": round(ms / 1000, 1)},
          open(f"{out}/../timing.json", "w"), indent=2)
PY
	(cd "$repo" && { git status --porcelain; echo; git diff; } >"$out/git-changes.txt")
	[ -d "$repo/.adp" ] && cp -r "$repo/.adp" "$out/adp"
	echo "done $name $config"
}

for name in $cases; do
	for pair in "$@"; do
		run_one "$name" "${pair%%=*}" "$(realpath "${pair#*=}")" &
	done
done
wait
echo "all runs finished"
