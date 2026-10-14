#!/usr/bin/env python3
"""Fix skill-creator's benchmark.json for this eval layout.

Usage: finalize_benchmark.py <iteration-dir> <model-id>

The aggregator orders configurations by directory name, so old_skill lands
before with_skill and the delta sign flips. It also hardcodes three runs per
configuration and leaves the model as a placeholder. We rewrite those fields
and leave every measured number as the aggregator computed it.
"""
import json
import os
import sys

iteration, model = sys.argv[1], sys.argv[2]
path = os.path.join(iteration, "benchmark.json")
b = json.load(open(path))
rs = b["run_summary"]
primary, baseline = rs["with_skill"], rs["old_skill"]
b["run_summary"] = {"with_skill": primary, "old_skill": baseline, "delta": {
    "pass_rate": f"{primary['pass_rate']['mean'] - baseline['pass_rate']['mean']:+.2f}",
    "time_seconds": f"{primary['time_seconds']['mean'] - baseline['time_seconds']['mean']:+.1f}",
    "tokens": f"{primary['tokens']['mean'] - baseline['tokens']['mean']:+.0f}"}}
runs = {(r["eval_id"], r["configuration"]) for r in b["runs"]}
b["metadata"]["runs_per_configuration"] = max(sum(1 for r in b["runs"] if (r["eval_id"], r["configuration"]) == k) for k in runs)
b["metadata"]["executor_model"] = model
b["metadata"]["skill_path"] = os.path.expanduser("~/.claude/skills/prreview")
b["runs"].sort(key=lambda r: (r["eval_id"], r["configuration"] != "with_skill", r["run_number"]))
json.dump(b, open(path, "w"), indent=2)
print(json.dumps(b["run_summary"]["delta"]), "runs/config:", b["metadata"]["runs_per_configuration"])
