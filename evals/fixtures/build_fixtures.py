#!/usr/bin/env python3
"""Build one throwaway git repo per prreview eval case.

Usage: build_fixtures.py <eval-name> <dest-dir>

Each repo is a tiny Python project with unittest tests and a seeded .adp/ corpus.
The seeded defects are listed in evals.json next to each case, and the grader
checks the review against them, so a change here must change evals.json too.
"""
import os
import subprocess
import sys
import textwrap

ENV = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.com",
           GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.com")


def git(repo, *args, date="2026-10-01T12:00:00"):
    env = dict(ENV, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def write(repo, path, text):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(text).lstrip("\n"))


def commit(repo, msg, date):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, date=date)


BASE_LEDGER = '''
"""Small ledger helpers."""


def total(amounts):
    """Return the sum of every amount."""
    return sum(amounts)
'''

BASE_TEST = '''
import unittest

from src.ledger import total


class TotalTest(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([1, 2, 3]), 6)


if __name__ == "__main__":
    unittest.main()
'''


def base_repo(repo):
    os.makedirs(repo, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    # The fixtures model a project that commits .adp/, so a user-wide ignore rule must not apply.
    git(repo, "config", "core.excludesFile", "/dev/null")
    write(repo, "src/__init__.py", "")
    write(repo, "src/ledger.py", BASE_LEDGER)
    write(repo, "tests/__init__.py", "")
    write(repo, "tests/test_ledger.py", BASE_TEST)
    write(repo, "run_tests.sh", """
        #!/usr/bin/env bash
        # Runs the unittest suite from the repository root. The exit code is the verdict.
        cd "$(dirname "$0")"
        python3 -m unittest discover -s tests -t . -v
    """)
    os.chmod(os.path.join(repo, "run_tests.sh"), 0o755)
    write(repo, ".gitignore", "__pycache__/\n")
    write(repo, "CLAUDE.md", """
        # CLAUDE.md
        Run `./run_tests.sh` for the test suite. All ADP work lives in `.adp/<task-id>/`.
    """)
    write(repo, ".adp/.gitkeep", "")
    commit(repo, "Initial ledger", "2026-10-01T09:00:00")


def audit_log(task, title, problem, dl_entries, premortem_rows, mandatory, extra=""):
    return f"""
# Audit Log — {task}

## Problem Statement
**What the problem is:** {problem}
**What the problem is not:** Not a change to `total`.
**Human-level definition of done:** {title}
**Confirmed by:** developer   **Date:** 2026-10-02
**Revision history:** none.

## Knowledge Gap Document
| Known | Inferred (flagged) | Cannot Determine |
|-------|--------------------|------------------|
| `src/ledger.py` holds the helpers. | Callers pass lists. | — |

## Open Questions (resolve before Phase 3)
1. None.

## Recommendation Brief
**Recommended approach:** One function in `src/ledger.py`.
**Defense:** The module already holds the ledger helpers.
**Alternatives considered:**
| Alternative | Reason rejected |
|-------------|-----------------|
| A new module | One function does not need one. |
**Assumptions this depends on:** See the Decision Log.

## Pre-Mortem Report
Assumed: this implementation failed in production. Most likely causes:
| Failure mode | Likelihood | Impact | Developer response (rebuttal or mitigation) | Monitoring signal | Implemented at |
|--------------|------------|--------|---------------------------------------------|-------------------|----------------|
{premortem_rows}

## Implementation Authorization
All HIGH-likelihood items resolved: YES
Authorized by: developer

## Decision Log
{dl_entries}

## Test Adversary Document
**What passing tests prove:** The happy path of the new function.
**What passing tests do not prove:**
| Gap | Why untestable / untested | Risk if the assumption is wrong | dl_ref |
|-----|---------------------------|---------------------------------|--------|
| Large inputs | Not measured | Slow calls | DL-001 |
**Untestable assumptions logged to Decision Log:** DL-001

## PR Summary
**Problem being solved:** → Problem Statement Document
**Approach taken:** → Recommendation Brief
**Key decisions:** → Decision Log

## 🚩 Mandatory Review Items (LOW-confidence decisions)
{mandatory}

## Residual Risk
Large inputs are not measured.

## Test Coverage Gaps
→ Test Adversary Document
{extra}"""


def dl(n, title, decision, conf, basis, assumptions, status="OPEN"):
    return f"""
### [DL-{n:03d}] {title}
- **Decision:** {decision}
- **Alternatives considered:** None worth a row.
- **Rationale:** It is the simplest shape that meets the Problem Statement.
- **Confidence:** {conf}
- **Confidence basis:** {basis}
- **Assumptions:** {assumptions}
- **Monitoring signal:** A caller reports a wrong result — fires at one — distinguishes: a caller passing bad input, which a stack trace shows.
- **Created:** 2026-10-02, Phase 5
- **Status:** {status}
"""


def build_branch_single_task(repo):
    base_repo(repo)
    git(repo, "checkout", "-q", "-b", "lgr-01-page-window")
    task = "LGR-01-page-window"
    # Seeded defect 1 (COR): the slice end adds one, so a page holds size + 1 items.
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def page(items, number, size):
    """Return page `number` (1-based) of `items`, holding at most `size` items."""
    start = (number - 1) * size
    return items[start:start + size + 1]
''')
    write(repo, "tests/test_ledger.py", BASE_TEST.replace(
        "from src.ledger import total", "from src.ledger import page, total").replace(
        "\n\nif __name__", '''

class PageTest(unittest.TestCase):
    def test_first_page_of_short_list(self):
        self.assertEqual(page([1, 2], 1, 5), [1, 2])


if __name__'''))
    # Seeded defect 2 (ADP-02): the Pre-Mortem anchor for the size guard is absent from the code.
    # Seeded defect 3 (ADP-06): DL-002 is LOW and Mandatory Review Items says there is none.
    rows = ('| A caller passes size 0 and loops forever over empty pages. | M | H | Mitigation: `page` '
            'raises ValueError when size is not positive. | A ValueError in the caller log — fires at one — '
            'distinguishes: a caller bug, which names a different line. | `src/ledger.py` § "if size <= 0: '
            'raise ValueError" (line 12, advisory) |')
    entries = (dl(1, "Pages are list slices", "`page` slices the list.", "HIGH",
                  "DIRECT EVIDENCE — callers hold lists in memory.", "Lists fit in memory.")
               + dl(2, "Callers never ask for page 0", "`page` does not guard `number` below 1.", "LOW",
                    "DEVELOPER ASSERTION — the developer said callers start at 1.",
                    "No caller passes `number` 0 or less."))
    write(repo, f".adp/{task}/audit-log.md", audit_log(
        task, "A caller gets one page of at most `size` items.",
        "Callers need to page through a ledger list.", entries, rows,
        "No Decision Log entry is at LOW confidence."))
    commit(repo, "Add page() for ledger lists", "2026-10-03T10:00:00")


def build_multi_task_base(repo):
    base_repo(repo)
    git(repo, "checkout", "-q", "-b", "feature/batch-work")
    t1, t2 = "LGR-02-csv-export", "LGR-03-csv-escape"
    write(repo, "src/csv_export.py", '''
        """CSV export for ledger rows."""


        def export_csv(rows):
            """Return rows as CSV text, one line per row."""
            return "\\n".join(",".join(str(v) for v in row) for row in rows)
    ''')
    write(repo, f".adp/{t1}/audit-log.md", audit_log(
        t1, "A caller gets CSV text for a list of rows.", "Ledger rows need a CSV export.",
        dl(1, "Rows join with commas", "`export_csv` joins values with commas.", "HIGH",
           "DIRECT EVIDENCE — rows are short lists.", "Rows are lists of scalars."),
        "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None."))
    commit(repo, "Add CSV export", "2026-10-03T10:00:00")
    # Seeded defect (COR): commas are quoted, but a value holding a double quote is not escaped.
    write(repo, "src/csv_export.py", '''
        """CSV export for ledger rows."""


        def _cell(value):
            text = str(value)
            if "," in text:
                return '"' + text + '"'
            return text


        def export_csv(rows):
            """Return rows as RFC 4180 CSV text, one line per row."""
            return "\\n".join(",".join(_cell(v) for v in row) for row in rows)
    ''')
    write(repo, f".adp/{t2}/audit-log.md", audit_log(
        t2, "CSV values that hold commas or quotes stay one cell.", "Values with commas break the export.",
        dl(1, "Quote values that need it", "`_cell` quotes a value that holds a comma.", "HIGH",
           "INFERENCE FROM CONVENTION — RFC 4180.", "Values hold no newlines."),
        "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None."))
    commit(repo, "Escape CSV values", "2026-10-04T10:00:00")


R1_REVIEW = """
# PR Review — local round 1 · LGR-04-balance

## Review Target
- **Schema:** adp-pr-review/1
- **Task:** LGR-04-balance
- **Tasks on branch:** —
- **Task resolution:** BRANCH NAME — the branch equals the directory name in lowercase.
- **Mode:** LOCAL
- **PR:** —
- **Branch:** lgr-04-balance → main
- **Head:** {head}
- **Base:** {base}
- **Round:** 1
- **Previous round:** —
- **Date:** 2026-10-10

## Findings

### [PR-COR-001] balance drops negative amounts
- **Severity:** must
- **Category:** COR — Correctness
- **Location:** `src/ledger.py:12` (RIGHT)
- **Claim:** `balance` sums only positive amounts, so a withdrawal never lowers the balance.
- **Evidence:** `return sum(a for a in amounts if a > 0)` at `src/ledger.py:12`.
- **Failure scenario:** `balance([100, -30])` returns 100, not 70.
- **Suggested fix:** `balance` returns the sum of every amount. A test asserts `balance([100, -30]) == 70`.
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I ran the call and read the result.
- **Verification:** `python3 -c "from src.ledger import balance; print(balance([100, -30]))"` printed 100.
- **Criterion:** correctness
- **Refs:** —
- **Created:** 2026-10-10, round 1
- **Status:** OPEN

## Review Verdict
- **Verdict:** REQUEST_CHANGES
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I read the diff and ran the tests.
- **Counts:** must 1 / should 0 / question 0 / nit 0
- **Opened:** PR-COR-001
- **Closed:** —
- **Carried open:** —
- **Summary:** REQUEST_CHANGES. 1 must, 0 should, 0 question, 0 nit. PR-COR-001: balance drops negative amounts. Tests 2 pass, 0 fail.
"""


def build_re_review(repo):
    base_repo(repo)
    git(repo, "checkout", "-q", "-b", "lgr-04-balance")
    task = "LGR-04-balance"
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def balance(amounts):
    """Return the running balance: deposits are positive, withdrawals negative."""
    return sum(a for a in amounts if a > 0)
''')
    log = audit_log(task, "A caller gets the balance and an overdraft flag.", "Callers need a balance.",
                    dl(1, "Balance is a plain sum", "`balance` sums the amounts.", "HIGH",
                       "DIRECT EVIDENCE — amounts are ints.", "Amounts are ints."),
                    "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None.")
    write(repo, f".adp/{task}/audit-log.md", log)
    commit(repo, "Add balance()", "2026-10-09T10:00:00")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    base = subprocess.run(["git", "rev-parse", "main"], cwd=repo, capture_output=True, text=True).stdout.strip()
    write(repo, f".adp/{task}/pr-review-local-20261010-r1.md", R1_REVIEW.format(head=head, base=base))
    with open(os.path.join(repo, f".adp/{task}/audit-log.md"), "a", encoding="utf-8") as f:
        f.write(f"""
## Review findings — local round 1 (2026-10-10)
- **Review file:** `.adp/{task}/pr-review-local-20261010-r1.md`
- **Verdict:** REQUEST_CHANGES
- **Counts:** must 1 / should 0 / question 0 / nit 0
- **Opened:** PR-COR-001
- **Closed:** —
- **Head:** {head}
""")
    commit(repo, "Record prreview round 1", "2026-10-10T10:00:00")
    # The fix for PR-COR-001, plus seeded defect (COR): overdraft compares with limit, not -limit.
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def balance(amounts):
    """Return the running balance: deposits are positive, withdrawals negative."""
    return sum(amounts)


