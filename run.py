"""Offline smoke runner. Expected fields are only consumed by graders."""
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

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev","holdout","all"], default="dev")
    parser.add_argument("--validate",action="store_true")
    args=parser.parse_args(); tasks=load_tasks(); validate(tasks)
    if args.validate:
        print("Validated 50 tasks: 35 dev / 15 frozen holdout; expectations remain draft."); return
    config=json.loads((ROOT/"config.json").read_text())
    if config["api_enabled"] or config["spend_cap_usd"] != 0 or config["agent"] != "offline-rules-v0":
        raise RuntimeError("Only zero-spend offline baseline is implemented")
    out=ROOT/"results/local"; out.mkdir(parents=True,exist_ok=True)
    selected=[t for t in tasks if args.split=="all" or t["split"]==args.split]
    records=[]
    for task in selected:
        env=Store(task["fixture"]); before=env.state(); start=time.perf_counter()
        answer=baseline(task["input"], env, config["max_steps"])
        checks=grade(task["expected"],before,env.state(),answer,env.trace)
        records.append(dict(task_id=task["id"],split=task["split"],input=task["input"],answer=answer,trace=env.trace,before=before,after=env.state(),graders=checks,passed=all(checks.values()),latency_ms=(time.perf_counter()-start)*1000,cost_usd=0,agent=config["agent"]))
        env.db.close()
    (out/(args.split+"-traces.jsonl")).write_text("".join(json.dumps(r)+"\n" for r in records))
    passed=sum(r["passed"] for r in records)
    summary=dict(mode="offline plumbing smoke, not LLM performance",split=args.split,tasks=len(records),passed=passed,success_rate=passed/len(records),cost_usd=0)
    (out/(args.split+"-report.json")).write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__":
    main()
