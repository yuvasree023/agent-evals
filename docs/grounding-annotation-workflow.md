# Tool references and atomic claim-support annotations

2026-10-13. Offline preparation only. `grounding_eval.py` creates fingerprinted blank annotations and scores supplied reviewed annotations. It does not invent references, divide an answer into claims automatically, call an NLI model, or assign support labels. Frozen judge and original human labels stay unchanged.

## Tool reference rules

A reviewer records one or more acceptable tool-call sequences for the exact supplied trace scope. Each call includes its name and complete arguments. The scorer compares multisets of name/argument pairs and reports precision/recall. Duplicate calls consume matches; argument differences do not match. Empty actual/reference sets score 1 only when both are empty. With several reviewed acceptable alternatives, the best F1 is used (recall then precision breaks ties).

This is call selection measurement, not sequence/order correctness. A repeated or unsafe write cannot be declared safe by high call precision. The existing trajectory/state/confirmation checks stay separate. Reference sequences must come from policy and reviewer intent, not be copied from the agent's trace to make its score high.

The 80-row template binds the 50 v1 and 30 v2 label-sheet evidence records. Those sheets omit repeated policy/model-envelope material and are not the full original run traces. Thus references for this template must use that same sheet scope; never call its metric whole-run tool precision. To measure all actual calls, use the full recovered raw archive with unique case keys such as `main:T015:1` and regenerate fingerprints. Trimmed failure-ledger records are explicitly refused for scoring.

## Claim annotation rules

A reviewer splits factual answer content into atomic claims. Each claim has a unique ID, exact answer substring and zero-based start/end positions (end exclusive), support value, reason and evidence pointers. Pointers name `input`, the unchanged `policy`, or `trace:N` for the zero-based call index in the supplied evidence.

Supported claims require a valid pointer. Unsupported claims have a reason that identifies missing or contradictory evidence. Unknown means the reviewer has not established support either way. The report shows both all-claim and known-claim support rates and review coverage; unknowns never silently become supported. A reviewer's name is required, but the program cannot authenticate a reviewer or prove that a claim split is complete. Annotation coverage and atomicity need review outside this syntax check. This is annotated-claim support, not a general hallucination rate.

## Reproduce

```
python3 grounding_eval.py labels/dev-judged-runs-v1.jsonl --blank --out blank.jsonl
python3 grounding_eval.py evidence.jsonl --annotations reviewed.jsonl --out report.json
```

`results/grounding-annotation-template-2026-10-13.jsonl` has all fields requiring judgment blank. Its 80 source records are the concatenation of the v1 and v2 label sheets. For scoring that combined template, concatenate those exact sheets into evidence.jsonl first. Exact case coverage, evidence fingerprints, reviewed reference alternatives and reviewed claim spans are required. Blank templates cannot produce a score. This finishes annotation/scoring plumbing, not real references, atomic segmentation/NLI validation, or the 100-200 human-label requirement.