def overdraft(amounts, limit):
    """Return True when the balance is below -limit."""
    return balance(amounts) < limit
''')
    write(repo, "tests/test_ledger.py", BASE_TEST.replace(
        "from src.ledger import total", "from src.ledger import balance, total").replace(
        "\n\nif __name__", '''

class BalanceTest(unittest.TestCase):
    def test_withdrawal_lowers_balance(self):
        self.assertEqual(balance([100, -30]), 70)


if __name__'''))
    commit(repo, "Sum every amount and add overdraft()", "2026-10-11T10:00:00")


R1_RESPONSE_REVIEW = """
# PR Review — local round 1 · LGR-09-fees

## Review Target
- **Schema:** adp-pr-review/1
- **Task:** LGR-09-fees
- **Tasks on branch:** —
- **Task resolution:** BRANCH NAME — the branch equals the directory name in lowercase.
- **Mode:** LOCAL
- **PR:** —
- **Branch:** lgr-09-fees → main
- **Head:** {head}
- **Base:** {base}
- **Round:** 1
- **Previous round:** —
- **Date:** 2026-10-12

## Findings

### [PR-COR-001] fee rounds a half cent down to even
- **Severity:** should
- **Category:** COR — Correctness
- **Location:** `src/ledger.py:11` (RIGHT)
- **Claim:** `fee` uses `round`, which rounds a half to the nearest even number, so a fee of 2.5 cents becomes 2.
- **Evidence:** `return round(amount * rate)` at `src/ledger.py:11`.
- **Failure scenario:** `fee(250, 0.01)` returns 2, not 3.
- **Suggested fix:** `fee` rounds a half up. A test asserts `fee(250, 0.01) == 3`.
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I ran the call and read the result.
- **Verification:** `python3 -c "from src.ledger import fee; print(fee(250, 0.01))"` printed 2.
- **Criterion:** correctness
- **Refs:** —
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

### [PR-CON-001] the unit of rate is not stated
- **Severity:** question
- **Category:** CON — Contract
- **Location:** `src/ledger.py:9` (RIGHT)
- **Claim:** Nothing states whether `rate` is a fraction such as 0.01 or a percent such as 1, and a percent would charge 100 times the fee.
- **Evidence:** `def fee(amount, rate):` at `src/ledger.py:9`, and the docstring names no unit.
- **Failure scenario:** A caller passes `1` for one percent, and `fee(250, 1)` returns 250.
- **Suggested fix:** The docstring or DL-001 names the unit of `rate`. The developer names the unit.
- **Confidence:** MEDIUM
- **Confidence basis:** INFERENCE FROM CONVENTION — no caller exists in the diff.
- **Verification:** `grep -rn "fee(" src tests` found no caller.
- **Criterion:** contract
- **Refs:** DL-001
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

### [PR-TST-001] fee has no test
- **Severity:** should
- **Category:** TST — Tests
- **Location:** `tests/test_ledger.py`
- **Claim:** No test calls `fee`, so a change to its rounding passes the suite.
- **Evidence:** `grep -n "fee" tests/test_ledger.py` found no match.
- **Failure scenario:** A later edit makes `fee` return 0, and the tests still pass.
- **Suggested fix:** A test asserts `fee` for a whole-cent case and a half-cent case.
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I read the test file.
- **Verification:** `grep -n "fee" tests/test_ledger.py` exited 1.
- **Criterion:** tests
- **Refs:** —
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

## Review Verdict
- **Verdict:** COMMENT
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I read the diff and ran the tests.
- **Counts:** must 0 / should 2 / question 1 / nit 0
- **Opened:** PR-COR-001, PR-CON-001, PR-TST-001
- **Closed:** —
- **Carried open:** —
- **Summary:** COMMENT. 0 must, 2 should, 1 question, 0 nit. PR-COR-001: fee rounds a half cent down to even. Tests 1 pass, 0 fail.
"""


def build_response_round(repo):
    base_repo(repo)
    git(repo, "checkout", "-q", "-b", "lgr-09-fees")
    task = "LGR-09-fees"
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def fee(amount, rate):
    """Return the fee for an amount, in whole cents."""
    return round(amount * rate)
''')
    log = audit_log(task, "A caller gets the fee for an amount.", "Payments need a fee.",
                    dl(1, "Fee is a rounded product", "`fee` multiplies the amount by the rate and rounds.", "HIGH",
                       "DIRECT EVIDENCE — amounts are whole cents.", "Amounts are whole cents."),
                    "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None.")
    write(repo, f".adp/{task}/audit-log.md", log)
    commit(repo, "Add fee()", "2026-10-11T10:00:00")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    base = subprocess.run(["git", "rev-parse", "main"], cwd=repo, capture_output=True, text=True).stdout.strip()
    write(repo, f".adp/{task}/pr-review-local-20261012-r1.md", R1_RESPONSE_REVIEW.format(head=head, base=base))
    pointer = f"""
## Review findings — local round 1 (2026-10-12)
- **Review file:** `.adp/{task}/pr-review-local-20261012-r1.md`
- **Verdict:** COMMENT
- **Counts:** must 0 / should 2 / question 1 / nit 0
- **Opened:** PR-COR-001, PR-CON-001, PR-TST-001
- **Closed:** —
- **Head:** {head}
"""
    with open(os.path.join(repo, f".adp/{task}/audit-log.md"), "a", encoding="utf-8") as f:
        f.write(pointer)
    commit(repo, "Record prreview round 1", "2026-10-12T10:00:00")
    # The developer accepts PR-TST-001 by hand in the working tree and does not commit it, so the
    # review must read the acceptance from the working-tree log under record source GIT HEAD.
    with open(os.path.join(repo, f".adp/{task}/audit-log.md"), "a", encoding="utf-8") as f:
        f.write("- **PR-TST-001 CLOSED 2026-10-13 → ACCEPTED.** Dana Reyes, the task owner, accepted "
                "the missing test until the billing tests land in LGR-10.\n")


