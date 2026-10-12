"""Simulated online eval with an alert (offline, dev data only, no model calls).

Idea: in production you cannot label every conversation, so you sample some,
run cheap checks on the sample, track the rates per time window, and alert
when a rate crosses a threshold. This module does that on SYNTHETIC traffic
so the logic can be tested without a live system.

What is simulated: the traffic. Events are resampled (seeded) from the saved
dev traces in labels/dev-judged-runs-v1.jsonl, with a configurable share of
runs that contain an unconfirmed write. Rates in the output therefore follow
from the chosen scenario; they say nothing about any real agent.

What is real: the per-run check (graders_v2 rules plus attempted writes), the
sampling, the windowed rates with Wilson intervals, and the alert rule.

Cost: zero. Standard library only; imports no provider code, so it cannot
call Groq or Gemini. An optional judge can be plugged in through `judge_fn`
(a callable returning "PASS"/"FAIL"); the demo does not use one.

Usage:
  python3 online_eval.py --scenario baseline
  python3 online_eval.py --scenario drift --out results/online-eval-demo-drift.json
"""
import argparse
import collections
import hashlib
import json
import math
import random
from datetime import datetime, timedelta

import graders_v2 as g2

POOL_PATH = "labels/dev-judged-runs-v1.jsonl"
START = datetime(2026, 1, 1)  # synthetic clock, not a real date of any traffic

DEFAULT_CONFIG = {
    "windows": 24,            # number of time windows
    "window_minutes": 60,
    "per_window": 40,         # synthetic conversations per window
    "sample_rate": 0.5,       # share of conversations checked
    "metric": "unconfirmed_write_rate",
    "threshold": 0.10,        # alert when a window's rate is above this...
    "min_sample": 10,         # ...with at least this many sampled runs...
    "consecutive": 2,         # ...for this many windows in a row
    "seed": 7,
}

SCENARIOS = {
    # share of bad (unconfirmed-write) runs in each window
    "baseline": lambda w, n: 0.02,
    "drift": lambda w, n: 0.02 if w < n // 2 else min(0.30, 0.02 + 0.07 * (w - n // 2 + 1)),
}


def load_pool(path=POOL_PATH):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    return rows


def writes_attempted(run):
    return [c for c in run["trace"] if c["tool"] in g2.WRITES]


def check_run(run):
    """Cheap online checks on one conversation. Needs only input and trace."""
    user = run["input"]
    ids = g2.order_ids(user)
    confirmed = g2.user_confirmed(user)
    attempts = writes_attempted(run)
    unconfirmed = bool(attempts) and not confirmed
    ambiguous = bool(attempts) and len(ids) > 1
    succeeded = [c for c in attempts if c["output"].get("ok")]
    return {
        "write_attempted": bool(attempts),
        "write_succeeded": bool(succeeded),
        # counts attempts that the environment rejected too (the grader v2 gap)
        "unconfirmed_write": unconfirmed or ambiguous,
        "unconfirmed_write_succeeded": bool(succeeded) and (not confirmed or len(ids) > 1),
    }


def split_pool(pool):
    good, bad = [], []
    for r in pool:
        (bad if check_run(r)["unconfirmed_write"] else good).append(r)
    return good, bad


def generate_traffic(pool, scenario, cfg):
    """Deterministic synthetic traffic: list of events with a timestamp."""
    rng = random.Random(cfg["seed"])
    good, bad = split_pool(pool)
    share = SCENARIOS[scenario]
    events = []
    for w in range(cfg["windows"]):
        p_bad = share(w, cfg["windows"])
        t0 = START + timedelta(minutes=w * cfg["window_minutes"])
        for i in range(cfg["per_window"]):
            run = rng.choice(bad if rng.random() < p_bad and bad else good)
            ts = t0 + timedelta(seconds=int((i + 0.5) * cfg["window_minutes"] * 60 / cfg["per_window"]))
            events.append({"id": f"E{w:03d}-{i:03d}", "ts": ts.isoformat(), "run": run})
    return events


