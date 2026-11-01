# Loop state — website-qa-gates

Updated: 2026-11-01 (loop bootstrap). Facts here are the standing state;
when one changes, the PR that changes it updates this file.

## Direction channel

- Tasks: GitHub Issues labeled `jarvis-task` in this repo.
- Reviews and verdicts: PR comments only.
- Merge owner: Jarvis. External Claude opens PRs from `claude/*` branches.

## Decisions in force

- The gate set is the pre-publish standard for the website line; changes
  here propagate to that line's release checklist.

## Acceptance rules

- CI green on the current head before merge.
