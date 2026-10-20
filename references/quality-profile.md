# Quality profile

A quality profile gives the reviewer repository-specific criteria that general review knowledge
does not cover. The profile is optional. Without it, the review uses the guidance files, the ADP
checks, and general review obligations.

## Location

`.adp/pr-review-quality.yaml` at the project root. The file sits at the `.adp/` root on purpose:
the ADP index treats every subdirectory of `.adp/` as a ticket and ignores root files.

## Shape

```yaml
id: repository-code-quality
version: 1
review_dimensions:
  - id: correctness
    required: true
    pass: Changed behavior satisfies the requested outcome and preserves existing behavior in touched paths.
project_rules:
  - id: api-error-contract
    category: CON
    evidence: src/http/errors.ts, docs/api.md
    pass: API handlers return the standard error envelope, and clients parse it through the shared client utilities.
documentation_paths:
  - site/
  - notes/*.txt
```

- `pass` states the accepted state as a positive sentence. A reviewer checks the code against it.
- `category` is the finding category a failure of the rule takes. It is optional.
- `evidence` names the file, test, CI job, or developer decision that makes the rule true for this
  repository. A rule without evidence is general advice, and general advice does not belong here.
- `documentation_paths` adds paths to the docs-only candidates in
  `references/finding-conventions.md` § Docs only. It is optional. A listed path still needs the
  reader grep, and it never makes an agent-read file into docs.

## Authoring a profile

Write or change a profile only when the developer asks for it.

1. Read the repository first: CI workflows, tests, schemas, guidance files, the memory bank, and
   the ADP corpus's Decision Log entries that set conventions.
2. Propose the profile before you write it. Give each rule with its evidence, and name each
   generic rule you left out with the reason.
3. Ask one question: write the proposal, or change it.
4. Write the file after the developer confirms.

Good rules name a concrete contract and the evidence to inspect. "Code is clean and secure" is not
a rule.