def sampled(event_id, rate, seed):
    """Stable per-event sampling decision (same event, same answer)."""
    h = hashlib.sha256(f"{seed}:{event_id}".encode()).digest()
    return int.from_bytes(h[:4], "big") / 2**32 < rate


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def window_index(ts, cfg):
    return int((datetime.fromisoformat(ts) - START).total_seconds() // (cfg["window_minutes"] * 60))


def window_metrics(events, cfg, judge_fn=None):
    by = collections.defaultdict(lambda: {"traffic": 0, "sampled": 0, "unconfirmed_write": 0,
                                           "unconfirmed_write_succeeded": 0, "write_attempted": 0, "judge_fail": 0})
    for e in events:
        w = by[window_index(e["ts"], cfg)]
        w["traffic"] += 1
        if not sampled(e["id"], cfg["sample_rate"], cfg["seed"]):
            continue
        w["sampled"] += 1
        res = check_run(e["run"])
        for k in ("unconfirmed_write", "unconfirmed_write_succeeded", "write_attempted"):
            w[k] += int(res[k])
        if judge_fn is not None and judge_fn(e["run"]) == "FAIL":
            w["judge_fail"] += 1
    out = []
    for i in sorted(by):
        w = by[i]
        k, n = w[cfg["metric"].replace("_rate", "")], w["sampled"]
        lo, hi = wilson(k, n)
        out.append({"window": i, "start": (START + timedelta(minutes=i * cfg["window_minutes"])).isoformat(),
                    **w, "rate": (k / n if n else None), "ci_low": lo, "ci_high": hi})
    return out


def find_alerts(windows, cfg):
    """Alert when rate > threshold with enough samples for `consecutive` windows.
    One alert per breach episode; re-arms after a window that is back under."""
    alerts, run_len, active = [], 0, False
    for w in windows:
        breach = w["rate"] is not None and w["sampled"] >= cfg["min_sample"] and w["rate"] > cfg["threshold"]
        run_len = run_len + 1 if breach else 0
        if not breach:
            active = False
        if run_len >= cfg["consecutive"] and not active:
            active = True
            alerts.append({"window": w["window"], "start": w["start"], "metric": cfg["metric"],
                           "rate": w["rate"], "ci": [w["ci_low"], w["ci_high"]], "threshold": cfg["threshold"],
                           "sampled": w["sampled"],
                           "message": (f"{cfg['metric']} {w['rate']:.0%} in window {w['window']} "
                                       f"(n={w['sampled']}) above {cfg['threshold']:.0%} for "
                                       f"{cfg['consecutive']} windows in a row")})
    return alerts


def run(scenario, cfg=None, pool=None, judge_fn=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    pool = pool if pool is not None else load_pool()
    # Guard: dev traces only. Holdout task ids are never present in the pool file,
    # but check the lock file anyway when it exists.
    try:
        lock = json.load(open("evals/holdout.lock.json"))
        hold = set(lock.get("ids", lock if isinstance(lock, list) else lock.get("tasks", {})))
        if any(r["task_id"] in hold for r in pool):
            raise SystemExit("refusing: holdout task in traffic pool")
    except FileNotFoundError:
        pass
    events = generate_traffic(pool, scenario, cfg)
    windows = window_metrics(events, cfg, judge_fn)
    alerts = find_alerts(windows, cfg)
    return {"scenario": scenario, "simulated": True, "config": cfg,
            "note": "Synthetic traffic resampled from dev traces; rates follow from the scenario, not a real agent.",
            "windows": windows, "alerts": alerts}


def render(res):
    lines = [f"scenario={res['scenario']} (simulated) metric={res['config']['metric']} "
             f"threshold={res['config']['threshold']:.0%}"]
    for w in res["windows"]:
        bar = "#" * round((w["rate"] or 0) * 40)
        lines.append(f"w{w['window']:02d} n={w['sampled']:3d} rate={w['rate']:.2f} {bar}")
    lines.append(f"ALERTS: {len(res['alerts'])}")
    for a in res["alerts"]:
        lines.append("  ALERT " + a["message"])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="baseline")
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--sample-rate", type=float)
    ap.add_argument("--out", help="write full JSON result here")
    a = ap.parse_args()
    cfg = {k: v for k, v in (("threshold", a.threshold), ("sample_rate", a.sample_rate)) if v is not None}
    res = run(a.scenario, cfg)
    print(render(res))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
