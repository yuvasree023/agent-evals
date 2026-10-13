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

## Milestone status (2026-10-13)

- M0: environment, model loop, 50 tasks and 35/15 hash lock exist. Human review
  of all dev expectations remains incomplete. T020 amount semantics are open.
- M1: v1 main and flip are recorded; v2 main has 140 runs, flip only 42/70.
  A fresh 70-run v2 flip check is planned after quota reset. Runs are sequential
  for free-tier pacing, not parallel. No candidate-v3/v4 model results exist.
- M2: state, response and policy graders and reporting layers exist. Grader v2
  has documented blind spots. New candidate diagnostics inspect attempts,
  including rejected writes, but do not replace old scores. Comprehensive tool
  precision/recall and full schema validation remain open.
- M3: narrow deterministic response checks are prepared for invented order IDs,
  action claims, global nonexistence and shipping statements. Full atomic-claim
  support labels/NLI and validated hallucination rates remain open.
- M4: 50 owner labels and a judge validation report exist. Rubric saw these
  labels; small test failure class means this is not proven general accuracy.
  The fresh 30-case v2 set awaits owner labels. Frozen judge is unchanged;
  100-200 labels and independent per-claim/bias testing remain incomplete.
- M5: taxonomy reviews 118 smoke-failed v1 main/flip runs with reconciled counts.
  Open-coded note per failed trace and two clickable exemplars per category
  remain incomplete. See failure-taxonomy.md for actual scope and overlaps.
- M6: one measured confirmation-gate fix; rounds 2/3 are unpromoted offline
  candidates. Three measured gated iterations, task-cluster bootstrap CIs,
  category non-regression gates and untouched-holdout chart remain open.
- M7: simulated online eval, sampling, Wilson intervals and alert demo exist.
  Real traffic integration and a persistent annotation queue are not built.

## Next experiment and gates

First finish v2 flip with unchanged code/model/grader. Then collect owner V01-V30
labels and test the unchanged judge before tuning it. Neither T020 nor pending
C01/C03/C04 labels may be resolved by code changes. Candidate v3 adds observed-
state eligibility checks; v4 adds clarification and narrow response grounding.
Offline scripted tests are preparation, not evidence of model improvement.

For candidate live comparisons, use the same 35 dev tasks, four independent
trials and two uncached flip trials, same Groq model, isolated versioned outputs.
Report old grader-v2 diagnostics alongside new per-family attempt/claim signals,
never rename a new grader score as improvement over old scoring. Treat task
repetitions as clustered, not independent samples. Do not promote on unit tests.
Freeze meaningful thresholds before release-gate outcomes. No holdout execution
or holdout-driven tuning is authorized in the current dev workflow.

pass^k means all k trials succeeding; pass@k means at least one. A complete
uncached paired protocol is needed before either reliability claim is made.

## Spend and data licences

Offline tests require no network or model calls. Live adapters support free
Groq/Gemini plans, configured for $0 with no billing card. Provider/model is
unchanged. Keys stay out of the repository. A quota reset must be verified by
current provider response; a schedule is not proof of availability. Free-tier
settings and zero-spend guards are not an unlimited-quota guarantee.

Fixtures are fictional; no real customer data or external dataset rows are
included. Source links are not licence grants. No repository licence was
selected, by the owner's choice. Do not import third-party code/data without
checking redistribution terms.

## Sources

- https://github.com/rasswanth-lyzr/ship-ai-projects/blob/main/projects/02-agent-evals/BRIEF.md
- https://hamel.dev/blog/posts/llm-judge/
