# Development regression supplement v0.2

2026-10-13. Twelve author-created synthetic scripted regressions turn known
v1/v2 failure families into permanent candidate path controls. They supplement
v0.1, never replace its 50 tasks or 15 frozen holdout rows.

Run:

```
python3 regression_suite.py --out results/regression-offline-2026-10-13.json
```

No provider is called. Each case scripts model tool proposals and checks candidate
state, gate errors and selected final-answer properties. This proves those tested
paths, not that a live model selects the right calls. The report is explicitly
scripted/offline and must not enter a model-improvement chart.

| Cases | Controls |
|---|---|
| R001-R004 | shipped refund, day-31 refund, over-total and negative amount |
| R005 | confirmed delivered day-30 positive refund |
| R006-R007 | negated confirmation and ambiguous cancel target |
| R008 | confirmed pending cancellation positive control |
| R009 | shipped address change blocked |
| R010 | missing-ID status clarification |
| R011 | unsupported transit/arrival statement replaced by observed status |
| R012 | account-scoped not-found wording |

`evals/regressions-v0.2.jsonl` includes source family, dataset version, candidate,
input, fixture, scripted tool proposals and explicit test expectations. The
loader enforces development-only scope, unique IDs and exact-content dedup.
Embedding/paraphrase dedup is not implemented. None of these expectations is an
owner's annotation; T020 amount semantics and C01/C03/C04 remain unanswered.

Selected shipping/entity regex checks remain narrow. Real tracking timestamps
are not modeled; the fixture supplies no such evidence. Live candidate runs,
independent human validation, model noise and release gates remain separate.