R1_REFUTE_REVIEW = """
# PR Review — local round 1 · LGR-11-clamp

## Review Target
- **Schema:** adp-pr-review/1
- **Task:** LGR-11-clamp
- **Tasks on branch:** —
- **Task resolution:** BRANCH NAME — the branch equals the directory name in lowercase.
- **Mode:** LOCAL
- **PR:** —
- **Branch:** lgr-11-clamp → main
- **Head:** {head}
- **Base:** {base}
- **Round:** 1
- **Previous round:** —
- **Date:** 2026-10-12

## Findings

### [PR-COR-001] clamp does not bound a negative amount
- **Severity:** should
- **Category:** COR — Correctness
- **Location:** `src/ledger.py:11` (RIGHT)
- **Claim:** `min(amount, limit)` caps only the high side, so a negative amount below `-limit` passes through.
- **Evidence:** `return max(-limit, min(amount, limit))` at `src/ledger.py:11`.
- **Failure scenario:** `clamp(-500, 100)` returns -500, not -100.
- **Suggested fix:** `clamp` also bounds the low side. A test asserts `clamp(-500, 100) == -100`.
- **Confidence:** MEDIUM
- **Confidence basis:** INFERENCE FROM CONVENTION — I read the line and did not run it.
- **Verification:** Read `src/ledger.py:11`.
- **Criterion:** correctness
- **Refs:** —
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

### [PR-CON-001] callers may pass a negative limit
- **Severity:** question
- **Category:** CON — Contract
- **Location:** `src/ledger.py:9` (RIGHT)
- **Claim:** Nothing states that `limit` is positive, and a negative limit returns `-limit` for every amount.
- **Evidence:** `def clamp(amount, limit):` at `src/ledger.py:9`, and the docstring names no sign for `limit`.
- **Failure scenario:** A caller passes `-1`, and `clamp(5, -1)` returns 1.
- **Suggested fix:** The docstring or DL-001 states that `limit` is positive. The developer names what callers pass.
- **Confidence:** MEDIUM
- **Confidence basis:** INFERENCE FROM CONVENTION — no caller exists in the diff.
- **Verification:** `grep -rn "clamp(" src tests` found no caller.
- **Criterion:** contract
- **Refs:** DL-001
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

### [PR-TST-001] clamp has no test
- **Severity:** should
- **Category:** TST — Tests
- **Location:** `tests/test_ledger.py`
- **Claim:** No test calls `clamp`, so a change to its bounds passes the suite.
- **Evidence:** `grep -n "clamp" tests/test_ledger.py` found no match.
- **Failure scenario:** A later edit makes `clamp` return `amount`, and the tests still pass.
- **Suggested fix:** A test asserts `clamp` above, inside, and below the range.
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — I read the test file.
- **Verification:** `grep -n "clamp" tests/test_ledger.py` exited 1.
- **Criterion:** tests
- **Refs:** —
- **Created:** 2026-10-12, round 1
- **Status:** OPEN

## Review Verdict
- **Verdict:** COMMENT
- **Confidence:** MEDIUM
- **Confidence basis:** INFERENCE FROM CONVENTION — I read the diff and ran the tests, and I did not run `clamp`.
- **Counts:** must 0 / should 2 / question 1 / nit 0
- **Opened:** PR-COR-001, PR-CON-001, PR-TST-001
- **Closed:** —
- **Carried open:** —
- **Summary:** COMMENT. 0 must, 2 should, 1 question, 0 nit. PR-COR-001: clamp does not bound a negative amount. Tests 1 pass, 0 fail.
"""


