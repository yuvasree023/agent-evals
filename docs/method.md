# Method and roadmap

## Dataset v0.1

50 synthetic draft tasks, 10 per feature. 35 dev / 15 holdout, 3 holdout tasks
per feature. Dimensions: feature, scenario, persona, difficulty. Each task has
an isolated fixture, explicit expected state, and response smoke checks.
Persona tags describe coverage intent; varied persona wording still needs
human review. Policy-question scenarios are not all independent failure modes.
The set is a starting draft, not representative production traffic.

Holdout IDs and canonical JSON hashes are frozen before model development.
The lock verifies membership AND content; initial scenario families do not
cross splits. No intentional dev/holdout paraphrase pairs. Future near-duplicate
checks still need implementation. Do not print holdout failures for tuning,
pick exemplars from them, or use them in judge prompts. Only aggregate release
gate results are used for promotion. A content correction after exposure needs
a documented new untouched holdout, not silent lock regeneration.

Review dev expectations by hand against policy. Do not claim these draft
expectations are human annotations. Authoring a benchmark is distinct from
using its held-out outcomes to optimize a model. The runner passes only input
and environment to the baseline, never expected answers or tags.

## Critique shadowing (Hamel blog)

Review real dev traces with input, full tool calls/results, final response,
DB diff, and policy together. Label pass/fail and write a detailed critique;
no arbitrary numeric scales. Let criteria evolve on dev, then freeze rubric.
Fix obvious errors before a judge. Keep generating dev cases until new failure
modes stop appearing. Every fix gets a permanent regression test.

No domain-expert experience or second-reviewer participation is claimed.
The builder can review this fictional policy; an optional support/ops reviewer
would catch blind spots. Do not contact anyone without a separate decision.

Build a judge later from diverse, human-written critiques, context, and rubric.
Ask for critique before verdict. Tune manually on judge-dev only. Split by
underlying task/family, not individual trials, so judge-test has no sibling
traces in judge-dev. Freeze prompt before reporting judge-test. Do not tune
until judge-test numbers improve. If exposed labels guide changes, retire that
test set and collect a new untouched set. Revalidate after material changes.

Declare failure the positive class: TPR = TP/(TP+FN), TNR = TN/(TN+FP),
precision = TP/(TP+FP), plus Cohen's kappa. TPR/TNR are not precision/recall.
Report class counts and undefined denominators honestly. Check verbosity and
position bias. Slice failures by feature/scenario/persona, then read failures
and open-code root causes. Specialized judges come after evidence of need.

## Milestones still pending

- M0: model/tool loop now wired (2026-10-12); dev expectations still
  unreviewed drafts, so M0 stays open until human review.
- M1: trial machinery and flip-check built (`--trials`, `--flip-check`; the
  second run bypasses the cache because cached responses cannot measure
  noise). A full >=4-trial dev run is not done yet. Full token/cost logging
  and concurrency are still missing.
- M2: first reporting layers added (schema validity, mutation without
  lookup, repeated calls, tool errors, step efficiency). They do not change
  pass/fail. Full state/trajectory graders and tool P/R against reviewed
  expectations are still missing. Current substring checks are smoke tests
  only.
- M3: atomic supported/contradicted/unsupported claims, fabricated entities,
  fabricated actions verified against successful tool effects, not mere calls.
- M4: 100-200 real human-labeled trials, held-out judge validation and bias checks.
- M5: read >=100 failed traces, taxonomy (5-10 categories), counts and examples.
- M6: >=3 gated fixes, dev tuning only, task-cluster bootstrap CIs, paired
  comparison, no category regression, compare deltas with flip rate, charts.
- M7: simulated online traffic, reference-free graders, review queue and alert.

pass^k estimates all k trials succeeding; pass@k estimates at least one.
Resample tasks, not trials. Predeclare task set, trial count, gate thresholds,
and reporting schedule before seeing outcomes. No invented metrics or chart.

## Spend and data licences

All current execution is offline, standard library, zero API cost. Config
refuses API enablement: a provider adapter is not implemented. Before paid
runs, select agent/judge models, approve a hard total cap, record price/version,
reserve worst-case request cost before calls, stop at cap, and cache with model,
prompt, tool schema, policy, and input hashes. Never commit API keys or real
customer traces. `.gitignore` is defence in depth, not a secret scanner.

Fixtures are fictional and contain no external dataset rows. No benchmark
code, brief text, or blog prompt is copied into the runtime. The architecture
uses ideas from the sources below. No third-party dataset is currently used;
check source licences and redistribution terms before importing one. A source
link is not a licence grant. No repository code/data licence selected yet.

## Sources

- https://github.com/rasswanth-lyzr/ship-ai-projects/blob/main/projects/02-agent-evals/BRIEF.md
- https://hamel.dev/blog/posts/llm-judge/
