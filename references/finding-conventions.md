# Finding conventions

## Ticket ids

A finding id has the form `PR-<CAT>-<NNN>`: a category code from the table below and a
three-digit number, as in `PR-SEC-003`. The number counts up per category across every
`pr-review-*.md` file in the task directory. An id never repeats in a task and is never reused
after its finding closes. The padding matches ADP's `DL-001` form, so ids sort as text.

## Categories

| Code | Name | Use it for |
|------|------|------------|
| `COR` | Correctness | Wrong behavior, broken logic, unhandled states, regressions in touched paths. |
| `SEC` | Security | Auth, authorization, secrets, untrusted input, unsafe IO, dependency loading. |
| `CON` | Contract | Public API, schema, CLI flag, persisted data, event, or file-format compatibility. |
| `TST` | Tests | A failing test, a missing regression test, or a test that cannot fail. |
| `PERF` | Performance | A measurable cost on a hot path, unbounded growth, or a needless round trip. |
| `OPS` | Operations | Migration safety, rollback, deploy order, observability, configuration. |
| `MNT` | Maintainability | Duplication, dead code, misleading names or comments, needless complexity. |
| `ADP` | ADP conformance | A gap between the change and its task's ADP artifacts. See `adp-checks.md`. |

Pick the category of the root cause, not of the symptom. A missing auth check that a test also
misses is `SEC`. The missing test goes into the `SEC` finding's fix contract.

## Severity

| Severity | Meaning |
|----------|---------|
| `must` | A bug, a broken contract, a security issue, a data-loss risk, a failing test, or a merge-blocking quality gap. |
| `should` | A concrete, evidence-backed risk or pre-merge obligation below a clear correctness blocker. |
| `question` | The code supports a concern, but one named fact, contract source, or human decision decides whether it is a defect. The finding names that input. |
| `nit` | Optional cleanup with no concrete failure, risk, or pre-merge obligation. |

Give each finding the best supported severity. Do not raise a severity to make a finding look
important. An unresolved `question` never blocks the verdict.

## Confidence

Confidence uses ADP's words and bases, never "probably" or "fairly sure".

- **HIGH:** you read the code path end to end, or you ran a repro, and the claim holds.
- **MEDIUM:** you read the changed lines and the nearest contract, but one link in the chain is
  convention or is outside the material you could load.
- **LOW:** the claim rests on convention or on what a developer told you, and you could not check it.

The basis is one of `DIRECT EVIDENCE`, `INFERENCE FROM CONVENTION`, or `DEVELOPER ASSERTION`.
Never let a convention dress as direct evidence. "I do not see it in this code" is not "it does
not happen". Write the weaker claim.

A `must` finding needs HIGH or MEDIUM confidence. A LOW-confidence concern is a `question`.

## Granularity

Write one finding per fix contract. A fix contract is the set of post-fix obligations, and the
verification for each, that resolves the issue. Group nearby issues that one fix resolves. Split
issues that can stay broken independently, belong to different owners, or need separate
verification.

Write **Suggested fix** so a later factory stage can repair from it alone. State the observable
outcome after the fix and how to verify it. Require a specific mechanism only when a contract or
a criterion requires that mechanism. Cover the sibling cases that can still break the same
contract after the obvious fix.

## Status

| Status | Meaning |
|--------|---------|
| `OPEN` | The finding stands against the reviewed head. Every finding starts here. |
| `RESOLVED` | A later head removes the defect, and the reviewer verified the removal. |
| `REFUTED` | Later evidence shows the claim was wrong, or a superseding finding replaces it. |
| `ACCEPTED` | A named person accepted the risk on the record, with no code change. |

A status changes only through a ledger line. See `review-file-template.md`. The entry's own
**Status** line stays `OPEN` forever, as an ADP Decision Log entry keeps its own Status line once
a ruling is recorded.

## Verdict

- `REQUEST_CHANGES` when at least one `must` finding is OPEN, this round or carried.
- `COMMENT` when no `must` is OPEN and at least one `should` or `question` is OPEN.
- `APPROVE` when only `nit` findings, or none, are OPEN.

**Counts** gives the number of findings at each severity that are OPEN after this round: the
findings this round opens plus the findings it carries open. A finding that closes this round, by
any ledger line, is not counted. The verdict rule above reads the same set, so the counts always
explain the verdict. The terminal summary prints the same numbers. In round 1, every finding is
OPEN, so the counts are the findings in the file.

The review confidence is the lowest of these: the confidence your material coverage supports, and
MEDIUM when the tests did not run. Coverage is HIGH when you read every changed file's diff, the
nearby contracts, the audit log, the guidance, and the prior comments. Coverage is MEDIUM when a
nearby contract or the prior comments were unavailable. Coverage is LOW when a key material did
not load.
