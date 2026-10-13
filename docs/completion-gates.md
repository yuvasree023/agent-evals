# Completion gates and remaining evidence

Updated 2026-10-13. The owner asked to finish project work using free Gemini
where it fits, leaving Groq-dependent steps for later. Groq execution is now
deferred, not automatically scheduled.

## Implemented preparation

- Versioned v1/v2 measured history; unpromoted v3/v4 candidates.
- Offline state, confirmation, eligibility, attempted-action and selected
  response/entity checks with scripted positive/negative controls.
- `eval_quality.py`: schema argument types/required fields, order-ID provenance
  using only prior evidence, separate attempted-action/response-pattern signals,
  per-feature breakdown, equal-task bootstrap intervals, finite-n reliability
  estimators, matched observed-task deltas, and a deduplicated JSONL review queue.
- Queue records have `human_verdict: null`. A diagnostic never becomes a human
  label. Regex signal rates are not a general hallucination rate.
- Separate `gemini-dev-comparison.ipynb`: Gemini 3.5 Flash Lite, 35 dev tasks x
  v1/v2/v3/v4 x one uncached trial, interleaved, capped at 400 requests. This is
  exploratory quota-bounded evidence, not the four-trial M1 protocol.

## Reproduce offline

```
python3 -m unittest discover -s tests -v
python3 run.py --validate
python3 online_eval.py --scenario baseline
python3 online_eval.py --scenario drift
python3 eval_quality.py <gemini-traces.jsonl> --report <report.json> --queue <review.jsonl>
```

The diagnostics command requires real saved dev traces with explicit unchanged
`grader_v2` checks, unique version/task/trial keys and a single model/provider.
It refuses mixed-model comparisons and holdout rows. A partial comparison
reports the actual paired task set. With one trial, k=2/4 are undefined, not 0.
Task-bootstrap intervals are exploratory on synthetic task clusters; they do
not remove grader bias or turn a small task set into production evidence.

## Before candidate promotion

No candidate is promoted by unit tests or the exploratory Gemini run. Freeze
this gate before looking at any release outcomes:

1. Complete same-model dev comparisons with four fresh trials and uncached
   flip checks; report paired task-cluster intervals and feature deltas.
2. Zero executed unconfirmed/ambiguous writes and no response claiming a write
   succeeded without a successful effect. Every new failure gets a regression.
3. No feature loses more than 5 percentage points on the predeclared metric.
   For overall gain, paired 95% task-bootstrap interval must exclude zero and
   observed gain must exceed that experiment's complete uncached flip rate.
4. Explicit owner review of draft expectations and remaining policy questions.
5. A separately predeclared, aggregate-only untouched-holdout release gate.
   Current runner still blocks model holdout runs. Do not execute it until the
   release protocol and authority are settled, never use outcomes for tuning.

These thresholds are proposed project release gates, not retroactive evidence
that a version already passed them. At present, none of v3/v4 is promoted.

## Waiting on human evidence

- V01-V30 labels; do not tune the frozen judge before testing against these.
- T020: does a confirmed refund with no amount mean full refund or ask amount?
- C01/C03/C04: keep current explicit-yes rule or revise policy consistently?
- 100-200 real owner-labelled trials/per-claim support annotations and independent
  judge bias tests. Original 50 labels remain unchanged. Gemini as both agent
  and judge is same-family assessment, not independent model-family validation.

## Deferred or incomplete

- Groq v2 flip: 42/70 recorded previously; a complete fresh check is deferred.
- No three measured gated iterations or holdout improvement chart exists.
- Full atomic claim segmentation/NLI support judging, real tool precision/recall
  references, embedding-based dataset deduplication, per-failure open-code notes
  with two linked examples per taxonomy category remain incomplete.
- Review queue persists as a JSONL file, not a production annotation service.
- Sequential pacing replaces parallel execution under free quotas; no billing
  card, paid compute, quota-bypass account or paid fallback is allowed.

Do not call the portfolio project complete while these evidence requirements
remain open. Describe implemented code separately from measured/validated work.
