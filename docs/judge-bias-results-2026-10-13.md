# Frozen-judge bias experiment results

2026-10-13. Separate experiment per the predeclared [protocol](judge-bias-protocol-2026-10-13.md). Source commit 918df70; 48/48 planned uncached free Gemini 3.5 Flash Lite verdict calls completed on 12 selected Groq-generated v2 dev traces; 4 variants per case (base, base repeat, reversed few-shot order, answer repeated 3x). $0, no Groq execution, no holdout, no label/rubric changes. Frozen file SHA-256 hashes for judge/judge.py, judge/validate.py, policy.md and the original human label file were verified identical before and after the run. Machine records: [manifest](../results/judge-bias-2026-10-13/manifest.json), [report](../results/judge-bias-2026-10-13/report.json), [verdicts](../results/judge-bias-2026-10-13/verdicts.jsonl) (prompt hashes, critiques, usage).

## Headline result and why it is weak

Zero verdict flips in all three comparisons (base repeat 0/12, reversed examples 0/12, verbose repeat 0/12).

This does not show the judge is unbiased. The judge returned PASS on all 48 calls, including the unchanged base verdict for every one of the 12 cases. On an all-PASS subset there was little room for a flip to be visible, and 12 cases with one repeat control cannot separate "no sensitivity" from "test too small or subset too easy". Treat this as consistency observed on a narrow all-PASS slice, not evidence of position or verbosity robustness.

## Other caveats

- These v2 traces have no human labels; no accuracy was or could be computed. PASS here is only the frozen judge's output.
- The rubric was written after seeing the old v1 labels, so historical contamination noted in judge-validation-2026-10-12 still stands.
- Groq-generated traces judged by Gemini avoids same-family generation in this experiment only; it does not make the judge independently validated.
- Answer repetition can change perceived quality; verbosity results are not semantic-invariance proof.
- Raw model responses are preserved in verdicts.jsonl for audit.

## What would strengthen this

A variant subset containing cases where the base verdict is FAIL (requires new labelled traces, i.e. the V01-V30 label gate), more cases, and more repeats per variant to bound stochastic flip rates. These remain gated on human labeling.
