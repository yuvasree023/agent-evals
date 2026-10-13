# Changelog

## 0.1 - Starter

Added an offline SQLite support environment, six tools, rule-based smoke
baseline, 50 synthetic draft tasks, 35/15 split lock, offline runner, tests,
and critique-shadowing roadmap. No LLM evaluation or improvement claimed.

## 0.2 - Free-tier model wiring

Added Groq and Gemini providers (keys from environment variables only, free
plans with billing disabled, non-free models refused), a model -> tool ->
result agent loop, disk response cache keyed by a key-mixed hash, retries
honoring Retry-After with daily-quota stop, and dev-only live runs (holdout
refused outside release gates). Verified live with two-turn tool loops
against both providers on 2026-10-12. No model quality results claimed; dev
expectations remain unreviewed drafts.

## 0.3 - Trials, flip check, layered graders

Added `--trials N` for repeated independent dev trials and `--flip-check`
(two uncached runs per task, reports verdict flips) per the M1 plan, plus
first M2 reporting layers (schema validity, mutation without lookup,
repeated calls, tool errors, step efficiency) that accompany but do not
change the smoke pass/fail. Live smoke on 2026-10-12: three happy-path dev
tasks through Groq gpt-oss-120b, 3/3 smoke graders passed with correct
lookup-before-mutate trajectories. Plumbing evidence only: dev expectations
remain unreviewed drafts and no multi-trial run has been done.

## 0.4 - Simulated online eval, README rewrite

Added `online_eval.py` (seeded synthetic traffic from dev traces, sampling,
windowed unconfirmed-write rate with Wilson intervals, consecutive-window alert),
tests, and two demo outputs. Offline, no model calls. README rewritten to
describe the M1 -> grader bug -> v2 gate -> judge calibration story and its
limits. No new agent results: the v2 re-run is pending the Groq daily reset.


## 0.5 - Offline rounds 2/3 candidates (2026-10-13)

Preserved measured v1/v2 and grader v2, holdout, labels and frozen judge.
Added unpromoted v3 eligibility checks based on observed lookup results and
v4 narrow clarification/response checks. Scripted positive/negative controls
cover shipped/pending/delivered boundaries, refund ceilings, failed-service
controls, successful confirmed refunds and selected evidence failures.
Updated stale README/method status. Offline tests and split/hash validation
only; no API calls, model improvement deltas, promotion or holdout results.
