#!/usr/bin/env python3
"""Grade prreview eval runs against the assertions in evals.json.

Usage: grade.py <iteration-dir>

Each check is code, not judgment, so a rerun grades the same output the same
way. Content checks look for the seeded defect by its distinctive tokens, and
the evidence string quotes what matched so a human can confirm it in the viewer.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARSER = os.path.expanduser("~/.claude/skills/auditable-dev-protocol/scripts/adp-parser-lib.js")
REQUIRED = ["Severity", "Category", "Location", "Claim", "Evidence", "Failure scenario", "Suggested fix",
            "Confidence", "Confidence basis", "Verification", "Criterion", "Refs", "Created", "Status"]
MARKER = re.compile(r"^\s*⟦sc:[^⟧]*⟧\s*$")
LEDGER = re.compile(r"^- \*\*(PR-[A-Z]+-\d{3}) CLOSED (\d{4}-\d{2}-\d{2}) → (RESOLVED|REFUTED|ACCEPTED)\.\*\*", re.M)

PARSE_JS = r"""
const P=require(process.argv[1]); const md=require("fs").readFileSync(0,"utf8");
const secs=P.parseSections(md).secs; const out={sections:{}, findings:[]};
for(const s of secs){ out.sections[s.title]=P.parseDLFields(s.body).reduce((a,f)=>(a[f.label]=f.value,a),{});
  if(s.title==="Findings"){ for(const e of P.parseDLEntries(s.body.join("\n")).entries){
    const f=P.parseDLFields(P.dlSplitBody(e.lines).fieldLines);
    out.findings.push({head:e.head, fields:Object.fromEntries(f.map(x=>[x.label,x.value]))}); } } }
