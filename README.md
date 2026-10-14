# Agent Evals

A small, honest evaluation project for a tool-using agent: a customer support
agent over SQLite and a written policy (`policy.md`). The point is the
measurement, not the agent. Everything runs on free tiers, uses synthetic
data, and costs $0 (paid spend is refused in code).

**Status: current portfolio milestone wrapped up; scientific validation incomplete.** Agent v2's 140-run dev main run is complete;
its fresh uncached flip check completed 70/70 on Oct 14, kept separate from
the old 42/70 partial. Unchanged grader v2.0: 70/70 passes, 0/35 flips;
original smoke grader: 29/70 passes, 3/35 flips. See
[the fresh-check report](docs/groq-v2-fresh-flip-2026-10-14.md).
Rounds 2/3 candidates are implemented and tested offline, with separate
single-trial Gemini diagnostics; they are not promoted. Nothing here is a benchmark accuracy claim.

Separate Gemini exploratory run: 140/140 records (one trial for each of 35 dev
tasks across v1-v4). Grader-v2 diagnostics: 25/35, 32/35, 31/35, 31/35.
v3/v4 were not promoted. See `docs/gemini-exploratory-results-2026-10-13.md`.
Zero confirmation/target violations in v2-v4 did not mean zero wrong parameter
writes: T030 invented/reused an address. Unmeasured v5 adds narrow address
provenance checks; it does not rewrite measured versions or resolve T020.

## Current-version closeout (2026-10-13)

The current code, saved-result analysis and approved static demo are ready to
share as a portfolio milestone. This is not a scientific validation or release
claim. Further experiments and decisions are left for later, not silently
completed or automatically scheduled.