def build_refute_round(repo):
    base_repo(repo)
    git(repo, "checkout", "-q", "-b", "lgr-11-clamp")
    task = "LGR-11-clamp"
    # PR-COR-001 in the r1 file is wrong: max() bounds the low side, so clamp(-500, 100) is -100.
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def clamp(amount, limit):
    """Return the amount bounded to the range from -limit to limit."""
    return max(-limit, min(amount, limit))
''')
    log = audit_log(task, "A caller gets an amount bounded by a limit.", "Payments need a cap.",
                    dl(1, "Clamp with min and max", "`clamp` bounds the amount with `min` and `max`.", "HIGH",
                       "DIRECT EVIDENCE — amounts are whole cents.", "Amounts are whole cents."),
                    "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None.")
    write(repo, f".adp/{task}/audit-log.md", log)
    commit(repo, "Add clamp()", "2026-10-11T10:00:00")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    base = subprocess.run(["git", "rev-parse", "main"], cwd=repo, capture_output=True, text=True).stdout.strip()
    write(repo, f".adp/{task}/pr-review-local-20261012-r1.md", R1_REFUTE_REVIEW.format(head=head, base=base))
    pointer = f"""
## Review findings — local round 1 (2026-10-12)
- **Review file:** `.adp/{task}/pr-review-local-20261012-r1.md`
- **Verdict:** COMMENT
- **Counts:** must 0 / should 2 / question 1 / nit 0
- **Opened:** PR-COR-001, PR-CON-001, PR-TST-001
- **Closed:** —
- **Head:** {head}
"""
    with open(os.path.join(repo, f".adp/{task}/audit-log.md"), "a", encoding="utf-8") as f:
        f.write(pointer)
    commit(repo, "Record prreview round 1", "2026-10-12T10:00:00")
    # An uncommitted acceptance that names no person, so it must close nothing.
    with open(os.path.join(repo, f".adp/{task}/audit-log.md"), "a", encoding="utf-8") as f:
        f.write("- **PR-TST-001 CLOSED 2026-10-13 → ACCEPTED.** Accepted until the billing tests land in LGR-10.\n")


def build_ambiguous(repo):
    base_repo(repo)
    for task in ("LGR-05-rounding", "LGR-06-currency"):
        write(repo, f".adp/{task}/audit-log.md", audit_log(
            task, "Done.", "A ledger task.", dl(1, "x", "y", "HIGH", "DIRECT EVIDENCE — z.", "None."),
            "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None."))
    commit(repo, "Open two ledger tasks", "2026-10-02T10:00:00")
    git(repo, "checkout", "-q", "-b", "wip")
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def average(amounts):
    """Return the mean amount."""
    return sum(amounts) / len(amounts)
''')
    commit(repo, "Add average()", "2026-10-03T10:00:00")