console.log(JSON.stringify(out));
"""


def parse_review(path):
    md = open(path, encoding="utf-8").read()
    r = subprocess.run(["node", "-e", PARSE_JS, PARSER], input=md, capture_output=True, text=True, check=True)
    data = json.loads(r.stdout)
    data["text"] = md
    return data


def terminal_lines(run):
    text = open(os.path.join(run, "outputs", "terminal.txt"), encoding="utf-8").read()
    lines = [l for l in text.strip().splitlines() if l.strip()]
    marker = bool(lines) and bool(MARKER.match(lines[-1]))
    if marker:
        lines = lines[:-1]
    return text, lines, marker


def reviews(run):
    return sorted(glob.glob(os.path.join(run, "repo", ".adp", "*", "pr-review-*.md")))


def rel(run, path):
    return os.path.relpath(path, os.path.join(run, "repo"))


def check_terminal(run, ctx):
    text, lines, marker = terminal_lines(run)
    files = reviews(run)
    new = [rel(run, f) for f in files if not f.endswith("-r1.md") or ctx.get("round", 1) == 1]
    ok = len(lines) == 2 and len(lines[0]) <= 250 and any(lines[1].strip().strip("`") == p for p in new)
    note = " A trailing session marker line was ignored." if marker else ""
    return ok, f"{len(lines)} line(s); first line {len(lines[0]) if lines else 0} chars; last line {lines[-1][:120] if lines else ''!r}.{note}"


def find(data, pred):
    return [f for f in data["findings"] if pred(f)]


def summarize(fs):
    return "; ".join(f"{f['head'][:70]} [{f['fields'].get('Severity','?')}]" for f in fs) or "none"


def grade_branch_single_task(run):
    res = {}
    files = reviews(run)
    pat = re.compile(r"\.adp/LGR-01-page-window/pr-review-local-\d{8}-r1\.md$")
    res["file-path"] = (len(files) == 1 and bool(pat.search(files[0])), f"review files: {[rel(run, f) for f in files]}")
    res["terminal-two-lines"] = check_terminal(run, {"round": 1})
    if not files:
        for k in ("card-grammar", "target-block", "finds-off-by-one", "finds-adp-02", "finds-adp-06", "verdict", "tests-recorded"):
            res[k] = (False, "no review file")
    else:
        d = parse_review(files[0])
        bad = [(f["head"][:40], [r for r in REQUIRED if r not in f["fields"]]) for f in d["findings"]]
        heads_ok = all(re.match(r"^\[PR-(COR|SEC|CON|TST|PERF|OPS|MNT|ADP)-\d{3}\] \S", f["head"]) for f in d["findings"])
        res["card-grammar"] = (bool(d["findings"]) and heads_ok and all(not m for _, m in bad),
                               f"{len(d['findings'])} findings; headings ok={heads_ok}; missing fields={[b for b in bad if b[1]]}")
        t = d["sections"].get("Review Target", {})
        ok = (t.get("Mode") == "LOCAL" and t.get("Task") == "LGR-01-page-window" and t.get("Round") == "1"
              and t.get("Task resolution", "").startswith("BRANCH NAME"))
        res["target-block"] = (ok, json.dumps({k: t.get(k) for k in ("Mode", "Task", "Round", "Task resolution")})[:300])
        fs = find(d, lambda f: f["fields"].get("Severity") == "must" and "ledger.py" in f["fields"].get("Location", "")
                  and re.search(r"size \+ 1|\+ 1|one extra|extra item|size\+1|4 items|four items", json.dumps(f["fields"]), re.I))
        res["finds-off-by-one"] = (bool(fs), summarize(fs))
        fs = find(d, lambda f: f["fields"].get("Category", "").startswith("ADP") and "ADP-02" in f["fields"].get("Criterion", ""))
        res["finds-adp-02"] = (bool(fs), summarize(fs))
        fs = find(d, lambda f: f["fields"].get("Category", "").startswith("ADP") and "ADP-06" in f["fields"].get("Criterion", "")
                  and "DL-002" in json.dumps(f["fields"]))
        res["finds-adp-06"] = (bool(fs), summarize(fs))
        v = d["sections"].get("Review Verdict", {})
        counts = {s: sum(1 for f in d["findings"] if f["fields"].get("Severity") == s) for s in ("must", "should", "question", "nit")}
        want = "must {must} / should {should} / question {question} / nit {nit}".format(**counts)
        res["verdict"] = (v.get("Verdict") == "REQUEST_CHANGES" and v.get("Counts") == want,
                          f"Verdict={v.get('Verdict')!r}; Counts={v.get('Counts')!r}; computed {want!r}")
        m = re.search(r"^\| Tests \| (.*)$", d["text"], re.M)
        res["tests-recorded"] = (bool(m and re.search(r"\d+ pass", m.group(1))), m.group(1)[:200] if m else "no Tests row")
    log = open(os.path.join(run, "repo", ".adp/LGR-01-page-window/audit-log.md"), encoding="utf-8").read()
    secs = re.findall(r"^## .*$", log, re.M)
    last = log[log.rfind("\n## "):]
    ok = secs[-1].startswith("## Review findings — local round 1 (") and "pr-review-local-" in last
    res["pointer"] = (ok, f"last H2: {secs[-1]!r}")
    res["no-code-edits"] = no_code_edits(run)
    return res


def no_code_edits(run):
    r = subprocess.run(["git", "status", "--porcelain"], cwd=os.path.join(run, "repo"), capture_output=True, text=True)
    # .lens/ is the lens MCP server's index, written by tooling, not by the review.
    changed = [l[3:] for l in r.stdout.splitlines() if not l[3:].startswith((".adp/", ".lens/"))]
    return (not changed, f"changed outside .adp/: {changed}")


def grade_multi_task_base(run):
    res = {}
    files = reviews(run)
    in_base = [f for f in files if "/LGR-02-csv-export/" in f]
    in_other = [f for f in files if "/LGR-03-csv-escape/" in f]
    res["base-task-file"] = (len(in_base) == 1 and not in_other, f"review files: {[rel(run, f) for f in files]}")
    if in_base:
        d = parse_review(in_base[0])
        t = d["sections"].get("Review Target", {})
        res["tasks-on-branch"] = ("LGR-03-csv-escape" in t.get("Tasks on branch", ""), f"Tasks on branch={t.get('Tasks on branch')!r}")
        res["resolution-basis"] = (t.get("Task resolution", "").startswith("BASE TASK"), f"Task resolution={t.get('Task resolution', '')[:160]!r}")
        fs = find(d, lambda f: re.search(r'double quote|quote character|quotes? (is|are) not (escaped|doubled)|""|embedded quote|contains a quote|holds a quote|quote',
                                         f["fields"].get("Claim", "") + f["fields"].get("Failure scenario", ""), re.I))
        res["finds-quote-escape"] = (bool(fs), summarize(fs))
    else:
        for k in ("tasks-on-branch", "resolution-basis", "finds-quote-escape"):
            res[k] = (False, "no review file in the base task")
    logs = {t: open(os.path.join(run, "repo", f".adp/{t}/audit-log.md"), encoding="utf-8").read()
            for t in ("LGR-02-csv-export", "LGR-03-csv-escape")}
    ok = "## Review findings — " in logs["LGR-02-csv-export"] and "## Review findings — " not in logs["LGR-03-csv-escape"]
    res["pointer-base-only"] = (ok, f"LGR-02 pointer={'## Review findings — ' in logs['LGR-02-csv-export']}; LGR-03 pointer={'## Review findings — ' in logs['LGR-03-csv-escape']}")
    res["terminal-two-lines"] = check_terminal(run, {"round": 1})
    return res


def grade_re_review(run):
    res = {}
    task = os.path.join(run, "repo", ".adp", "LGR-04-balance")
    r2 = [f for f in glob.glob(os.path.join(task, "pr-review-*-r2.md"))]
    if not r2:
        for k in ("round-2-file", "ledger-resolved", "id-continuity", "finds-overdraft", "closed-field"):
            res[k] = (False, f"no r2 file; files: {os.listdir(task)}")
    else:
        d = parse_review(r2[0])
        t = d["sections"].get("Review Target", {})
        res["round-2-file"] = (bool(re.search(r"pr-review-local-\d{8}-r2\.md$", r2[0])) and t.get("Round") == "2"
                               and "pr-review-local-20261010-r1.md" in t.get("Previous round", ""),
                               f"{os.path.basename(r2[0])}; Round={t.get('Round')!r}; Previous round={t.get('Previous round')!r}")
        lines = [m for m in LEDGER.finditer(d["text"]) if m.group(1) == "PR-COR-001"]
        res["ledger-resolved"] = (any(m.group(3) == "RESOLVED" for m in lines), f"ledger lines: {[m.group(0) for m in lines] or 'none'}")
        heads = [f["head"] for f in d["findings"]]
        res["id-continuity"] = (any(h.startswith("[PR-COR-002]") for h in heads) and not any(h.startswith("[PR-COR-001]") for h in heads),
                                f"headings: {heads}")
        fs = find(d, lambda f: "overdraft" in json.dumps(f["fields"]).lower() and re.search(r"-limit|negat|sign", json.dumps(f["fields"]), re.I))
        res["finds-overdraft"] = (bool(fs), summarize(fs))
        v = d["sections"].get("Review Verdict", {})
        res["closed-field"] = ("PR-COR-001" in v.get("Closed", ""), f"Closed={v.get('Closed')!r}")
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", ".adp/LGR-04-balance/pr-review-local-20261010-r1.md"],
                       cwd=os.path.join(run, "repo"))
    res["r1-immutable"] = (r.returncode == 0, "r1 unchanged against the fixture commit" if r.returncode == 0 else "r1 differs from the fixture commit")
    res["terminal-two-lines"] = check_terminal(run, {"round": 2})
    return res


def grade_ambiguous(run):
    res = {}
    files = reviews(run)
    res["no-file"] = (not files, f"review files: {[rel(run, f) for f in files]}")
    r = subprocess.run(["git", "status", "--porcelain", "--", ".adp"], cwd=os.path.join(run, "repo"), capture_output=True, text=True)
    res["logs-untouched"] = (not r.stdout.strip(), f".adp changes: {r.stdout.strip() or 'none'}")
    text, lines, _ = terminal_lines(run)
    # A reply that reviews anyway is not asking, even when it mentions both tasks.
    reviewed = bool(re.search(r"^## (Critical|High|Medium)|\[PR-[A-Z]+-\d{3}\]", text, re.M))
    ok = bool(lines) and lines[-1].rstrip().endswith("?") and "LGR-05" in text and "LGR-06" in text and not reviewed
    res["asks"] = (ok, f"last line: {lines[-1][:160] if lines else ''!r}; review content present={reviewed}")
    # The cause matters: "no task covers this" needs ADP to open one, "several could" needs a pick.
    no_task = re.search(r"\bno (\w+ ){0,2}tasks? (\w+ )?(covers|owns|exists for|matches)|not covered by any (\w+ )?task|no ADP task", text, re.I)
    recommends = re.search(r"auditable-dev-protocol", text)
    res["no-task-cause"] = (bool(no_task and recommends), f"no-task statement={no_task.group(0) if no_task else None!r}; names auditable-dev-protocol={bool(recommends)}")
    return res


def grade_untracked_adp(run):
    res = {}
    files = reviews(run)
    good = [f for f in files if "/20261002-LGR-07-cents/" in f]
    res["log-ref-file"] = (len(good) == 1 and len(files) == 1, f"review files: {[rel(run, f) for f in files]}")
    if good:
        d = parse_review(good[0])
        t = d["sections"].get("Review Target", {})
        res["record-source"] = (t.get("Record source", "").startswith("WORKING TREE"), f"Record source={t.get('Record source')!r}")
        res["resolution-basis"] = (t.get("Task resolution", "").startswith("LOG REFERENCE"), f"Task resolution={t.get('Task resolution', '')[:160]!r}")
        fs = find(d, lambda f: "to_cents" in json.dumps(f["fields"]) and re.search(r"truncat|\b28\b|floor|round", json.dumps(f["fields"]), re.I))
        res["finds-truncation"] = (bool(fs), summarize(fs))
    else:
        for k in ("record-source", "resolution-basis", "finds-truncation"):
            res[k] = (False, "no review file in the LGR-07 task")
    log = open(os.path.join(run, "repo", ".adp/20261002-LGR-07-cents/audit-log.md"), encoding="utf-8").read()
    secs = re.findall(r"^## .*$", log, re.M)
    res["pointer"] = (secs[-1].startswith("## Review findings — local round 1 ("), f"last H2: {secs[-1]!r}")
    res["terminal-two-lines"] = check_terminal(run, {"round": 1})
    return res


def grade_response_round(run):
    res = {}
    task = os.path.join(run, "repo", ".adp", "LGR-09-fees")
    r2 = glob.glob(os.path.join(task, "pr-review-*-r2.md"))
    keys = ("round-2-file", "responses-verbatim", "question-refuted", "should-carried", "needs-developer",
            "human-accepted", "verdict-comment", "summary-tail")
    if not r2:
        for k in keys:
            res[k] = (False, f"no r2 file; files: {os.listdir(task)}")
    else:
        d = parse_review(r2[0])
        t = d["sections"].get("Review Target", {})
        res["round-2-file"] = (bool(re.search(r"pr-review-local-\d{8}-r2\.md$", r2[0])) and t.get("Round") == "2"
                               and "pr-review-local-20261012-r1.md" in t.get("Previous round", ""),
                               f"{os.path.basename(r2[0])}; Round={t.get('Round')!r}; Previous round={t.get('Previous round')!r}")
        m = re.search(r"^## Developer Responses\n(.*?)(?=^## |\Z)", d["text"], re.M | re.S)
        rows = [l for l in (m.group(1) if m else "").splitlines() if l.startswith("|")]
        cor = [l for l in rows if "PR-COR-001" in l and "banker's rounding" in l]
        con = [l for l in rows if "PR-CON-001" in l and "never a percent" in l]
        res["responses-verbatim"] = (bool(cor and con), f"section {'found' if m else 'missing'}; rows: {[l[:90] for l in rows]}")
        lines = list(LEDGER.finditer(d["text"]))
        by = lambda i: [x for x in lines if x.group(1) == i]
        res["question-refuted"] = (any(x.group(3) == "REFUTED" for x in by("PR-CON-001")), f"PR-CON-001 lines: {[x.group(0) for x in by('PR-CON-001')] or 'none'}")
        v = d["sections"].get("Review Verdict", {})
        res["should-carried"] = (not by("PR-COR-001") and "PR-COR-001" in v.get("Carried open", ""),
                                 f"PR-COR-001 lines: {[x.group(0) for x in by('PR-COR-001')] or 'none'}; Carried open={v.get('Carried open')!r}")
        res["needs-developer"] = ("PR-COR-001" in v.get("Needs developer", ""), f"Needs developer={v.get('Needs developer')!r}")
        acc = [x for x in by("PR-TST-001") if x.group(3) == "ACCEPTED"]
        acc_line = d["text"][acc[0].start():].splitlines()[0] if acc else ""
        res["human-accepted"] = (bool(acc) and "Dana Reyes" in acc_line and "PR-TST-001" not in v.get("Carried open", ""),
                                 f"line: {acc_line[:120] or 'none'}; Carried open={v.get('Carried open')!r}")
        # OPEN after the round: the r2 file's new findings plus the carried ids, whose severity is in r1.
        sev = {f["head"][1:].split("]")[0]: f["fields"].get("Severity") for f in parse_review(os.path.join(task, "pr-review-local-20261012-r1.md"))["findings"]}
        sev.update({f["head"][1:].split("]")[0]: f["fields"].get("Severity") for f in d["findings"]})
        open_ids = [f["head"][1:].split("]")[0] for f in d["findings"]] + re.findall(r"PR-[A-Z]+-\d{3}", v.get("Carried open", ""))
        counts = {k: sum(1 for i in open_ids if sev.get(i) == k) for k in ("must", "should", "question", "nit")}
        want = "must {must} / should {should} / question {question} / nit {nit}".format(**counts)
        res["verdict-comment"] = (v.get("Verdict") == "COMMENT" and v.get("Counts", "").startswith(want),
                                  f"Verdict={v.get('Verdict')!r}; Counts={v.get('Counts')!r}; computed {want!r}")
        _, tl, _ = terminal_lines(run)
        first = tl[0] if tl else ""
        res["summary-tail"] = (bool(re.search(r"Needs developer: PR-COR-001\.\s*$", first)) and len(first) <= 250,
                               f"{len(first)} chars: {first[-80:]!r}")
    bad = []
    for f in glob.glob(os.path.join(run, "repo", ".adp", "**", "*.md"), recursive=True):
        for x in LEDGER.finditer(open(f, encoding="utf-8").read()):
            if x.group(3) == "ACCEPTED" and x.group(1) in ("PR-COR-001", "PR-CON-001"):
                bad.append(f"{rel(run, f)}: {x.group(0)}")
    res["no-agent-accept"] = (not bad, f"agent ACCEPTED lines: {bad or 'none'}")
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", ".adp/LGR-09-fees/pr-review-local-20261012-r1.md"],
                       cwd=os.path.join(run, "repo"))
    res["r1-immutable"] = (r.returncode == 0, "r1 unchanged against the fixture commit" if r.returncode == 0 else "r1 differs from the fixture commit")
    res["no-code-edits"] = no_code_edits(run)
    res["terminal-two-lines"] = check_terminal(run, {"round": 2})
    return res


def grade_refute_round(run):
    res = {}
    task = os.path.join(run, "repo", ".adp", "LGR-11-clamp")
    r2 = glob.glob(os.path.join(task, "pr-review-*-r2.md"))
    keys = ("round-2-file", "responses-verbatim", "should-refuted-verified", "question-carried",
            "nameless-not-accepted", "verdict-comment", "summary-tail")
    if not r2:
        for k in keys:
            res[k] = (False, f"no r2 file; files: {os.listdir(task)}")
    else:
        d = parse_review(r2[0])
        t = d["sections"].get("Review Target", {})
        res["round-2-file"] = (bool(re.search(r"pr-review-local-\d{8}-r2\.md$", r2[0])) and t.get("Round") == "2"
                               and "pr-review-local-20261012-r1.md" in t.get("Previous round", ""),
                               f"{os.path.basename(r2[0])}; Round={t.get('Round')!r}; Previous round={t.get('Previous round')!r}")
        m = re.search(r"^## Developer Responses\n(.*?)(?=^## |\Z)", d["text"], re.M | re.S)
        rows = [l for l in (m.group(1) if m else "").splitlines() if l.startswith("|")]
        cor = [l for l in rows if "PR-COR-001" in l and "bounds the low side" in l]
        con = [l for l in rows if "PR-CON-001" in l and "billing team" in l]
        res["responses-verbatim"] = (bool(cor and con), f"section {'found' if m else 'missing'}; rows: {[l[:90] for l in rows]}")
        lines = list(LEDGER.finditer(d["text"]))
        by = lambda i: [x for x in lines if x.group(1) == i]
        full = lambda x: d["text"][x.start():].splitlines()[0]
        # The quoted RESPONSE holds no command, so a command or a line read in the note is the reviewer's own check.
        ref = [full(x) for x in by("PR-COR-001") if x.group(3) == "REFUTED"]
        ok = any(re.search(r"python3|grep|src/ledger\.py:\d+", l) for l in ref)
        res["should-refuted-verified"] = (ok, f"PR-COR-001 REFUTED lines: {[l[:200] for l in ref] or 'none'}")
        v = d["sections"].get("Review Verdict", {})
        carried, nd = v.get("Carried open", ""), v.get("Needs developer", "")
        res["question-carried"] = (not by("PR-CON-001") and "PR-CON-001" in carried and "PR-CON-001" in nd,
                                   f"PR-CON-001 lines: {[x.group(0) for x in by('PR-CON-001')] or 'none'}; Carried open={carried!r}; Needs developer={nd!r}")
        acc = [x.group(0) for x in by("PR-TST-001") if x.group(3) == "ACCEPTED"]
        res["nameless-not-accepted"] = (not acc and "PR-TST-001" in carried and "PR-TST-001" in nd,
                                        f"PR-TST-001 ACCEPTED lines: {acc or 'none'}; Carried open={carried!r}; Needs developer={nd!r}")
        sev = {f["head"][1:].split("]")[0]: f["fields"].get("Severity") for f in parse_review(os.path.join(task, "pr-review-local-20261012-r1.md"))["findings"]}
        sev.update({f["head"][1:].split("]")[0]: f["fields"].get("Severity") for f in d["findings"]})
        open_ids = [f["head"][1:].split("]")[0] for f in d["findings"]] + re.findall(r"PR-[A-Z]+-\d{3}", carried)
        counts = {k: sum(1 for i in open_ids if sev.get(i) == k) for k in ("must", "should", "question", "nit")}
        want = "must {must} / should {should} / question {question} / nit {nit}".format(**counts)
        res["verdict-comment"] = (v.get("Verdict") == "COMMENT" and v.get("Counts", "").startswith(want),
                                  f"Verdict={v.get('Verdict')!r}; Counts={v.get('Counts')!r}; computed {want!r}")
        _, tl, _ = terminal_lines(run)
        first = tl[0] if tl else ""
        tail = re.search(r"Needs developer: (.*?)\.\s*$", first)
        ids = set(re.findall(r"PR-[A-Z]+-\d{3}", tail.group(1))) if tail else set()
        res["summary-tail"] = ({"PR-CON-001", "PR-TST-001"} <= ids and len(first) <= 250, f"{len(first)} chars: {first[-90:]!r}")
    acc = []
    for f in glob.glob(os.path.join(run, "repo", ".adp", "**", "*.md"), recursive=True):
        acc += [f"{rel(run, f)}: {x.group(0)}" for x in LEDGER.finditer(open(f, encoding="utf-8").read()) if x.group(3) == "ACCEPTED"]
    res["no-agent-accept"] = (len(acc) == 1 and acc[0].startswith(".adp/LGR-11-clamp/audit-log.md"), f"ACCEPTED lines: {acc or 'none'}")
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", ".adp/LGR-11-clamp/pr-review-local-20261012-r1.md"],
                       cwd=os.path.join(run, "repo"))
    res["r1-immutable"] = (r.returncode == 0, "r1 unchanged against the fixture commit" if r.returncode == 0 else "r1 differs from the fixture commit")
    res["no-code-edits"] = no_code_edits(run)
    res["terminal-two-lines"] = check_terminal(run, {"round": 2})
    return res


def grade_response_round_1(run):
    res = {}
    files = reviews(run)
    pat = re.compile(r"\.adp/LGR-01-page-window/pr-review-local-\d{8}-r1\.md$")
    res["file-path"] = (len(files) == 1 and bool(pat.search(files[0])), f"review files: {[rel(run, f) for f in files]}")
    if not files:
        for k in ("finds-off-by-one", "response-in-notes", "not-applied", "verdict-request-changes"):
            res[k] = (False, "no review file")
    else:
        d = parse_review(files[0])
        fs = find(d, lambda f: f["fields"].get("Severity") == "must" and "ledger.py" in f["fields"].get("Location", "")
                  and re.search(r"size \+ 1|\+ 1|one extra|extra item|size\+1|4 items|four items", json.dumps(f["fields"]), re.I))
        res["finds-off-by-one"] = (bool(fs), summarize(fs))
        m = re.search(r"^## Notes\n(.*?)(?=^## |\Z)", d["text"], re.M | re.S)
        notes = m.group(1) if m else ""
        res["response-in-notes"] = ("PR-COR-001" in notes and "page is correct" in notes, f"Notes {'found' if m else 'missing'}: {notes.strip()[:200]!r}")
        led = [x.group(0) for x in LEDGER.finditer(d["text"])]
        dr = bool(re.search(r"^## Developer Responses", d["text"], re.M))
        res["not-applied"] = (not dr and not led, f"Developer Responses section={dr}; ledger lines: {led or 'none'}")
        v = d["sections"].get("Review Verdict", {})
        res["verdict-request-changes"] = (v.get("Verdict") == "REQUEST_CHANGES", f"Verdict={v.get('Verdict')!r}")
    res["no-code-edits"] = no_code_edits(run)
    res["terminal-two-lines"] = check_terminal(run, {"round": 1})
    return res


GRADERS = {"branch-single-task": grade_branch_single_task, "multi-task-base": grade_multi_task_base,
           "re-review-round-2": grade_re_review, "ambiguous-placement": grade_ambiguous,
           "untracked-adp": grade_untracked_adp, "response-round-2": grade_response_round,
           "response-refute-round-2": grade_refute_round, "response-round-1": grade_response_round_1}


def main(iteration):
    evals = {e["name"]: e for e in json.load(open(os.path.join(HERE, "evals.json")))["evals"]}
    for name, ev in evals.items():
        edir = os.path.join(iteration, f"eval-{name}")
        if not os.path.isdir(edir):
            continue  # a CASES-filtered run skipped this eval
        json.dump({"eval_id": ev["id"], "eval_name": name, "prompt": ev["prompt"], "assertions": ev["assertions"]},
                  open(os.path.join(edir, "eval_metadata.json"), "w"), indent=2)
        for config in sorted(os.listdir(edir)):
            cdir = os.path.join(edir, config)
            if not os.path.isdir(cdir):
                continue
            run = os.path.join(cdir, "run-1")
            if not os.path.isdir(run):
                os.makedirs(run)
                for item in ("outputs", "repo", "timing.json"):
                    if os.path.exists(os.path.join(cdir, item)):
                        shutil.move(os.path.join(cdir, item), os.path.join(run, item))
            results = GRADERS[name](run)
            exps = [{"text": a["text"], "passed": bool(results[a["id"]][0]), "evidence": results[a["id"]][1]} for a in ev["assertions"]]
            passed = sum(e["passed"] for e in exps)
            # No timing key here: the aggregator reads tokens from timing.json only when grading.json has none.
            json.dump({"expectations": exps,
                       "summary": {"passed": passed, "failed": len(exps) - passed, "total": len(exps),
                                   "pass_rate": round(passed / len(exps), 2)}},
                      open(os.path.join(run, "grading.json"), "w"), indent=2, ensure_ascii=False)
            print(f"{name:22} {config:11} {passed}/{len(exps)}")


if __name__ == "__main__":
    main(os.path.realpath(sys.argv[1]))
