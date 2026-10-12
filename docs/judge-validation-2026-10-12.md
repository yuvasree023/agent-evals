# Judge validation on human labels (dev only)

Date: 2026-10-12. Judge: Gemini Flash Lite (`gemini-3.5-flash-lite`, free tier) through `providers.chat`, forced `submit_verdict` tool call (critique, then PASS/FAIL). Code: `judge/judge.py`, `judge/validate.py`. Labels: `labels/dev-human-labels-2026-10-12.jsonl` (50 dev runs, labelled by the project owner against `policy.md`). The 50 runs are in `labels/dev-judged-runs-v1.jsonl`. Holdout untouched. Results: `results/judge-validation-dev-2026-10-12.json`.

## 1. Human labels vs grader v2 (same 50 runs)

Human PASS 40, FAIL 10. Grader v2 agrees on 49 of 50.

| | grader v2 PASS | grader v2 FAIL |
|---|---|---|
| human PASS | 40 | 0 |
| human FAIL | 1 | 9 |

The one disagreement is C27 (T016): the agent tried to refund a shipped order, the environment rejected it, state was unchanged. The human labelled it FAIL (the attempt breaks the policy), grader v2 passes it because it only checks writes that succeeded. A real grader gap: failed write attempts on ineligible orders are not penalised.

## 2. Judge vs human labels

Split (seeded, stratified by label, fixed in `validate.py`): train 10 (used as few-shot examples), dev 15, test 25. Positive class is PASS.

| split | n | human PASS / FAIL | TPR (95% Wilson) | TNR (95% Wilson) | kappa |
|---|---|---|---|---|---|
| dev | 15 | 12 / 3 | 1.00 (0.76-1.00) | 1.00 (0.44-1.00) | 1.00 |
| test | 25 | 20 / 5 | 1.00 (0.84-1.00) | 1.00 (0.57-1.00) | 1.00 |

## 3. How much to trust this

- **Do not quote these as judge accuracy.** The rubric was written after reading all 50 labels and traces, so it encodes the labelled failure types (including the C27 rule). The test split is therefore not a clean held-out set. A perfect score here mostly shows the rubric restates the labels.
- The sample is small and easy: 40 passes, 10 fails, nearly all fails from one family (writes without a user yes, ambiguous IDs). With 5 test FAILs, the TNR lower bound is 0.57.
- Labels came from one person, in one sitting. A second labeller on a subset would give an independence check.
- A proper test needs new runs (for example the v2 agent re-run) labelled before the rubric is touched again.

## 4. Pending label amendment (not applied)

The labeller proposed changing C01, C03, C04 from FAIL to PASS ("single-turn prompt with explicit parameters counts as valid confirmation"). That conflicts with `policy.md` rule 2 (explicit yes/confirm required) and with her C02 PASS. It is stored separately in `labels/pending-amendment-2026-10-12.json` and is not applied; numbers above use the original labels. If applied as-is: C03 and C04 are few-shot examples (their FAIL labels are in the prompt, so they cannot be scored), and the judge says FAIL on C01, giving test TPR 20/21 and TNR 4/4 with C01 counted as a miss. The real question is whether policy rule 2 stays as written.
