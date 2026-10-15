# prreview

prreview is a Claude Code skill that reviews a pull request, or your branch before you open one.
Claude checks each finding before it reports it, gives the finding an id, and writes the whole
review to a file in your repository. Your terminal gets two lines.

prreview is a sister skill to the
[Auditable Development Protocol](https://github.com/russbeye/auditable-dev-protocol) (ADP). ADP
records how a change was built. prreview records how the change was judged, in the same task
folder.

## What you get

- Findings you can trust. Claude confirms each one with a grep, a file read, or a repro. A concern
  it cannot confirm becomes a question, never a blocker.
- Findings you can act on. Each one names the file and line, the evidence, a failure scenario, and
  the fix that would close it.
- A record that lasts. Each review round is a file. On a re-review, Claude closes or carries each
  earlier finding, so you see what changed between rounds.
- A test run. Claude finds your test command, runs it once on the reviewed commit, and records
  the counts. When it finds no command, it says so and lowers its confidence in the review.
- Your code stays as it is. prreview does not edit code and does not post to GitHub. It writes
  only the review file and a short pointer in the task's audit log.

## Install

You need Claude Code and `git`. To review a pull request by number, you also need the GitHub CLI
`gh`, logged in to your account.

1. Clone the skill into your Claude Code skills folder:

   ```bash
   git clone https://github.com/russbeye/prreview.git ~/.claude/skills/prreview
   ```

2. Start a new Claude Code session. The skill is ready.

To use prreview in one project only, clone it into `.claude/skills/prreview` inside that project
instead.

To update, run `git -C ~/.claude/skills/prreview pull`.

## Use it

Ask Claude in plain words, or use the slash command:

| You want to | Say | Or type |
|-------------|-----|---------|
| Review a pull request | "review PR 42" | `/prreview 42` |
| Review it again after new commits | "re-review PR 42" | `/prreview 42` |
| Review your branch before a PR exists | "review this branch" | `/prreview` |
| Answer a finding from the last round | "re-review PR 42. RESPONSE PR-CON-001: rate is a fraction." | `/prreview 42 RESPONSE PR-CON-001: rate is a fraction.` |

A PR URL works in place of the number. In branch mode, Claude compares your branch with the point
where it left the default branch.

Each review belongs to one ADP task. Claude finds the task from your branch name or from the task
folders your branch changes. When no task matches, or two tasks could own the review, Claude stops
and asks you. It never guesses and never creates a task for you.

### Answer a finding

When you disagree with a finding, or you know the fact a `question` asks for, answer it in the next
round. Start each answer with `RESPONSE` and the finding id. You can give several answers at once:

```
/prreview 42 RESPONSE PR-CON-001: rate is a fraction. billing.py:14 passes 0.01. RESPONSE PR-COR-002: the cache is per request, see app.py:30.
```

Claude records each answer word for word in the review file, then decides what it does:

- A `question` closes on your answer when the answer settles it.
- A `should` or `must` closes only when Claude checks your claim against the code and finds it
  true. Your word alone does not close it.
- An answer that asks Claude to accept a risk, or to leave a finding unfixed, closes nothing.
  Claude lists the finding under **Needs developer**.

### Accept a risk

Only you can accept a risk, and you do it in the audit log, not in an answer. Under the round's
`## Review findings` section in `.adp/<task>/audit-log.md`, add one line with your name:

```
- **PR-COR-001 CLOSED 2026-10-15 → ACCEPTED.** Dana Reyes accepted half-even rounding for fees.
```

The next round closes the finding. You do not need to commit the line first. A line without a
person's name closes nothing.

### Review in a loop

Claude can run review rounds until the change passes. Each round runs in a fresh headless session,
so one round cannot lean on the reasoning of the round before it.

A headless round cannot ask you for permission, so the command gives it what a review needs up
front:

```bash
claude -p "/prreview 42" --add-dir ~/.claude/skills/prreview --permission-mode acceptEdits --allowedTools "Read(~/.claude/skills/prreview/**)" "Bash(git:*)" "Bash(gh:*)" "Bash(ls:*)" "Bash(grep:*)" "Bash(find:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(<test command>:*)" "Bash(<runtime>:*)"
```

Replace `42` with your PR number. Replace `<test command>` with your test command, such as
`npm test`. Replace `<runtime>` with the program Claude uses to reproduce a bug, such as `python3`
or `node`. With these rules, Claude can run your tests and short scripts in your project without
asking, so use them only in a project you trust. Without them, the round stops and asks for
permission that a headless session cannot get.

Then paste this into Claude Code, with your filled-in command in place of `<command>`:

```
/goal Review the PR in rounds, at most 5. Run each round with this command: <command>
Read the verdict on line 1 of its output, and the Confidence field under Review Verdict in the
review file that line 2 names. Then:
- APPROVE with HIGH confidence: stop. The review passed.
- Line 1 ends with "Needs developer": stop and tell me which findings need me.
- REQUEST_CHANGES: fix the open findings, commit, and run the next round.
- COMMENT: fix the findings you agree with and commit. In the next round, add
  RESPONSE <PR-ID>: <your answer and its evidence> to the command's prompt for each other open
  finding.
- APPROVE below HIGH confidence: read the Confidence basis, fix what lowered it, and run the next
  round.
Never write a ledger line in the audit log. Only I accept a risk.
After round 5, stop and tell me where the review stands.
```

## Read the output

The terminal shows two lines:

```
REQUEST_CHANGES. 1 must, 2 should, 0 question, 1 nit. PR-SEC-003: token compare is not constant-time. Tests 212 pass, 0 fail.
.adp/ZUP-C1-ci-test-runner/pr-review-PR12-20261012-r2.md
```

The first line gives the verdict, the number of open findings at each severity, the most serious
finding, and the test result. When a finding needs your decision, the line ends with
`Needs developer:` and the finding ids. It is 250 characters or fewer. The second line is the path
to the review file.

### Verdict

| Verdict | When |
|---------|------|
| `REQUEST_CHANGES` | At least one `must` finding is open. |
| `COMMENT` | No `must` is open, and at least one `should` or `question` is open. |
| `APPROVE` | Only `nit` findings are open, or none. |

### Severity

| Severity | Meaning |
|----------|---------|
| `must` | A bug, a broken contract, a security issue, a data-loss risk, or a failing test. Fix it before you merge. |
| `should` | A real risk with evidence behind it, below a clear blocker. |
| `question` | The code supports a concern, and one fact or decision settles it. The finding names that fact. |
| `nit` | Optional cleanup. |

### Finding ids

An id looks like `PR-SEC-003`. The middle part is the category: `COR` correctness, `SEC`
security, `CON` contract, `TST` tests, `PERF` performance, `OPS` operations, `MNT`
maintainability, and `ADP` for a gap between the change and its ADP record. The number counts up
across every round in the task, so an id always points at one finding.

### The review file

Claude writes one file per round, named `pr-review-PR<n>-<date>-r<round>.md` for a pull request or
`pr-review-local-<date>-r<round>.md` for a branch. It holds these sections:

| Section | What it tells you |
|---------|-------------------|
| Review Target | The commits Claude judged, the task, and the round. |
| Inspected | What Claude read, and the test command with its pass, fail, and skip counts. |
| Findings | One card per finding: severity, location, claim, evidence, failure scenario, suggested fix, and confidence. |
| Quality Coverage | Each rule Claude checked the change against. |
| Developer Responses | Each answer you sent, word for word, and what it did. |
| Prior Findings | On a re-review, how each earlier finding closed. |
| Notes | Limits of the review, and concerns that did not become findings. |
| Review Verdict | The verdict, its confidence, the counts, the findings that need your decision, and the same summary the terminal printed. |

Each finding states its confidence as HIGH, MEDIUM, or LOW, and says where that confidence comes
from: evidence Claude saw, a convention in your code, or something you told it.

## Use it with ADP

prreview reads the task's ADP audit log before it reviews, so it judges the change against what
you planned as well as against the code. It checks, among other things:

- that the log holds every phase the change needs, such as the Test Adversary Document and the PR
  Summary
- that each mitigation in the Pre-Mortem Report still exists in the code
- that each real decision in the diff has a Decision Log entry
- that each LOW-confidence decision is listed for review
- that the code still does what the Decision Log says it does

A gap becomes an `ADP` finding with the entry id it refers to. When the review ends, Claude adds a
short section to the audit log that points at the review file. The ADP viewer then shows the
review with the rest of the task.

If your project has no `.adp/` folder, Claude says so, suggests that you start one with ADP, and
asks how you want to go on.

## Add your own rules

You can give prreview rules that only your repository has. Put them in
`.adp/pr-review-quality.yaml`:

```yaml
id: repository-code-quality
version: 1
review_dimensions:
  - id: correctness
    required: true
    pass: Changed behavior satisfies the requested outcome.
project_rules:
  - id: api-error-contract
    category: CON
    evidence: src/http/errors.ts, docs/api.md
    pass: API handlers return the standard error envelope.
```

Write each `pass` line as the state you accept. Claude checks the change against it and reports
each rule in Quality Coverage. See `references/quality-profile.md` for the full format.

You can also ask Claude to propose a profile for your repository. Claude reads your CI, tests, and
guidance files, shows you each rule with its evidence, and writes the file only after you agree.

## Evals

The `evals/` folder holds the test cases for the skill itself. They need the ADP skill and the
skill-creator skill. You do not need them to use prreview.

## License

GNU General Public License v3.0. See [LICENSE.md](LICENSE.md).
