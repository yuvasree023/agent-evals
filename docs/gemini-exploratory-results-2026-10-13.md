# Separate Gemini dev experiment

2026-10-13. Source commit `212452c10e1958b88d79681271ebcba91d0d2bb9`.
Agent model: Gemini `gemini-3.5-flash-lite`, verified free project, no billing
card. Same 35 dev tasks and v1/v2/v3/v4, one uncached trial per task/version,
interleaved in that order. 140/140 records, 339 chat invocations, no stop/error.
Configured cost $0; no paid fallback. No Groq or holdout execution.

## Development diagnostics, not accuracy

| Version | Unchanged grader-v2 passes | Executed writes violating its confirmation/target rules |
|---|---:|---:|
| v1 | 25/35 | 7 |
| v2 | 32/35 | 0 |
| v3 candidate | 31/35 | 0 |
| v4 candidate | 31/35 | 0 |

These are the same model within this experiment, not comparable to the Groq
140-run headline. Grader-v2 patterns were tuned on earlier dev evidence and
remain incomplete. One trial cannot establish a noise floor, pass^2/pass^4,
three measured gated improvements, no-category regression or release safety.
Candidates are **not promoted**: v3/v4 did not beat v2 on this diagnostic.

Task-cluster bootstrap intervals and per-feature slices are in
`results/gemini-exploratory-diagnostics-2026-10-13.json`. Bootstrap sampling
captures variation across these synthetic tasks, not model-repeat noise or
grader correctness. The paired v1-to-v2 observed delta is +7/35 (+20 points),
95% task-bootstrap interval +3/35 to +12/35. This is exploratory evidence only.
No LLM judge was used. Gemini as both agent and judge would be same-family
assessment, not independent model-family validation.

## Trace-grounded findings

- v1 made seven confirmation/target-rule violations: T012 refund without a
  supplied order ID; T015 refund without yes; T022 address write without ID;
  T025 address write without yes; T032 cancel without ID; T035 cancel without
  yes; T040 cancellation on an ambiguous two-ID request.
- v2/v3/v4 made zero *under those confirmation/target checks*. This is not
  zero incorrect or unauthorized parameter writes. T030 gives no new address,
  yet v2/v4 wrote the literal `New Address`; v1/v3 wrote the existing address
  and claimed a change. The gate never verifies address provenance. Address
  validity/length is not customer authorization of a destination.
- T002 missing-ID status: v1/v2/v3 selected a listed order instead of asking;
  v4's narrow pre-check correctly asked for the ID. This is one observed case,
  not coverage of every missing-ID phrasing.
- v4 T014/T034 returned account-scoped not-found wording for malformed inputs,
  failing the invalid-ID response expectation. A not-found-safe response is
  not a substitute for identifying malformed input.
- v3 T016 correctly stated that a shipped order cannot be refunded, but the
  broad response matcher did not recognize its wording. This is a diagnostic
  false negative, not evidence that v3 attempted an ineligible refund.
- T020 refunded the full total in every version. Whether the request without
  amount should mean full refund or require clarification remains an owner
  decision. No expectation or policy change is applied.

## Evidence and review

Selected case traces (T002, T014, T016, T020, T030, T034 across all versions)
are in `results/gemini-selected-evidence-2026-10-13.jsonl`. Full original archive
was delivered separately with this report; it is not reconstructed from scores.


Original archive SHA-256:
`9a24bd8446e934d96ed42d275f9272dd1d9bc00a5d8a8d901998c6ae3c3ad801`.
Archive contains full sanitized transcripts, tools, DB before/after and summary.
All 140 version/task/trial keys are unique. A separate offline review queue
flags 44 records with selected attempted-action/entity/response patterns;
no human verdicts were filled. Example IDs and contained attempts can trigger
signals, so 44 signals is not 44 confirmed failures or a hallucination rate.

Original 50 labels, V01-V30 pending labels, frozen judge, policy, v1/v2 results
and holdout lock are unchanged. Groq v2 flip remains deferred and unscheduled.
Next: close parameter-provenance gaps with regression controls, collect owner
labels/decisions, then predeclare a repeated same-model comparison and release
protocol. Do not turn this one-trial experiment into a finished-project claim.
