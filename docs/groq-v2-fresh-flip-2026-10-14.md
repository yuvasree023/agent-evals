# Fresh Groq v2 flip check: 2026-10-14

35 draft dev tasks x two fresh uncached trials, 70 unique graded records,
35 complete pairs, zero provider errors, $0 on free Groq and Colab CPU.
No historical partial records were appended or pooled. No holdout model runs.

| Grader | Passes | Verdict flips |
|---|---:|---:|
| Unchanged grader v2.0 | 70/70 | 0/35 |
| Original literal-wording smoke grader | 29/70 | 3/35 (T002, T004, T034) |

These are different graders, not conflicting runs. Grader v2.0 was tuned using
v1 development traces and has known blind spots. Zero flips in 35 synthetic
pairs is a small development diagnostic, not proof of general reliability,
human-validated accuracy, absence of hallucinations, or a release gate.
All 70 narrow policy checks pass, with zero executed confirmation/target
violations under that checker. Rejected forbidden attempts, unsupported claims,
missing-ID answers and wrong parameter provenance still need separate review.

The historical main run was not repeated: exact recovered 140-run traces
rescore to 139/140 using unchanged grader v2.0, 60/140 using original smoke,
and 140/140 narrow policy checks. Its trace SHA-256 remains
`8d617d6ff0d8ef325d0a8928e5bdc38877fc00c3df29a3ab03be6499284f1a68`.
Old 42-graded/28-error flip evidence stays historical and separate.
V01-V30 labels, T020 amount semantics and C01/C03/C04 policy decisions remain
open. No human labels, frozen judge, policy or candidate promotion changed.

## Reproduce and inspect

- `groq-v2-fresh-flip.ipynb` pins source commit
  `3ad211c78086874cde91307abeeaa6ab9c34cfa3` and uses official Groq SDK defaults.
- Only provider transport is patched in the Colab checkout; sampling, v2,
  tasks, grader and policy are unchanged. Manifest lists protected hashes.
- Saved Drive execution:
  https://colab.research.google.com/drive/1JATEDjTv1ENb3FgFx72lOsplOa_jaTeT
- Full fresh archive: `results/groq-v2-flip-2026-10-14/archive.base64`.
  It contains exact traces, checkpoint, original smoke report and manifest.
  Decode with `python3 -m base64 -d archive.base64 > fresh-results.zip`.
  Verify the ZIP SHA-256 against `manifest.json` before extraction.
- `rescore-v2.json` stores fresh flip per-run checks plus the historical main
  summary and a reference to its original per-run score file, keeping the
  two experiments separate. Reproduce with `rescore.py` using
  the actual historical main trace plus the new flip trace, never reconstructed
  score-only records. Keys are absent from all files.

91 offline tests and unchanged holdout hashes passed before execution.
Colab runtime was disconnected and deleted after archive verification.
No more runs are scheduled.