def build_untracked_adp(repo):
    base_repo(repo)
    # The project keeps .adp/ out of git, so the record lives only in the working tree.
    write(repo, ".gitignore", "__pycache__/\n.adp/\n")
    git(repo, "rm", "-q", "--cached", ".adp/.gitkeep")
    commit(repo, "Keep .adp/ out of git", "2026-10-01T10:00:00")
    git(repo, "checkout", "-q", "-b", "feature/rounding")
    # Seeded defect (COR): int() truncates the float product, so 0.29 becomes 28 cents.
    write(repo, "src/ledger.py", BASE_LEDGER + '''

def to_cents(amount):
    """Return a decimal amount as whole cents."""
    return int(amount * 100)
''')
    commit(repo, "Add to_cents()", "2026-10-03T10:00:00")
    for task, branch_line in (("20261002-LGR-07-cents", "Run start 2026-10-02, on branch `feature/rounding` cut from `main`.\n"),
                              ("20261001-LGR-08-reports", "Run start 2026-10-01, on branch `lgr-08-reports` cut from `main`.\n")):
        log = audit_log(task, "A caller gets whole cents.", "Amounts need cents.",
                        dl(1, "Cents are ints", "`to_cents` returns an int.", "HIGH", "DIRECT EVIDENCE — callers store ints.", "None."),
                        "| — | L | L | Rebuttal: trivial. | UNOBSERVABLE — trivial. | — |", "None.")
        write(repo, f".adp/{task}/audit-log.md", log.replace("\n## Problem Statement", "\n" + branch_line + "\n## Problem Statement", 1))


