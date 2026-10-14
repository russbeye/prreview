# ADP conformance checks

These checks audit the change against its task's `audit-log.md`. A failed check is a finding in
category `ADP`. Its **Criterion** field names the check id, and its **Refs** field names the ADP
entries involved. Run every check whose artifact exists in the log. A missing artifact is itself
check ADP-01.

| Id | Check | Severity when it fails |
|----|-------|------------------------|
| ADP-01 | The log holds every canonical artifact the change's stage needs. A PR needs Phases 1 through 7, and a PR that ships to production also needs Phase 8. A skipped phase has a LOW-confidence Decision Log entry that records the skip. | `must` for a missing Test Adversary Document or PR Summary. `should` otherwise. |
| ADP-02 | Every Pre-Mortem row with a mitigation has an **Implemented at** anchor that is not `PENDING`, and the verbatim anchor exists in the named file at the reviewed head. | `must` when the anchor is absent from the file, because the mitigation is unverified. `should` when the anchor drifted from its line hint or is still `PENDING`. |
| ADP-03 | Every HIGH-likelihood Pre-Mortem row is rebutted or mitigated, and the Implementation Authorization says `YES`. | `must` |
| ADP-04 | Every non-trivial decision visible in the diff has a Decision Log entry. A non-trivial decision is a choice between plausible alternatives: a library, a data shape, a boundary, a default, an error policy, a concurrency rule. | `should` per missing decision. Group the decisions in one file into one finding. |
| ADP-05 | Every Decision Log entry that is OPEN and holds an assumption has a **Monitoring signal** in the observable, threshold, and look-alike form, or a justified UNOBSERVABLE. | `should` |
| ADP-06 | Every LOW-confidence Decision Log entry appears in **Mandatory Review Items** as an unchecked review item. | `must` |
| ADP-07 | Each Test Adversary gap row names a `dl_ref` that exists, and no test in the diff claims to cover a gap the document calls untestable. | `should` |
| ADP-08 | The diff matches the Recommendation Brief, or the PR Summary names the deviation and its reason. | `must` when the deviation is unexplained and changes a contract. `should` otherwise. |
| ADP-09 | A Decision Log entry's claim matches the code at the reviewed head. An entry that says "we write the row inside the transaction" points at code that does so. | `must` when the code contradicts a HIGH-confidence entry. `should` otherwise. |
| ADP-10 | Record grammar is character-exact: ledger lines use `→`, ids have the `DL-` and `OT-<TASKID>-<n>` shapes, and no raw control byte is in the log. | `nit`, or `should` when a ledger line fails to parse and leaves a watch live on the board. |
| ADP-11 | Each phase the log reaches has a written gate confirmation when the run is solo, one-shot, or in auto mode. A confirmation names the check it confirmed and sits before the section's first entry. | `should` |
| ADP-12 | Every outcome the prompt's ask names maps to the Problem Statement's definition of done, a requirement, a probe, or a Test Adversary gap row. An outcome that the run drops has an exclusion with a reason. | `should`, or `must` when the dropped outcome is the reason the task exists. |

## How to check

- Read the log as the ADP viewer does: H2 headings are sections, and `### [DL-…]` blocks are
  entries with `- **Label:** value` fields.
- For ADP-02 and ADP-09, grep the verbatim anchor or the named identifier at the reviewed head.
  Record the command and its result in **Verification**.
- For ADP-04, list the decisions you see in the diff in your working notes first. Then match each
  one to an entry by its Decision field. Report only the unmatched decisions.
- When the ADP skill's `scripts/adp-index-builder-lib.js` is available, its `lintCorpus`
  advisories (`misplaced`, `control-byte`, `undated-window`) are DIRECT EVIDENCE for ADP-10.

The checks judge the record, not the developer. Write a failed check as a fact about the log and
the code: "DL-004 says the lock lives in Redis, and `src/lock.ts` takes a Postgres advisory lock."
