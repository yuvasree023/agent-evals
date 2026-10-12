"""Rescore saved M1 traces with grader v2. Offline, dev only, no model calls.
Usage: python3 rescore.py M1_TRACES.jsonl FLIP_TRACES.jsonl OUT.json"""
import json, sys, collections
from run import load_tasks, task_state
import graders_v2 as g2

def score(path, tasks):
    out = []
    for line in open(path):
        r = json.loads(line)
        t = tasks[r["task_id"]]
        assert t["split"] == "dev", "holdout must never be scored"
        g, viol = g2.grade_v2(t, task_state(t), r)
        out.append(dict(task_id=r["task_id"], trial=r["trial"], v1_passed=r["passed"], v1=r["graders"],
                        v2=g, v2_passed=all(g.values()), violations=viol))
    return out

def main():
    tasks = {t["id"]: t for t in load_tasks()}
    m1, flip = score(sys.argv[1], tasks), score(sys.argv[2], tasks)
    by = collections.defaultdict(list)
    for r in flip: by[r["task_id"]].append(r["v2_passed"])
    flips = sorted(k for k, v in by.items() if len(v) == 2 and v[0] != v[1])
    n = len(m1)
    summ = dict(grader_version=g2.GRADER_VERSION, runs=n,
        v2_passes=sum(r["v2_passed"] for r in m1), v1_passes=sum(bool(r["v1_passed"]) for r in m1),
        by_check={k: sum(r["v2"][k] for r in m1) for k in ("state", "response", "policy")},
        by_trial={i: sum(r["v2_passed"] for r in m1 if r["trial"] == i) for i in (1, 2, 3, 4)},
        policy_violation_runs=sorted({(r["task_id"], r["trial"], tuple(r["violations"])) for r in m1 if r["violations"]}),
        flip_pairs=len(by), flip_tasks=flips, flip_v2_passes=sum(r["v2_passed"] for r in flip))
    json.dump(dict(summary=summ, m1=m1, flip=flip), open(sys.argv[3], "w"), indent=1, default=list)
    print(json.dumps(summ, indent=1, default=list))
main()