def docs_repo(repo, extra):
    # No tests/ and no run_tests.sh: the project has no test command, so a review on main caps
    # its confidence at MEDIUM. `extra` maps paths to the files the case adds to the base commit.
    os.makedirs(repo, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.excludesFile", "/dev/null")
    write(repo, "src/__init__.py", "")
    write(repo, "src/ledger.py", BASE_LEDGER)
    write(repo, "README.md", """
        # ledger

        Small ledger helpers.
    """)
    write(repo, ".gitignore", "__pycache__/\n")
    write(repo, "CLAUDE.md", """
        # CLAUDE.md
        This project has no test suite. All ADP work lives in `.adp/<task-id>/`.
    """)
    for path, text in extra.items():
        write(repo, path, text)
    write(repo, ".adp/.gitkeep", "")
    commit(repo, "Initial ledger", "2026-10-01T09:00:00")


def docs_log(task, problem, done, decision, approach="Edit the one documentation file."):
    return f"""
# Audit Log — {task}

## Problem Statement
**What the problem is:** {problem}
**What the problem is not:** Not a change to any code.
**Human-level definition of done:** {done}
**Confirmed by:** developer   **Date:** 2026-10-02
**Revision history:** none.

## Knowledge Gap Document
| Known | Inferred (flagged) | Cannot Determine |
|-------|--------------------|------------------|
| `src/ledger.py` defines `total`, which returns `sum(amounts)`. | — | — |

## Open Questions (resolve before Phase 3)
1. None.

## Recommendation Brief
**Recommended approach:** {approach}
**Defense:** The text is the whole change.
**Alternatives considered:**
| Alternative | Reason rejected |
|-------------|-----------------|
| A new file | One section does not need one. |
**Assumptions this depends on:** None.

## Pre-Mortem Report
Assumed: this implementation failed in production. Most likely causes:
| Failure mode | Likelihood | Impact | Developer response (rebuttal or mitigation) | Monitoring signal | Implemented at |
|--------------|------------|--------|---------------------------------------------|-------------------|----------------|
| The text drifts from `total`. | L | L | Rebuttal: `total` is one line and the text quotes it. | A reader reports a wrong example — fires at one — distinguishes: a reader on an old copy, which the commit shows. | — |

## Implementation Authorization
All HIGH-likelihood items resolved: YES
Authorized by: developer

## Decision Log

### [DL-001] One section
- **Decision:** {decision}
- **Alternatives considered:** None worth a row.
- **Rationale:** It is the smallest text that meets the Problem Statement.
- **Confidence:** HIGH
- **Confidence basis:** DIRECT EVIDENCE — `src/ledger.py` returns `sum(amounts)`.
- **Assumptions:** None.
- **Monitoring signal:** A reader reports a wrong example — fires at one — distinguishes: a reader on an old copy, which the commit shows.
- **Created:** 2026-10-02, Phase 5
- **Status:** OPEN

## Test Adversary Document
**What passing tests prove:** Nothing. The project has no test suite, and the change is text.
**What passing tests do not prove:**
| Gap | Why untestable / untested | Risk if the assumption is wrong | dl_ref |
|-----|---------------------------|---------------------------------|--------|
| The example output | No test suite exists | A reader copies a wrong example | DL-001 |
**Untestable assumptions logged to Decision Log:** DL-001

## PR Summary
**Problem being solved:** → Problem Statement Document
**Approach taken:** → Recommendation Brief
**Key decisions:** → Decision Log

## 🚩 Mandatory Review Items (LOW-confidence decisions)
No Decision Log entry is at LOW confidence.

## Residual Risk
None beyond DL-001.

## Test Coverage Gaps
→ Test Adversary Document
"""


def build_docs_only_readme(repo):
    docs_repo(repo, {})
    git(repo, "checkout", "-q", "-b", "lgr-12-readme-usage")
    task = "LGR-12-readme-usage"
    # No seeded defect: the README example is true, and no file in the repo reads README.md.
    write(repo, "README.md", """
        # ledger

        Small ledger helpers.

        ## Usage

        `total` returns the sum of a list of amounts:

        ```python
        from src.ledger import total

        total([1, 2, 3])  # 6
        ```
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The README does not say how to call `total`.",
        "A reader of the README can call `total` and knows what it returns.",
        "Add a Usage section to `README.md` with one `total` example."))
    commit(repo, "Document total() in the README", "2026-10-03T10:00:00")


SKILL_MD = """
    ---
    name: ledger-style
    description: Write ledger helpers in the house style.
    ---

    # ledger-style

    Read `references/style.md` before you write a helper, and follow every rule in it.
"""


def build_docs_agent_read(repo):
    docs_repo(repo, {"SKILL.md": SKILL_MD, "references/style.md": """
        # Style

        - Give every helper a one-line docstring.
    """})
    git(repo, "checkout", "-q", "-b", "lgr-13-style-return")
    task = "LGR-13-style-return"
    # No seeded defect: the new rule is true of `total`. The file is Markdown that an agent
    # follows, because SKILL.md tells the agent to read it, so the change is code, not docs.
    write(repo, "references/style.md", """
        # Style

        - Give every helper a one-line docstring.
        - Start the docstring with "Return" when the helper returns a value.
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The style rules do not say how a docstring starts.",
        "An agent that follows `references/style.md` starts a returning helper's docstring with \"Return\".",
        "Add one rule to `references/style.md`."))
    commit(repo, "Add the docstring start rule", "2026-10-03T10:00:00")


