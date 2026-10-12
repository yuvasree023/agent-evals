"""Validate the judge against the human labels. Dev traces only.
Usage: python3 judge/validate.py OUT.json   (reads labels/ only; needs GEMINI_API_KEY)
Split is fixed by case id (stratified, seeded below) so it is reproducible:
train = few-shot examples, dev = free to inspect/iterate, test = judged once."""
import json, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from judge import judge_run
LABELS = os.path.join(os.path.dirname(__file__), "..", "labels", "dev-human-labels-2026-10-12.jsonl")

RUNS = os.path.join(os.path.dirname(__file__), "..", "labels", "dev-judged-runs-v1.jsonl")

def split(rows):
    import random
    rnd = random.Random(20261012)
    out = {"train": [], "dev": [], "test": []}
    for lab in ("FAIL", "PASS"):
        grp = sorted((r for r in rows if r["label"] == lab), key=lambda r: r["case"])
        rnd.shuffle(grp)
        n = len(grp)
        a, b = round(n * 0.2), round(n * 0.2) + round(n * 0.3)
        out["train"] += grp[:a]; out["dev"] += grp[a:b]; out["test"] += grp[b:]
    return out

def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))

def metrics(pairs):  # pairs of (human, judge); PASS is the positive class
    tp = sum(h == "PASS" and j == "PASS" for h, j in pairs)
    tn = sum(h == "FAIL" and j == "FAIL" for h, j in pairs)
    fp = sum(h == "FAIL" and j == "PASS" for h, j in pairs)
    fn = sum(h == "PASS" and j != "PASS" for h, j in pairs)
    n = len(pairs); po = (tp + tn) / n if n else 0
    pp = ((tp + fn) / n) * ((tp + fp) / n) if n else 0
    pn = ((tn + fp) / n) * ((tn + fn) / n) if n else 0
    pe = pp + pn
    kappa = (po - pe) / (1 - pe) if pe < 1 else None
    P, N = tp + fn, tn + fp
    return dict(n=n, human_pass=P, human_fail=N, tp=tp, tn=tn, fp=fp, fn=fn,
                tpr=tp / P if P else None, tpr_ci=wilson(tp, P),
                tnr=tn / N if N else None, tnr_ci=wilson(tn, N),
                accuracy=po, kappa=kappa)

def main():
    rows = [json.loads(l) for l in open(LABELS)]
    runs = {json.loads(l)["case"]: json.loads(l) for l in open(RUNS)}
    get = lambda r: runs[r["case"]]
    sp = split(rows)
    shots = [(get(r), r["label"], r["reason"]) for r in sp["train"]]
    res = {}
    for name in ("dev", "test"):
        recs = []
        for r in sp[name]:
            j = judge_run(get(r), shots)
            recs.append(dict(case=r["case"], human=r["label"], judge=j["verdict"], critique=j["critique"]))
        res[name] = dict(metrics=metrics([(x["human"], x["judge"]) for x in recs]), cases=recs)
    res["split"] = {k: [r["case"] for r in v] for k, v in sp.items()}
    json.dump(res, open(sys.argv[1], "w"), indent=1)
    print(json.dumps({k: res[k]["metrics"] for k in ("dev", "test")}, indent=1))
main()
