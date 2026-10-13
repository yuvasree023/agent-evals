# Trace audit inventory and taxonomy exemplars

2026-10-13. 80 saved selected traces inventoried (50 original v1 label-sheet rows, 30 v2 rows). These are not all 118 smoke-failed raw runs. The selected inventory is now supplemented by the [hash-verified full 118-failure ledger](m1-per-failure-audit-2026-10-13.md). No human verdicts assigned or amended.

Machine inventory: `results/trace-audit-inventory-2026-10-13.jsonl`. Each row binds case, source file, main/flip source, task/trial, actual write effects, rejected attempts and verbatim answer. Matching task IDs across main/flip are not the same run.

## Source-recoverable exemplars

### A1 confirmation

- C01, main T015 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C01`. Successful writes: 1; rejected attempts: [].
- C02, main T015 trial 2: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C02`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

### A2 ambiguous target

- C09, main T040 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C09`. Successful writes: 1; rejected attempts: [].
- C10, main T040 trial 2: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C10`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

### A3 eligibility attempt

- C27, main T016 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C27`. Successful writes: 0; rejected attempts: ['refund_ineligible'].
- V25, main T016 trial 1: source [v2 traces](../labels/dev-judged-runs-v2.jsonl), case key `V25`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

### A4 missing identifier

- C18, main T002 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C18`. Successful writes: 0; rejected attempts: [].
- V16, main T002 trial 1: source [v2 traces](../labels/dev-judged-runs-v2.jsonl), case key `V16`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

### A5 ownership-scoped wording

- C28, main T018 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C28`. Successful writes: 0; rejected attempts: [].
- V21, main T018 trial 1: source [v2 traces](../labels/dev-judged-runs-v2.jsonl), case key `V21`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

### A6 shipping evidence

- C17, main T001 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C17`. Successful writes: 0; rejected attempts: [].
- C23, main T010 trial 1: source [v1 traces](../labels/dev-judged-runs-v1.jsonl), case key `C23`. Successful writes: 0; rejected attempts: [].

These are fitting trace examples, not two independently confirmed failures. Refer to the taxonomy's exact failure task/trials before attributing a cause.

## Remaining failure-analysis evidence

Original main/flip archives were recovered from saved notebook output on 2026-10-13. Their raw trace hashes match the historical taxonomy. The full ledger now records all 118 failures; these nearby selected sheet rows remain examples/contrasts only and are not a substitute for exact failed runs. A3/A5/A6 contain just one primary-category failure each, so no second failure was invented.

## Judge bias preparation

`judge_bias.py` prepares base, reversed-few-shot-order and repeated-answer verbosity variants with fingerprints. It never changes the frozen rubric, trace, customer message or labels. Offline analysis requires actual verdicts for all matched variants and reports verdict flips only. Repeating an answer may itself change perceived quality; this is a stress test, not proof of semantic invariance. The [separate 48-call experiment](judge-bias-results-2026-10-13.md) is now complete: zero flips on an all-PASS subset, not evidence of no bias. A [FAIL-inclusive follow-up template](judge-bias-followup-template.json) is recorded without selected cases or calls until original labels arrive. Missing labels prevent accuracy validation, not preparation of bias jobs.