def build_docs_readme_read(repo):
    docs_repo(repo, {"scripts/gen_help.py": """
        \"\"\"Print the README as the command-line help text.\"\"\"
        print(open("README.md", encoding="utf-8").read())
    """})
    git(repo, "checkout", "-q", "-b", "lgr-14-readme-usage")
    task = "LGR-14-readme-usage"
    # No seeded defect in the text. scripts/gen_help.py opens README.md, so the README is a
    # runtime input and the change is not docs only, although only README.md changed.
    write(repo, "README.md", """
        # ledger

        Small ledger helpers.

        ## Usage

        `total` returns the sum of a list of amounts:

        ```python
        from src.ledger import total

        total([1, 2, 3])  # 6
        ```
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The README does not say how to call `total`.",
        "A reader of the README can call `total` and knows what it returns.",
        "Add a Usage section to `README.md` with one `total` example."))
    commit(repo, "Document total() in the README", "2026-10-03T10:00:00")



def build_docs_profile_path(repo):
    docs_repo(repo, {"notes/usage.md": """
        # Usage notes

        Import the helpers from `src.ledger`.
    """, ".adp/pr-review-quality.yaml": """
        id: ledger-quality
        version: 1
        review_dimensions:
          - id: correctness
            required: true
            pass: Changed behavior satisfies the requested outcome.
        documentation_paths:
          - notes/
    """})
    git(repo, "checkout", "-q", "-b", "lgr-15-notes-total")
    task = "LGR-15-notes-total"
    # No seeded defect. notes/ is not a default doc path, so only the profile's
    # documentation_paths makes notes/usage.md a docs-only candidate.
    write(repo, "notes/usage.md", """
        # Usage notes

        Import the helpers from `src.ledger`.

        `total([1, 2, 3])` returns `6`.
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The usage notes do not show what `total` returns.",
        "A reader of `notes/usage.md` knows what `total` returns.",
        "Add one `total` example to `notes/usage.md`."))
    commit(repo, "Show total() in the usage notes", "2026-10-03T10:00:00")



def build_docs_mention_only(repo):
    docs_repo(repo, {
        "src/ledger.py": BASE_LEDGER.replace('"""Small ledger helpers."""', '"""Small ledger helpers. See README.md for usage."""'),
        "LICENSE.md": """
            # License

            Copyright 2025 Ledger authors. All rights reserved.
        """,
        "scripts/make_fixture.py": """
            \"\"\"Write a sample project into the folder named on the command line.\"\"\"
            import os
            import sys

            dest = sys.argv[1]
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
                f.write("# sample\\n")
        """})
    git(repo, "checkout", "-q", "-b", "lgr-16-readme-license")
    task = "LGR-16-readme-license"
    # No seeded defect. Two files name README.md without reading the repo's README:
    # a docstring in src/ledger.py and a fixture script that writes its own copy. The README
    # names LICENSE.md, and both are candidates, so that link is not a reader either.
    write(repo, "README.md", """
        # ledger

        Small ledger helpers.

        ## Usage

        `total` returns the sum of a list of amounts:

        ```python
        from src.ledger import total

        total([1, 2, 3])  # 6
        ```

        ## License

        See `LICENSE.md`.
    """)
    write(repo, "LICENSE.md", """
        # License

        Copyright 2026 Ledger authors. All rights reserved.
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The README does not say how to call `total` or where the license is, and the license year is old.",
        "A reader of the README can call `total`, finds the license, and the license shows 2026.",
        "Add Usage and License sections to `README.md`, and set the year in `LICENSE.md` to 2026.",
        "Edit `README.md` and `LICENSE.md`, the two documentation files the change needs."))
    commit(repo, "Document total() and the license", "2026-10-03T10:00:00")



def build_docs_script(repo):
    docs_repo(repo, {"docs/run_examples.py": """
        \"\"\"Run the README examples by hand and print each result.\"\"\"
        from src.ledger import total

        print(total([1, 2, 3]))
    """})
    git(repo, "checkout", "-q", "-b", "lgr-17-examples-exit")
    task = "LGR-17-examples-exit"
    # No seeded defect. The file sits under docs/, but it is a Python script, so it is code and
    # the change is not docs only, although no tracked file names it.
    write(repo, "docs/run_examples.py", """
        \"\"\"Run the README examples by hand and print each result.\"\"\"
        import sys

        from src.ledger import total

        result = total([1, 2, 3])
        print(result)
        sys.exit(0 if result == 6 else 1)
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The examples script does not report a wrong result.",
        "Running `docs/run_examples.py` exits non-zero when `total` gives a wrong result.",
        "Make `docs/run_examples.py` exit 1 when the example result is wrong.",
        "Edit `docs/run_examples.py`, the one file the change needs."))
    commit(repo, "Exit non-zero from the examples script on a wrong result", "2026-10-03T10:00:00")