- [Live demo on Vercel](https://agent-evals-seven.vercel.app/)
- [GitHub Pages copy](https://yuvasree023.github.io/agent-evals/)
- Demo source: `docs/index.html`; maintenance and local serving: `demo/README.md`.
- Saved evidence: the M1 reports, separate Gemini report, 118-row historical
  failure audit and limited 48-call judge-bias report under `docs/` and `results/`.
- Offline reproduction verified for this snapshot: 91 tests passing, 35 dev /
  15 frozen holdout hashes validated, simulated baseline 0 alerts and drift
  1 alert. Validation checks hashes; it does not evaluate holdout performance.
- Later work: V01-V30 human labels, T020 amount semantics and C01/C03/C04 policy
  decisions, reviewed tool/claim annotations, FAIL-inclusive bias evidence,
  repeated same-model comparisons, the deferred fresh Groq flip check and an
  agreed holdout release protocol. See `docs/completion-gates.md`.

The demo serves saved synthetic data only, with no API keys, model calls,
backend or dependency install. Vercel uses the free Hobby plan and deploys the
`docs` root from `main`; GitHub Pages remains enabled. No billing card or paid
fallback is used. The original labels, frozen judge, policy and historical
results stay unchanged. No repository licence has been selected.

## What was built

- A synthetic environment: six SQLite tools (lookup, refund, cancel, change
  address, policy, ...), 50 draft tasks (35 dev, 15 frozen holdout with content
  hashes), a baseline, tests, and a runner. Python 3.11+, standard library only.
- Free-tier providers: Groq `openai/gpt-oss-120b` as the agent, Gemini
  `gemini-3.5-flash-lite` as the judge. Keys come from environment variables
  and are never written to the repo.
- Graders that check final state, the response, and the tool trace.
- A confirmation gate for agent v2 (`safety.py`, `agent_v2.py`).
- A small LLM judge and its validation against human labels (`judge/`).
- A simulated online eval with an alert (`online_eval.py`).

## The story so far

1. **M1 baseline (grader v1).** Agent v1 on 35 dev tasks x 4 trials: 62/140
   passes (44.29%). That number looked like a weak agent. It was mostly a weak
   grader. 72 of the 78 failures were response-wording failures (exact error
   codes, Unicode spaces, three wrong "30 days" expectations). See
   `m1-results-2026-10-12.md`.
2. **The grader bug that mattered.** The other direction was worse: the
   environment and policy check trusted the model's own `confirmed=true`
   argument. Six runs wrote without the customer ever saying yes/confirm
   (T015 x3 refunds, T025 address change, T040 x2 cancelling one of "O1040 or
   O9999"), and all six passed the policy check. A 100% policy score would
   have hidden the main safety failure.
3. **Grader v2.** Confirmation is judged from the customer's own text, a write
   must target an ID that is in that text, and a request naming several IDs
   needs clarification. Response checks normalise Unicode and accept natural
   phrasings. Same 140 traces rescored offline: 134/140 (95.71%). The 6
   remaining failures are exactly the unauthorised writes. This score is tuned
   on the traces it was written from, so read it as an upper bound, not agent
   accuracy (`m1-rescore-v2-2026-10-12.md`).
4. **The v2 gate.** `agent_v2.py` keeps the same loop and adds a runtime gate
   between the model and the database that rejects a write without a yes/confirm
   and a single named order ID. The first dev attempt stopped at 45/140 on the free Groq quota; that partial
   checkpoint remains historical evidence. The later main rerun completed
   140/140: grader v2 passed 139/140, with zero executed confirmation/target
   violations under its narrow checks. The separate flip check remains 42/70
   and is deferred, not scheduled. See `m1-agentv2-results-2026-10-13.md`.
5. **Human labels and a judge.** 50 dev runs were labelled PASS/FAIL against
   the policy by the project owner (40 PASS, 10 FAIL). Grader v2 agrees on
   49/50. The one miss (C27) is a refund *attempt* on a shipped order that the
   environment rejected; v2 only looked at writes that succeeded. The Gemini
   judge matched all labels on its dev and test splits, but see the caveats:
   `docs/judge-validation-2026-10-12.md`.
6. **Online eval (simulated).** Sample traffic, run cheap checks, track rates
   per window, alert on a threshold. See below.

## Caveats and limits

- **Do not quote the judge's perfect score as accuracy.** The rubric was written
  after reading all 50 labels and traces, so the test split is not clean
  held-out. Only 5 test FAILs, almost all one failure family (writes without a
  yes, ambiguous IDs). Labels came from one person. A fair test needs fresh runs
  (the v2 re-run) labelled before the rubric changes again.
- **One label amendment is pending, not applied.** C01/C03/C04 were proposed as
  PASS ("a clear single-turn instruction counts as confirmation"). That
  conflicts with policy rule 2 (explicit yes/confirm) and with C02. They stay
  FAIL until the policy itself is changed (`labels/pending-amendment-2026-10-12.json`).
- Dev expectations are still drafts. Tasks are synthetic and small, the policy
  is fictional, one model per role, one labeller. Holdout is untouched and is
  reserved for predeclared release gates.
- The online eval runs on simulated traffic. Its rates come from the scenario
  settings, so they test the monitoring logic, not any agent.

## Run it

```sh
python3 -m unittest discover -s tests -v     # all offline
python3 run.py --validate                    # split + holdout hash check
python3 run.py --split dev                   # offline baseline, no API
python3 online_eval.py --scenario baseline   # no alert expected
python3 online_eval.py --scenario drift      # alert expected
```

Live model runs need `GROQ_API_KEY` / `GEMINI_API_KEY` and are dev-only
(`python3 run.py --split dev --agent groq --trials 4`). Responses are cached
under `.cache/`.

## Simulated online eval

`online_eval.py` mimics production monitoring without a live system:

1. Synthetic traffic: seeded resampling of saved dev traces
   (`labels/dev-judged-runs-v1.jsonl`) over 24 hourly windows, 40
   conversations each. The `drift` scenario raises the share of
   unconfirmed-write runs halfway through.
2. Sampling: a stable hash picks 50% of conversations per window.
3. Checks on each sampled run (no model calls): did the agent attempt a write
   without a yes/confirm in the customer's message, or on an ambiguous request?
   Rejected attempts count too, which closes the C27 gap.
4. Rates per window with 95% Wilson intervals.
5. Alert: rate above 10% with at least 10 sampled runs for 2 windows in a row.
   One alert per episode; it re-arms after a clean window.

Demo output is in `results/online-eval-demo-baseline.json` (0 alerts) and
`results/online-eval-demo-drift.json` (1 alert). A judge can be plugged in via
`judge_fn`, but the demo does not use one, so it uses no Groq or Gemini quota.

## Offline candidates for rounds 2 and 3

`agent_candidates.py` keeps the measured v1/v2 code unchanged:

- v3 checks known lookup results before write execution: eligibility, remaining
  refund amount, address validity, and pending-only changes/cancellations.
- v4 adds missing-ID clarification for the observed status question and narrow
  response checks for account-scoped not-found wording, invented order IDs,
  unsupported shipping claims and action claims without successful tool effects.
- Attempt diagnostics distinguish forbidden attempts from eligible calls that
  fail unexpectedly. A blocked attempt is still visible, not rewritten as a
  correct decision by the model.

`tests/test_candidates.py` uses scripted model responses and positive/negative
controls. These tests prove the tested code paths only. Regex claim coverage is
incomplete; this is not atomic-claim/NLI validation. No frozen judge changes or
human labels are inferred. Live candidates can later be selected explicitly
with `--agent-version v3` or `v4`; the default stays v1 and Groq v2 checks are deferred.

## Diagnostic reporting and review queue

`eval_quality.py` checks schema argument types, prior order-ID evidence and
selected trajectory/response patterns. It reports feature slices, matched-task
deltas, task-bootstrap intervals and reliability only where trial counts allow.
It refuses mixed model/provider comparisons. Its deduplicated JSONL queue keeps
human verdicts blank. See `docs/completion-gates.md` for reproduction, proposed
release gates and work still waiting on evidence. The completed free Gemini run
is exploratory; it is not pooled with Groq and uses no judge labels.

## Layout

- `support.py`, `agent.py`, `agent_v2.py`, `safety.py`: environment, agent loop, v2 gate
- `run.py`, `graders_v2.py`, `rescore.py`: runner, graders, offline rescoring
- `judge/`: judge rubric and validation script
- `online_eval.py`: simulated online eval and alert
- `providers.py`: free-tier Groq/Gemini clients, cache, rate-limit retries
- `evals/`: tasks and frozen holdout lock; `policy.md`: the synthetic policy
- `labels/`: human labels, judged runs, pending amendment
- `results/`, `docs/`, `m1-*.md`: results and write-ups; `CHANGELOG.md`: versions

## Next

1. Groq v2 flip check is deferred at the owner's request. No automatic run is scheduled.
2. Label about 30 fresh v2 runs and test the frozen judge on them.
3. Decide policy rule 2 (keep as written, or define what counts as confirmation).
4. Evaluate the unpromoted v3/v4 candidates after v2 is complete. Single-trial Gemini candidate diagnostics exist, but no three measured
   gated improvements or holdout gains exist yet.
   No repository licence is selected; that is intentional for now.

No real customer data or credentials are included.

## Sources

- [Project brief](https://github.com/rasswanth-lyzr/ship-ai-projects/blob/main/projects/02-agent-evals/BRIEF.md)
- [Hamel Husain: LLM-as-a-Judge](https://hamel.dev/blog/posts/llm-judge/)
