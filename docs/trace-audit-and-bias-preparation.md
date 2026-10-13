# Trace audit inventory and taxonomy exemplars

2026-10-13. 80 saved selected traces inventoried (50 original v1 label-sheet rows, 30 v2 rows). These are not all 118 smoke-failed raw runs. The complete per-failure open-code requirement remains incomplete until original full archives are recovered. No human verdicts assigned or amended.

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

The original taxonomy has reconciled counts for 118 smoke failures, but its raw main/flip archives are not stored in this repo. This selected inventory cannot certify a note for each of those 118 runs. E1/E2/E3 wording/Unicode/expectation categories require their exact failed trials, not replacing them with nearby passing sheet rows. Recover full archives and preserve their recorded hashes before claiming the open-code ledger complete.

## Judge bias preparation

`judge_bias.py` prepares base, reversed-few-shot-order and repeated-answer verbosity variants with fingerprints. It never changes the frozen rubric, trace, customer message or labels. Offline analysis requires actual verdicts for all matched variants and reports verdict flips only. Repeating an answer may itself change perceived quality; this is a stress test, not proof of semantic invariance. No bias result exists until the frozen judge runs on these jobs. Missing labels prevent accuracy validation, not preparation of bias jobs.