def build_docs_makefile(repo):
    docs_repo(repo, {"docs/guide.md": """
        # Guide

        Call `total` with a list of amounts.
    """, "docs/Makefile": """
        html:
        \tpython3 -m markdown guide.md > guide.html
    """})
    write(repo, "README.md", """
        # ledger

        Small ledger helpers. Build the HTML guide with `make -C docs html`.
    """)
    commit(repo, "Point the README at the guide build", "2026-10-01T09:30:00")
    git(repo, "checkout", "-q", "-b", "lgr-18-docs-make")
    task = "LGR-18-docs-make"
    # No seeded defect. The file sits under docs/ and has no extension, but it is a build file,
    # so it is code and the change is not docs only, although only a candidate names it.
    write(repo, "docs/Makefile", """
        html:
        \tmkdir -p build
        \tpython3 -m markdown guide.md > build/guide.html
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The guide build writes its HTML next to the source.",
        "`make -C docs html` writes the HTML guide to `docs/build/`.",
        "Make the `html` target write to `docs/build/guide.html`.",
        "Edit `docs/Makefile`, the one file the change needs."))
    commit(repo, "Write the HTML guide to docs/build", "2026-10-03T10:00:00")


def build_docs_requirements(repo):
    docs_repo(repo, {"docs/guide.md": """
        # Guide

        Call `total` with a list of amounts.
    """, "docs/requirements.txt": "markdown==3.5\n"})
    write(repo, "README.md", """
        # ledger

        Small ledger helpers. Install the guide tools with `pip install -r docs/requirements.txt`.
    """)
    commit(repo, "Point the README at the guide tools", "2026-10-01T09:30:00")
    git(repo, "checkout", "-q", "-b", "lgr-19-docs-reqs")
    task = "LGR-19-docs-reqs"
    # No seeded defect. The file sits under docs/ and ends in .txt, but pip reads it by its name,
    # so it is code and the change is not docs only, although only a candidate names it.
    write(repo, "docs/requirements.txt", "markdown==3.6\n")
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The guide tools pin an old Markdown release.",
        "`pip install -r docs/requirements.txt` installs Markdown 3.6.",
        "Pin `markdown==3.6` in `docs/requirements.txt`.",
        "Edit `docs/requirements.txt`, the one file the change needs."))
    commit(repo, "Pin Markdown 3.6 for the guide tools", "2026-10-03T10:00:00")


def build_docs_jekyll(repo):
    docs_repo(repo, {"docs/_config.yml": "theme: jekyll-theme-minimal\n", "docs/index.md": """
        # Guide

        Call `total` with a list of amounts.
    """})
    git(repo, "checkout", "-q", "-b", "lgr-20-pages-intro")
    task = "LGR-20-pages-intro"
    # No seeded defect. The page is Markdown under docs/, and no tracked file names it, but
    # docs/_config.yml makes docs/ a Jekyll site that builds every page in it, so the change is
    # not docs only.
    write(repo, "docs/index.md", """
        # Guide

        Call `total` with a list of amounts. It returns their sum.
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The guide page does not say what `total` returns.",
        "A reader of the guide page learns that `total` returns the sum.",
        "Add one sentence on the return value to `docs/index.md`."))
    commit(repo, "Say what total returns on the guide page", "2026-10-03T10:00:00")


def build_docs_include(repo):
    docs_repo(repo, {"README.rst": """
        ledger
        ======

        Small ledger helpers. Call ``total`` with a list of amounts.
    """, "docs/conf.py": "project = 'ledger'\n", "docs/index.rst": """
        Ledger guide
        ============

        .. include:: ../README.rst
    """})
    git(repo, "checkout", "-q", "-b", "lgr-21-readme-return")
    task = "LGR-21-readme-return"
    # No seeded defect. README.rst sits outside docs/, and the only line that names it is inside
    # docs/index.rst, another candidate. That line includes README.rst into the Sphinx build that
    # docs/conf.py configures, so the change is not docs only.
    write(repo, "README.rst", """
        ledger
        ======

        Small ledger helpers. Call ``total`` with a list of amounts. It returns their sum.
    """)
    write(repo, f".adp/{task}/audit-log.md", docs_log(
        task, "The README does not say what `total` returns.",
        "A reader of `README.rst` learns that `total` returns the sum.",
        "Add one sentence on the return value to `README.rst`.",
        "Edit `README.rst`, the one file the change needs."))
    commit(repo, "Say what total returns in the README", "2026-10-03T10:00:00")


BUILDERS = {
    "branch-single-task": build_branch_single_task,
    "multi-task-base": build_multi_task_base,
    "re-review-round-2": build_re_review,
    "ambiguous-placement": build_ambiguous,
    "untracked-adp": build_untracked_adp,
    "response-round-2": build_response_round,
    "response-refute-round-2": build_refute_round,
    # Round 1 with a RESPONSE clause: the clause names no OPEN finding, so it changes nothing.
    "response-round-1": build_branch_single_task,
    "docs-only-readme": build_docs_only_readme,
    "docs-agent-read": build_docs_agent_read,
    "docs-readme-read": build_docs_readme_read,
    "docs-profile-path": build_docs_profile_path,
    "docs-mention-only": build_docs_mention_only,
    "docs-script": build_docs_script,
    "docs-makefile": build_docs_makefile,
    "docs-requirements": build_docs_requirements,
    "docs-jekyll": build_docs_jekyll,
    "docs-include": build_docs_include,
}

if __name__ == "__main__":
    name, dest = sys.argv[1], sys.argv[2]
    if os.path.exists(dest):
        sys.exit(f"refusing to overwrite {dest}")
    BUILDERS[name](dest)
    print(dest)
