"""Eval runner. Expected fields are only consumed by graders.

Offline by default: `python3 run.py --split dev` uses the rule baseline with
no network. Live runs use `--agent groq|gemini` with the matching API key in
an environment variable, and are restricted to dev tasks; the holdout is only
for predeclared release gates and this runner refuses it for model agents.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from support import Store, baseline
ROOT = Path(__file__).parent

def load_tasks():
    return [json.loads(line) for line in (ROOT / "evals/tasks.jsonl").read_text().splitlines() if line.strip()]

def validate(tasks):
    assert len(tasks) == 50, "Expected initial 50-task dataset"
    assert len({t["id"] for t in tasks}) == len(tasks), "Duplicate task ID"
    assert all(t["split"] in {"dev", "holdout"} for t in tasks)
    locked = json.loads((ROOT / "evals/holdout.lock.json").read_text())["tasks"]
    holdout = {t["id"]: hashlib.sha256(json.dumps(t,sort_keys=True,separators=(",", ":")).encode()).hexdigest() for t in tasks if t["split"] == "holdout"}
    assert holdout == locked, "Holdout content or split changed"
    assert len(holdout) / len(tasks) >= 0.30
    for t in tasks:
        assert set(t["tags"]) == {"feature", "scenario", "persona", "difficulty"}
        ids = {o["id"] for o in t["fixture"]["orders"]}
        for assertion in t["expected"]["state"]:
            assert assertion["order_id"] in ids
        assert t["review_status"] == "draft"
    dev_families={t["family_id"] for t in tasks if t["split"]=="dev"}
    assert not dev_families & {t["family_id"] for t in tasks if t["split"]=="holdout"}

def grade_layers(trace, answer, max_steps, provider=None):
    """M2 layered checks that do not change pass/fail yet: schema validity,
    trajectory hygiene, and loop/efficiency signals for human review."""
    from agent import TOOL_SCHEMAS
    schemas = {t["name"]: t["parameters"] for t in TOOL_SCHEMAS}
    required = {n: set(p.get("required", [])) for n, p in schemas.items()}
    layers = {}
    unknown = [c for c in trace if c["tool"] not in schemas]
    bad_args = [c for c in trace if c["tool"] in schemas
                and not required[c["tool"]] <= set(c["args"])]
    layers["schema_ok"] = not unknown and not bad_args
    layers["unknown_tool_calls"] = len(unknown)
    # trajectory: lookup must precede the first mutating call per order
    seen, violations = set(), 0
    for c in trace:
        oid = c["args"].get("order_id")
        if c["tool"] == "lookup_order" and "order" in c["output"]:
            seen.add(oid)
        if c["tool"] in {"refund_order", "change_address", "cancel_order"} and c["output"].get("ok"):
            if oid not in seen:
                violations += 1
    layers["mutation_without_lookup"] = violations
    # loops: identical (tool, args) call repeated
    sigs = [(c["tool"], json.dumps(c["args"], sort_keys=True)) for c in trace]
    layers["repeated_calls"] = len(sigs) - len(set(sigs))
    # errors that the agent retried blindly
    layers["tool_errors"] = sum(1 for c in trace if "error" in c["output"])
    layers["steps_used"] = len(trace)
    layers["efficient"] = len(trace) <= max_steps
    return layers

def grade(expected, before, after, answer, trace):
    state = before == after if expected["unchanged"] else True
    indexed = {o["id"]: o for o in after}
    for a in expected["state"]:
        state = state and indexed.get(a["order_id"], {}).get(a["field"]) == a["equals"]
    words = expected["response_any"]
    response = not words or any(w.lower() in answer.lower() for w in words)
    safety = all(0 <= o["refunded"] <= o["total"] for o in after)
    seen=set()
    for call in trace:
        oid=call["args"].get("order_id")
        if call["tool"]=="lookup_order" and "order" in call["output"]:
            seen.add(oid)
        if call["tool"] in {"refund_order", "change_address", "cancel_order"} and call["output"].get("ok"):
            safety = safety and oid in seen and call["args"].get("confirmed") is True
    return {"state":bool(state), "response_smoke":bool(response), "policy_smoke":bool(safety)}

def run_live(selected, args, config):
    """Live dev runs. trials>1 repeats each task independently (fresh
    environment per trial). flip_check runs every task twice with the
    response cache bypassed, because cached responses cannot measure
    model noise (docs/method.md M1)."""
    import agent
    import providers
    if args.split != "dev":
        raise RuntimeError(
            "Model agents run on dev only. The holdout is reserved for "
            "predeclared release gates (see docs/method.md).")
    if args.flip_check:
        args.trials = 2
        args.no_cache = True
    use_cache = not args.no_cache
    # Each (task, trial) has its own cache. Replaying a interrupted trial is
    # resumable, but distinct trials never share a sampled response.
    checkpoint = getattr(args, "checkpoint", None)
    records = []
    if getattr(args, "resume", False) and checkpoint and checkpoint.exists():
        records = [json.loads(line) for line in checkpoint.read_text().splitlines()
                   if line.strip()]
        records = [r for r in records if r.get("passed") is not None]
    completed = {(r["task_id"], r["trial"]) for r in records}
    quota_stop = False
    for task in selected:
        for trial in range(1, args.trials + 1):
            if (task["id"], trial) in completed:
                continue
            start = time.perf_counter()
            try:
                answer, env, messages = agent.run_task(
                    task, args.agent, args.model,
                    max_steps=config["max_steps"],
                    cache_dir=str(Path(args.cache_dir) / task["id"] / str(trial)),
                    use_cache=use_cache)
                checks = grade(task["expected"], task_state(task), env.state(), answer, env.trace)
                layers = grade_layers(env.trace, answer, config["max_steps"], provider=args.agent)
                records.append(dict(task_id=task["id"], split=task["split"],
                    trial=trial,
                    input=task["input"], answer=answer, trace=env.trace,
                    after=env.state(), graders=checks, passed=all(checks.values()),
                    layers=layers,
                    messages=_strip(messages),
                    latency_ms=(time.perf_counter()-start)*1000, cost_usd=0,
                    agent=f"{args.agent}:{args.model}", error=None))
                env.db.close()
            except providers.ProviderError as exc:
                records.append(dict(task_id=task["id"], split=task["split"],
                    trial=trial,
                    input=task["input"], answer=None, trace=[], graders=None,
                    passed=None, error=str(exc),
                    latency_ms=(time.perf_counter()-start)*1000, cost_usd=0,
                    agent=f"{args.agent}:{args.model}"))
                quota_stop = isinstance(exc, providers.DailyQuotaExhausted)
            if checkpoint:
                checkpoint.parent.mkdir(parents=True, exist_ok=True)
                checkpoint.write_text("".join(json.dumps(r)+"\n" for r in records))
            if quota_stop:
                break
        if quota_stop:
            break
    return records

def flip_summary(records):
    """M1 flip rate: verdict changes between the two uncached runs."""
    by_task = {}
    for r in records:
        by_task.setdefault(r["task_id"], {})[r["trial"]] = r["passed"]
    flips = {t: v for t, v in by_task.items()
             if len(v) == 2 and v[1] is not None and v[2] is not None and v[1] != v[2]}
    comparable = sum(1 for v in by_task.values()
                     if len(v) == 2 and v[1] is not None and v[2] is not None)
    return {"comparable_tasks": comparable,
            "flipped_tasks": sorted(flips),
            "flip_rate": (len(flips) / comparable) if comparable else None}

def task_state(task):
    return sorted((dict(o) for o in task["fixture"]["orders"]),
                  key=lambda o: o["id"])

def _strip(messages):
    """Drop provider raw turns from trace files; keep auditable content."""
    out = []
    for m in messages:
        m = {k: v for k, v in m.items() if k != "raw"}
        out.append(m)
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev","holdout","all"], default="dev")
    parser.add_argument("--validate",action="store_true")
    parser.add_argument("--agent", choices=["offline","groq","gemini"], default="offline")
    parser.add_argument("--model", default=None,
                        help="provider model ID; default from config.json")
    parser.add_argument("--limit", type=int, default=None,
                        help="run at most N tasks (smoke runs)")
    parser.add_argument("--cache-dir", default=".cache/llm")
    parser.add_argument("--no-cache", action="store_true",
                        help="bypass the response cache (flip-rate second runs)")
    parser.add_argument("--resume", action="store_true",
                        help="reuse completed trial checkpoints (same code/config only)")
    parser.add_argument("--trials", type=int, default=1,
                        help="independent trials per task (M1: use >=4)")
    parser.add_argument("--flip-check", action="store_true",
                        help="run twice uncached and report verdict flips")
    args=parser.parse_args(); tasks=load_tasks(); validate(tasks)
    if args.validate:
        print("Validated 50 tasks: 35 dev / 15 frozen holdout; expectations remain draft."); return
    config=json.loads((ROOT/"config.json").read_text())
    if args.agent != "offline" and not args.model:
        args.model = config["default_models"][args.agent]
    if args.agent == "offline":
        if config["api_enabled"] or config["spend_cap_usd"] != 0 or config["agent"] != "offline-rules-v0":
            raise RuntimeError("Only zero-spend offline baseline is implemented")
    selected=[t for t in tasks if args.split=="all" or t["split"]==args.split]
    if args.limit:
        selected=selected[:args.limit]
    out=ROOT/"results/local"; out.mkdir(parents=True,exist_ok=True)
    suffix = f"{args.split}-{args.agent}" + ("-flip" if args.flip_check else "-m1")
    args.checkpoint = out / (suffix + "-checkpoint.jsonl")
    if args.agent == "offline":
        records=[]
        for task in selected:
            env=Store(task["fixture"]); before=env.state(); start=time.perf_counter()
            answer=baseline(task["input"], env, config["max_steps"])
            checks=grade(task["expected"],before,env.state(),answer,env.trace)
            records.append(dict(task_id=task["id"],split=task["split"],input=task["input"],answer=answer,trace=env.trace,before=before,after=env.state(),graders=checks,passed=all(checks.values()),latency_ms=(time.perf_counter()-start)*1000,cost_usd=0,agent=config["agent"]))
            env.db.close()
    else:
        records = run_live(selected, args, config)
    (out/(suffix+"-traces.jsonl")).write_text("".join(json.dumps(r)+"\n" for r in records))
    graded=[r for r in records if r["passed"] is not None]
    passed=sum(r["passed"] for r in graded)
    flips = flip_summary(records) if args.agent != "offline" and args.flip_check else None
    summary=dict(
        mode=("offline plumbing smoke, not LLM performance" if args.agent=="offline"
              else "live model smoke on draft dev expectations, not a benchmark"),
        split=args.split, agent=args.agent if args.agent=="offline" else f"{args.agent}:{args.model or ''}",
        tasks=len(records), graded=len(graded), passed=passed,
        success_rate=(passed/len(graded)) if graded else None,
        trials=args.trials if args.agent != "offline" else 1,
        errors=len(records)-len(graded), cost_usd=0,
        expected_records=len(selected)*(args.trials if args.agent != "offline" else 1),
        complete=len(graded)==len(selected)*(args.trials if args.agent != "offline" else 1),
        flip_check=flips)
    (out/(suffix+"-report.json")).write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    if not summary["complete"]:
        raise SystemExit(75)  # checkpoints/artifacts retained; do not run flip yet

if __name__ == "__main__":
    main()
