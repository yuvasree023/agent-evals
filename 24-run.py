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
    import agent
    import providers
    if args.split != "dev":
        raise RuntimeError(
            "Model agents run on dev only. The holdout is reserved for "
            "predeclared release gates (see docs/method.md).")
    records = []
    for task in selected:
        start = time.perf_counter()
        try:
            answer, env, messages = agent.run_task(
                task, args.agent, args.model,
                max_steps=config["max_steps"], cache_dir=args.cache_dir)
            checks = grade(task["expected"], task_state(task), env.state(), answer, env.trace)
            records.append(dict(task_id=task["id"], split=task["split"],
                input=task["input"], answer=answer, trace=env.trace,
                after=env.state(), graders=checks, passed=all(checks.values()),
                messages=_strip(messages),
                latency_ms=(time.perf_counter()-start)*1000, cost_usd=0,
                agent=f"{args.agent}:{args.model}", error=None))
            env.db.close()
        except providers.ProviderError as exc:
            records.append(dict(task_id=task["id"], split=task["split"],
                input=task["input"], answer=None, trace=[], graders=None,
                passed=None, error=str(exc),
                latency_ms=(time.perf_counter()-start)*1000, cost_usd=0,
                agent=f"{args.agent}:{args.model}"))
    return records

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
    parser.add_argument("--no-cache", action="store_true")
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
    if args.agent == "offline":
        records=[]
        for task in selected:
            env=Store(task["fixture"]); before=env.state(); start=time.perf_counter()
            answer=baseline(task["input"], env, config["max_steps"])
            checks=grade(task["expected"],before,env.state(),answer,env.trace)
            records.append(dict(task_id=task["id"],split=task["split"],input=task["input"],answer=answer,trace=env.trace,before=before,after=env.state(),graders=checks,passed=all(checks.values()),latency_ms=(time.perf_counter()-start)*1000,cost_usd=0,agent=config["agent"]))
            env.db.close()
    else:
        if args.no_cache:
            raise RuntimeError("--no-cache is reserved for M1 flip-rate runs")
        records = run_live(selected, args, config)
    suffix = f"{args.split}-{args.agent}"
    (out/(suffix+"-traces.jsonl")).write_text("".join(json.dumps(r)+"\n" for r in records))
    graded=[r for r in records if r["passed"] is not None]
    passed=sum(r["passed"] for r in graded)
    summary=dict(
        mode=("offline plumbing smoke, not LLM performance" if args.agent=="offline"
              else "live model smoke on draft dev expectations, not a benchmark"),
        split=args.split, agent=args.agent if args.agent=="offline" else f"{args.agent}:{args.model or ''}",
        tasks=len(records), graded=len(graded), passed=passed,
        success_rate=(passed/len(graded)) if graded else None,
        errors=len(records)-len(graded), cost_usd=0)
    (out/(suffix+"-report.json")).write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
