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
