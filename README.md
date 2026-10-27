# prreview

prreview is a Claude Code skill that reviews your pull requests. It can also review a branch
before you open a pull request. Claude checks every finding against your code before it reports
the finding. You get a short verdict in the terminal and a full review file in your repository.

prreview is a sister skill to the
[Auditable Development Protocol](https://github.com/russbeye/auditable-dev-protocol) (ADP). ADP
records how a change was built. prreview records how the change was judged, and it keeps that
record in the same task folder.

## What you get

- **Findings you can trust.** Claude confirms each finding with a search, a file read, or a small
  test script. If Claude cannot confirm a concern, the concern becomes a question, not a blocker.
- **Findings you can act on.** Each finding gives the file and line, the evidence, what goes wrong,
  and the fix that closes it.
- **A test run.** Claude finds your test command and runs it once on the commit it reviews. If
  there is none, the review says so, and its confidence goes down unless the change is docs only.
- **A record that lasts.** Each review round is a file in your repository. On a second round,
  Claude says which earlier findings closed and which stay open.
- **No surprise changes.** prreview does not edit your code and does not post to GitHub. It writes
  only the review file and a short pointer in the task's audit log.

## Quick start

Before you start, you need two things. The GitHub CLI, `gh`, must be signed in to your account,
because Claude reads the pull request with it. Your project must also have an ADP task in `.adp/`
that covers the change. Without a task, Claude stops and asks you how to continue, so start one
with [ADP](https://github.com/russbeye/auditable-dev-protocol) first.

1. Install the skill:

   ```bash
   git clone https://github.com/russbeye/prreview.git ~/.claude/skills/prreview
   ```

2. Start a new Claude Code session in your project.
3. Type the slash command with your pull request number:

   ```
   /prreview 42
   ```

4. Read the two lines that Claude prints:

   ```
   REQUEST_CHANGES. 1 must, 2 should, 0 question, 1 nit. PR-SEC-003: token compare is not constant-time. Tests 212 pass, 0 fail.
   .adp/ZUP-C1-ci-test-runner/pr-review-PR12-20261012-r2.md
   ```

   The first line is the verdict. The second line is the review file, which holds every finding
   in full.

5. Fix the findings, commit, push, and run `/prreview 42` again. A pull request review reads the
   head commit on GitHub, so it does not see a commit that you did not push. Repeat until the
   verdict is `APPROVE`.

## Install

You need Claude Code and `git`. To review a pull request by its number, you also need the GitHub
CLI, `gh`, signed in to your account.

- **For all your projects:** clone the skill into `~/.claude/skills/prreview`, as the quick start
  shows.
- **For one project only:** clone the skill into `.claude/skills/prreview` inside that project.

The skill is ready in the next Claude Code session you start. To update the skill, run
`git -C ~/.claude/skills/prreview pull`.

## Use it

Ask Claude in plain words, or type the slash command:

| You want to | Say | Or type |
|-------------|-----|---------|
| Review a pull request | "review PR 42" | `/prreview 42` |
| Review it again after new commits | "re-review PR 42" | `/prreview 42` |
| Review your branch before a pull request exists | "review this branch" | `/prreview` |
| Answer a finding from the last round | "re-review PR 42. RESPONSE PR-CON-001: rate is a fraction." | `/prreview 42 RESPONSE PR-CON-001: rate is a fraction.` |

You can give a pull request URL in place of the number. When you review a branch, Claude compares
your branch with the point where it left the default branch.

Each review belongs to one ADP task. Claude finds the task from your branch name, or from the task
folders that your branch changes. If no task matches, or if two tasks could own the review, Claude
stops and asks you. Claude never guesses a task and never creates one for you.

## Read a review

### The two terminal lines

The first line gives these facts, in this order:

1. The verdict.
2. The number of open findings at each severity.
3. The most serious finding.
4. The test result.

If a finding needs a decision from you, the first line ends with `Needs developer:` and the
finding ids. The first line is 250 characters or fewer. The second line is the path to the review
file.

If your own setup requires a line on every reply, for example a session marker, that line may
follow the two lines. It is not part of the report.

### Verdict

| Verdict | When you get it |
|---------|-----------------|
| `REQUEST_CHANGES` | At least one `must` finding is open. |
| `COMMENT` | No `must` finding is open, and at least one `should` or `question` is open. |
| `APPROVE` | Only `nit` findings are open, or no findings are open. |

### Severity

| Severity | What it means for you |
|----------|-----------------------|
| `must` | A bug, a broken contract, a security issue, a data-loss risk, or a failing test. Fix it before you merge. |
| `should` | A real risk that has evidence behind it, but is not a clear blocker. |
| `question` | The code supports a concern, and one fact or decision settles it. The finding names that fact. |
| `nit` | Optional cleanup. |

### Finding ids

A finding id looks like `PR-SEC-003`. The middle part is the category:

| Code | Category |
|------|----------|
| `COR` | Correctness |
| `SEC` | Security |
| `CON` | Contract |
| `TST` | Tests |
| `PERF` | Performance |
| `OPS` | Operations |
| `MNT` | Maintainability |
| `ADP` | A gap between the change and its ADP record |

The number counts up across every round in the task. So an id always points at one finding.

### The review file

Claude writes one file for each round. A pull request review is named
`pr-review-PR<n>-<date>-r<round>.md`. A branch review is named `pr-review-local-<date>-r<round>.md`.
The file has these sections:

| Section | What it tells you |
|---------|-------------------|
| Review Target | The commits that Claude judged, the task, and the round. |
| Inspected | What Claude read, and your test command with its pass, fail, and skip counts. |
| Findings | One card for each finding: severity, location, claim, evidence, failure scenario, suggested fix, and confidence. |
| Quality Coverage | Each rule that Claude checked the change against. |
| Developer Responses | Each answer you sent, word for word, and what the answer did. |
| Prior Findings | On a later round, how each earlier finding closed. |
| Notes | The limits of the review, and concerns that did not become findings. |
| Review Verdict | The verdict, its confidence, the counts, the findings that need your decision, and the same summary line that the terminal prints. |

Each finding gives its confidence as HIGH, MEDIUM, or LOW. It also says where that confidence
comes from: evidence that Claude saw, a convention in your code, or something that you told Claude.

## Answer a finding

Sometimes you disagree with a finding, or you know the fact that a `question` asks for. Give your
answer in the next round. Start each answer with `RESPONSE` and the finding id. You can send
several answers in one command:

```
/prreview 42 RESPONSE PR-CON-001: rate is a fraction. billing.py:14 passes 0.01. RESPONSE PR-COR-002: the cache is per request, see app.py:30.
```

Claude copies each answer word for word into the review file. Then the answer has one of these
results:

- A `question` closes when your answer settles it.
- A `should` or a `must` closes only when Claude checks your claim against the code and finds it
  true. Your word alone does not close it.
- An answer that asks Claude to accept a risk, or to leave a finding unfixed, closes nothing.
  Claude lists the finding under **Needs developer**.

## Accept a risk

Only you can accept a risk. You do it in the audit log, not in an answer. Find the round's
`## Review findings` section in `.adp/<task>/audit-log.md`. Under it, add one line with your name:

```
- **PR-COR-001 CLOSED 2026-10-15 → ACCEPTED.** Dana Reyes accepted half-even rounding for fees.
```

The next round closes the finding. You do not need to commit the line first. A line without a
person's name closes nothing.

## Review in a loop

Claude can run review rounds for you until the change passes. Claude fixes the findings between
rounds, and each round reviews the result. Each round runs in a new headless session, so a round
cannot lean on the reasoning of the round before it.

### Step 1: pick the round command

A headless session cannot ask you for permission. So the round command must give the review
everything it needs before it starts. Pick one of these two commands.

**The scoped command.** This command allows only the tools that a review uses. Use it when your
project is outside `~/.claude`:

```bash
claude -p "/prreview 42" --add-dir ~/.claude/skills/prreview --permission-mode acceptEdits --allowedTools "Read(~/.claude/skills/prreview/**)" "Bash(git:*)" "Bash(gh:*)" "Bash(ls:*)" "Bash(grep:*)" "Bash(find:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(<test command>:*)" "Bash(<runtime>:*)"
```

Make these replacements:

- Replace `42` with your pull request number.
- Replace `<test command>` with your test command, such as `npm test`.
- Replace `<runtime>` with the program that Claude uses to reproduce a bug, such as `python3` or
  `node`.

These rules let Claude run your tests and short scripts without asking. Use them only in a project
that you trust.

**The bypass command.** This command skips every permission check. Use it when your project is
inside `~/.claude`, such as a skill that you develop in `~/.claude/skills/`:

```bash
claude -p "/prreview 42" --permission-mode bypassPermissions
```

Replace `42` with your pull request number. Claude Code treats every file under `~/.claude` as
sensitive. It asks before it edits such a file, even when the scoped command allows edits. So the
scoped command stops when it writes the review file there, and only the bypass command gets
through.

Warning: use the bypass command only in a project that you trust. With it, Claude can run any
command and edit any file without asking.

### Step 2: start the loop

Paste this into Claude Code. Put your round command in place of `<command>`:

```
/goal Review the PR in rounds, at most 5. Run each round with this command: <command>
Read the verdict on line 1 of its output, and the Confidence field under Review Verdict in the
review file that line 2 names. Then:
- APPROVE with HIGH confidence: stop. The review passed.
- Line 1 ends with "Needs developer": stop and tell me which findings need me.
- REQUEST_CHANGES: fix the open findings, commit, push, and run the next round.
- COMMENT: fix the findings you agree with, commit, and push. In the next round, add
  RESPONSE <PR-ID>: <your answer and its evidence> to the command's prompt for each other open
  finding.
- APPROVE below HIGH confidence, and the only reason is that the tests did not run: stop. Tell me
  the reason from the Tests row under Inspected. A round whose tests did not run cannot reach
  HIGH, unless the change is docs only.
- APPROVE below HIGH confidence for any other reason: read the Confidence basis, fix what lowered
  it, commit, push, and run the next round.
Never write a ledger line in the audit log. Only I accept a risk.
After round 5, stop and tell me where the review stands.
```

The loop stops in one of four ways:

- The review passes with `APPROVE` at HIGH confidence.
- The review passes with `APPROVE` below HIGH confidence only because the tests did not run.
  Claude tells you why they did not run.
- A finding needs your decision. Claude names the finding ids.
- Five rounds finish. Claude tells you where the review stands.

## Use it with ADP

prreview reads the task's ADP audit log before it reviews. So Claude judges the change against
your plan as well as against the code. Claude checks these points, among others:

- The log holds every phase that the change needs, such as the Test Adversary Document and the PR
  Summary.
- Each mitigation in the Pre-Mortem Report still exists in the code.
- Each real decision in the diff has a Decision Log entry.
- Each LOW-confidence decision is on the list for review.
- The code still does what the Decision Log says it does.

A gap becomes an `ADP` finding that names the entry it refers to. When the review ends, Claude adds
a short section to the audit log that points at the review file. The ADP viewer then shows the
review with the rest of the task.

If your project has no `.adp/` folder, Claude tells you. Claude suggests that you start one with
ADP, and asks how you want to continue.

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

Write each `pass` line as the state that you accept. Claude checks the change against each rule
and reports the result in Quality Coverage. For the full format, see
`references/quality-profile.md`.

You can also ask Claude to propose rules for your repository. Claude reads your CI, your tests, and
your guidance files. Then Claude shows you each rule with its evidence. Claude writes the file only
after you agree.

## Evals

The `evals/` folder holds the test cases for the skill itself. They need the ADP skill and the
skill-creator skill. You do not need them to use prreview.

If your setup ends every reply with a session marker, set `PRREVIEW_MARKERS` before you run
`evals/grade.py`. Put one regular expression on each line. The grader ignores the last line of a
reply only when one pattern matches that whole line. When the variable is unset or empty, the
grader ignores no line, and a marker line fails the terminal checks. For example:

```bash
export PRREVIEW_MARKERS='⟦sc:[^⟧]*⟧
⟦lc:[^⟧]*⟧'
```

Run `python3 evals/test_grade.py` to test the grader's marker handling. The test needs no eval
runs and does not read `PRREVIEW_MARKERS`.

## License

GNU General Public License v3.0. See [LICENSE.md](LICENSE.md).
