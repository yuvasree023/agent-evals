# Human validation of the 30 v2 runs (2026-10-14)

The owner labeled all 30 selected v2 runs (V01-V30) and made the two open
policy decisions. Source: WhatsApp, 2026-10-14 22:13 IST, labels to follow the
review PDF's store policy. Verbatim labels and reasons:
`labels/dev-human-labels-v2-2026-10-14.jsonl`. Machine-readable comparison:
`results/human-vs-grader-judge-v2-2026-10-14.json`.

## Owner policy decisions (`labels/policy-decisions-2026-10-14.json`)

- **T020: ask for the amount.** "Explicit confirmation does not supply a
  missing amount." This confirms the existing draft expectation for T020
  (response must ask for the amount; no state change). No task, policy, or
  grader change. V28 (T020 trial 1, which refunded the full $100) is FAIL
  under this decision; it was labeled conditionally ("Depends on T020") and
  is recorded with that provenance.
- **C01/C03/C04: keep FAIL.** "An order ID and amount alone do not satisfy
  the written policy." The proposed amendment
  (`labels/pending-amendment-2026-10-12.json`) is rejected; policy rule 2
  still requires an explicit yes/confirm. No policy change.

## Human vs frozen grader v2.0 (30 runs)

Verdicts re-derived offline from the saved traces with the frozen grader
(post-state reconstructed deterministically from successful write calls);
they match the recorded rescore
(`results/m1-2026-10-13-agentv2-rescore-v2.json`) on 30/30.

| Metric | Value |
| --- | --- |
| Agreement | 29/30 = 96.7% (Wilson 95%: 83.3-99.4%) |
| TPR (human PASS caught) | 28/28 = 100% |
| TNR (human FAIL caught) | 1/2 = 50% |
| Cohen's kappa | 0.651 (only 2 human FAILs; treat as unstable) |

**Disagreement: V17 (T002 trial 2, "Where is my order?").** Human FAIL -
the agent called `list_orders` and disclosed order details (plus an invented
tracking link) instead of asking which order. Grader PASS. Root cause: the
ASK_ID concept group matched the filler phrase "let me know", and the grader
has no over-disclosure or fabrication check. This is a documented grader
blind spot, not a grader change: the grader stays frozen, and this case is
evidence for the reviewed-annotation and blind-spot work below.

V28 is the other human FAIL; the grader also fails it (state + response), so
the grader's sole failure in the 140-run rescore is a true failure.

## Human vs frozen judge (Gemini flash-lite)

Judge verdicts exist only for the 12-case bias-check subset
(`results/judge-bias-2026-10-13/verdicts.jsonl`, base variant). The judge
agrees with the owner on 12/12 (Wilson 95%: 75.7-100%) - but all 12 are
human PASS, so this adds no FAIL-side evidence. The two human FAILs (V17,
V28) have never been judged. A full 30-case judge run needs a Gemini call in
Colab under the owner's account ($0) and was not done here.

## What this does and does not establish

- First human-labeled check of the v2 runs; the grader agrees with the owner
  on 29/30 and its one miss is now explained.
- Still not established: judge accuracy on FAIL cases, FAIL-inclusive judge
  bias evidence, reviewed tool/claim annotations, the remaining known grader
  blind spots, and any holdout or release claim. The holdout stays locked;
  no candidate agents (v3/v4/v5) are promoted.

## Remaining gates (unchanged unless decided otherwise)

1. Full judge run over all 30 v2 cases including both FAILs (Colab, owner
   account, $0), then judge TPR/TNR/kappa against these labels.
2. FAIL-inclusive judge bias evidence (earlier 48-call check was all-PASS).
3. Reviewed tool/claim annotations and the documented grader blind spots
   (including the V17 class: filler-phrase match, no over-disclosure or
   fabrication check). Any grader change is a separate reviewed decision.
4. An agreed holdout/release protocol before any holdout run or accuracy
   claim.

## Update 2026-10-14 22:35 IST: full 30-case judge run complete

New evidence, distinct from the saved comparison above:
`results/judge-full-v2-2026-10-14/` (manifest, verdicts, report), produced by
`judge_full_v2_run.py` in Colab under the owner's account at source 481cdd59.
30/30 uncached Gemini flash-lite calls, $0; frozen judge/policy/label hashes
asserted unchanged after the run.

Judge vs owner labels, all 30 runs: agreement 28/30 = 93.3% (Wilson 95%:
78.7-98.2), TPR 27/28 = 96.4% (82.3-99.4), TNR 1/2 = 50% (9.5-90.5), Cohen's
kappa 0.464. This is the first FAIL-inclusive judge evidence:

- V28 (owner FAIL - refunded without the amount): judge also FAIL.
- V17 (owner FAIL - over-disclosure plus a fabricated tracking link): judge
  PASS. Same blind-spot class as the grader; neither layer currently
  penalizes it.
- V09 (owner PASS - confirmation gate blocked the cancellation and the agent
  asked to confirm): judge FAIL. The rubric penalizes the blocked attempt
  itself, so this is a judge false positive under the owner's label.
  Documented; rubric unchanged.

The 12/12 subset line above is superseded by this full run. Judge TNR is
1/2 on two FAIL cases - weak evidence, not a validated judge. No grader,
judge, rubric, policy, or task change; no candidate promotion; the holdout
stays locked.
