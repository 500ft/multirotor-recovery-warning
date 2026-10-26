# Agent instructions

## Scope discipline — owner rule, 2026-09-29

This repository exists to be finished. A PR must do at least one of these:
add a measurement or an executed run, change a result, close an item on the
critical path below, or record an owner decision. If it does none, don't open it.

- **No plan-only PRs.** A plan belongs in the PR that implements it, or in a
  `.txt` handoff outside the repo. Never open a PR that supersedes another plan
  PR; edit the open one.
- **One home per number.** A consequential number lives in one source file (a
  results JSON or the parameter register). The README and manuscript may quote
  headline numbers; other documents link to the source instead of restating
  them. If a correction would need edits in more than one document, replace the
  copies with links first.
- **No hardening before first use.** Don't add or extend intake, manifest,
  contract or provenance checkers for data that doesn't exist yet. Build a
  checker in the same PR as the first real data it checks. A fix to a fix
  (`-b`, `-c`) is the signal to stop.
- **No cross-repo template passes.** Don't apply a change here because it was
  applied to a sibling repository (literature reviews, presentation passes,
  audits, traceability indexes) unless this repo's critical path needs it.
- **When blocked on the owner, say so in one line and stop.** Don't fill the wait
  with documents.
- Dependency updates arrive as Dependabot's grouped monthly PRs; don't hand-edit
  pins to chase them.

**Plan:** [ROADMAP.md](ROADMAP.md) is the only plan. It holds the finish line,
the current step and what is left. Update it in the same PR as any change to
those. `docs/SPRINT_PROGRESS.md` and `docs/REVIEW_READY.md` are history logs,
not plans; don't add status there that belongs in the roadmap.


## Writing — owner rule, 2026-09-30

The owner finds much of this repository's text reads as machine-written. New
and edited text should read like an engineer wrote it for another engineer.

- Lead with the result or the action and its number. Context comes after.
- State each limitation once, where limits are discussed. Don't hang a
  "this does not establish…" clause on every sentence.
- Avoid "X, not Y" and "not X but Y" framings unless the contrast is the point.
- Skip filler and house jargon: honest(ly), robust, comprehensive, crucial,
  leverage, fail-closed, canonical, bounded, evidence boundary, source-linked,
  defensible, "it is worth noting".
- Short sentences, active voice, plain words. Bold at most one term per
  section. Don't chain clauses with em dashes.
- Keep dates and changelog entries out of README and roadmap prose unless the
  date matters to the reader. History belongs in git and the progress log.
- In public research summaries, name the question, observed result and next
  evidence needed. Keep permission restrictions explicit in operational guidance,
  but avoid narrating internal handoffs in every result paragraph.
