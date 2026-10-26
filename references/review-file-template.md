# Review file record grammar

The headings, field labels, table columns, status words, and ledger lines below are record
grammar. Copy them character-exact, arrows and em dashes included. A card view and later factory
stages parse them with the same field reader ADP uses for Decision Log entries
(`parseDLFields` in the ADP skill's `scripts/adp-parser-lib.js`): a `- **Label:** value` line
opens a field, and a continuation line joins the field above it.

The free prose inside a field follows ASD-STE100 under the ADP Base output style. Write it for an
incident reviewer six months out who has no conversation to consult. Nothing points at the chat.

Do not add YAML front matter. The ADP viewer strips front matter and never shows it, so the review
target lives in the `## Review Target` field block, where a reader sees it and the same field
reader parses it.

## The review file

````markdown
# PR Review — PR #<n> round <k> · <task dir>

## Review Target
- **Schema:** adp-pr-review/1
- **Task:** <task dir>
- **Tasks on branch:** <other task dirs, comma-separated> / —
- **Task resolution:** BRANCH NAME / DIFF TOUCHES / LOG REFERENCE / BASE TASK / DEVELOPER ASSERTION — one line naming the evidence
- **Record source:** GIT HEAD / WORKING TREE
- **Mode:** PR / LOCAL
- **PR:** #<n> <url> / —
- **Branch:** <head branch> → <base branch>
- **Head:** <full head SHA>
- **Base:** <full base or merge-base SHA>
- **Round:** <k>
- **Previous round:** <file name of round k-1> / —
- **Date:** <YYYY-MM-DD>

## Inspected
| Item | Value |
|------|-------|
| Changed files | <count>: `path`, `path`, … |
| Audit log | `.adp/<task>/audit-log.md`, phases present <list>, DL entries <count> |
| Prompt | `.adp/<task>/prompt.yaml` / — |
| Prior review files | <file names> / — |
| Guidance | <files read> / — |
| Memory bank | <slices read> / — |
| Quality profile | `.adp/pr-review-quality.yaml` <id> v<version> / — |
| Prior PR comments considered | <count> / — |
| Tests | `<command>`: <p> pass, <f> fail, <s> skip / NOT RUN — <reason> / NOT RUN — docs only: <files>. <grep commands> found no reader. |

## Findings

### [PR-<CAT>-<NNN>] <short title>
- **Supersedes:** [PR-XXX-NNN when this finding replaces one from an earlier round; omit the line otherwise]
- **Severity:** must / should / question / nit
- **Category:** <CAT> — <category name>
- **Location:** `<path>:<line>` (RIGHT / LEFT), comma-separated when several / `<path>` / —
- **Claim:** <one sentence that states the defect>
- **Evidence:** <what you read or ran, with a verbatim anchor from the code or the command and its output>
- **Failure scenario:** <concrete inputs or state, and the wrong outcome they produce>
- **Suggested fix:** <the fix contract: each post-fix obligation and the verification that proves it>
- **Confidence:** HIGH / MEDIUM / LOW
- **Confidence basis:** DIRECT EVIDENCE / INFERENCE FROM CONVENTION / DEVELOPER ASSERTION — one line naming the evidence, the convention, or who asserted what
- **Verification:** <the grep, read, or repro that confirmed the claim, and its result>
- **Criterion:** <quality profile id, guidance rule, ADP check id, or general criterion>
- **Refs:** <DL-XXX, Pre-Mortem failure-mode text in quotes, OT-XXX-n, prior comment URL> / —
- **Later record:** [a log section written after the head that answers part of this finding, and the part it leaves open; omit the line otherwise]
- **Created:** <YYYY-MM-DD>, round <k>
- **Status:** OPEN

[repeat per finding; write "No findings." as the only line when there are none]

## Quality Coverage
| Criterion | Changed surface | Evidence checked |
|-----------|-----------------|------------------|
| ...       | ...             | ...              |

## Developer Responses
| Finding | Response | Outcome |
|---------|----------|---------|
| PR-<CAT>-<NNN> | <the RESPONSE text, verbatim> | REFUTED / SUPERSEDED by PR-<CAT>-<NNN> / CARRIED — <the reason> |

[omit the section in round 1, which records each clause in `## Notes`, and when the round received no RESPONSE clause]

## Prior Findings
- **PR-<CAT>-<NNN> CLOSED <YYYY-MM-DD> → RESOLVED.** <what in the current head resolves it>
- **PR-<CAT>-<NNN> CLOSED <YYYY-MM-DD> → REFUTED.** <the evidence that shows the claim was wrong>
- **PR-<CAT>-<NNN> CLOSED <YYYY-MM-DD> → ACCEPTED.** <who accepted the risk, and where that is recorded>

[omit the section in round 1]

## Suppressed Prior Comments
| Source | Reason |
|--------|--------|
| <comment URL or reviewer and date> | <why repeating it adds nothing> |

[omit the section when nothing was suppressed]

## Notes
- <a review limitation, an unavailable material, or a boundary you considered and cleared>

## Review Verdict
- **Verdict:** REQUEST_CHANGES / COMMENT / APPROVE
- **Confidence:** HIGH / MEDIUM / LOW
- **Confidence basis:** DIRECT EVIDENCE / INFERENCE FROM CONVENTION / DEVELOPER ASSERTION — one line naming what the review covered and what it could not
- **Counts:** must <n> / should <n> / question <n> / nit <n>
- **Opened:** <finding ids opened this round> / —
- **Closed:** <finding ids closed this round> / —
- **Carried open:** <OPEN finding ids from earlier rounds> / —
- **Needs developer:** <OPEN finding ids only the developer can settle> / —
- **Summary:** <the same 250-character summary the terminal prints>
````

### Field rules

- A finding entry is immutable once written. Only a ledger line under `## Prior Findings` of a
  later round, or under the audit-log pointer, changes its disposition. A changed claim is a new
  finding whose **Supersedes** field names the old id, and the old id closes as `REFUTED`.
- Gate notes, tables, and code blocks go before the first `###` entry of `## Findings`, never
  inside an entry. Within an entry, nothing follows the fields.
- **Location** uses the diff side ADP and GitHub both understand: `RIGHT` for the head, `LEFT` for
  the base. A cross-file or non-line finding gives paths only, or `—`.
- **Evidence** quotes the code exactly in a code span. A line number is an advisory hint, as in
  ADP's `Implemented at` column.
- **Refs** quotes Pre-Mortem failure-mode text verbatim, so a reader can search for it.
- `## Notes` holds only what no other section records. A Notes line never repeats an `## Inspected`
  row, a `## Quality Coverage` row, or a finding. Notes keeps: a review limitation, an unavailable
  material, a boundary you cleared that no Quality Coverage row names, a candidate that a later
  record resolves, an acceptance that names no person, a RESPONSE clause that names no OPEN
  finding or that arrives in round 1, a missing test command, and each docs-only grep hit outside
  a candidate with its class.
- **Counts** in the Review Verdict counts the findings OPEN after this round: the round's new
  findings plus the findings it carries open. See `finding-conventions.md` § "Verdict".

## The ledger lines

The forms copy ADP's Phase 9 ledger grammar. The outcome word is the finding's terminal status.

```
- **<PR-ID> CLOSED <YYYY-MM-DD> → <RESOLVED|REFUTED|ACCEPTED>.** <closing note>
```

The ADP index harvests only `OT-` and `DL-` ids today, so it reads these lines as prose. They are
still character-exact, so a later additive `adp-index/1` field can harvest them without a rewrite.

## The audit-log pointer

Append one section to `.adp/<task>/audit-log.md` per review round. It goes after the last section
of the log, because ADP places every `review`-kind section after the chain in event order.

```markdown
## Review findings — PR #<n> round <k> (<YYYY-MM-DD>)
- **Review file:** `.adp/<task>/<review file name>`
- **Verdict:** REQUEST_CHANGES / COMMENT / APPROVE
- **Counts:** must <n> / should <n> / question <n> / nit <n>
- **Opened:** <finding ids> / —
- **Closed:** <finding ids> / —
- **Head:** <full head SHA>
```

In branch mode, write `## Review findings — local round <k> (<YYYY-MM-DD>)`.

The pointer carries no finding prose. The review file is the system of record for the review.
