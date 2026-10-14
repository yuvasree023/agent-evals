"""Full frozen-judge validation over all 30 v2 dev runs (V01-V30), scored
against the owner's 2026-10-14 labels. Separate bounded free-Gemini run;
preserves frozen judge files. Never touches the holdout."""
import json
import hashlib
import importlib.util
import math
from pathlib import Path
import time
import providers

OUTDIR = 'results/judge-full-v2-2026-10-14'
FROZEN = ['judge/judge.py', 'judge/validate.py', 'policy.md',
          'labels/dev-human-labels-2026-10-12.jsonl']
HUMAN_V2 = 'labels/dev-human-labels-v2-2026-10-14.jsonl'


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
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
                tpr=round(tp / P, 3) if P else None, tpr_ci=wilson(tp, P),
                tnr=round(tn / N, 3) if N else None, tnr_ci=wilson(tn, N),
                agreement=round(po, 3), agreement_ci=wilson(tp + tn, n),
                kappa=round(kappa, 3) if kappa is not None else None)


def run(outdir=OUTDIR):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    dest = out / 'verdicts.jsonl'
    if dest.exists():
        raise ValueError('Existing experiment output: preserve, do not overwrite or rerun')
    spec = importlib.util.spec_from_file_location('frozen_judge', 'judge/judge.py')
    judge = importlib.util.module_from_spec(spec); spec.loader.exec_module(judge)
    original = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in FROZEN}
    historical = json.loads(Path('results/judge-validation-dev-2026-10-12.json').read_text())
    labels_v1 = {r['case']: r for r in map(json.loads, Path('labels/dev-human-labels-2026-10-12.jsonl').read_text().splitlines())}
    v1 = {r['case']: r for r in map(json.loads, Path('labels/dev-judged-runs-v1.jsonl').read_text().splitlines())}
    shots = [(v1[c], labels_v1[c]['label'], labels_v1[c]['reason']) for c in historical['split']['train']]
    human_v2 = {r['case']: r for r in map(json.loads, Path(HUMAN_V2).read_text().splitlines())}
    v2 = {r['case']: r for r in map(json.loads, Path('labels/dev-judged-runs-v2.jsonl').read_text().splitlines())}
    cases = sorted(v2)
    assert set(cases) == set(human_v2), 'every judged run needs an owner label'
    manifest = {'cases': cases, 'variant': 'base', 'calls_planned': len(cases),
                'model': judge.MODEL, 'provider': 'gemini', 'uncached': True,
                'frozen_hashes': original,
                'human_labels_v2': HUMAN_V2,
                'human_labels_v2_sha256': hashlib.sha256(Path(HUMAN_V2).read_bytes()).hexdigest(),
                'few_shot_cases': historical['split']['train'],
                'cost_usd': 0,
                'scope': ('First FAIL-inclusive judge validation: all 30 v2 dev runs judged by the '
                          'frozen judge, scored against the owner 2026-10-14 labels. V28 label is '
                          'conditional, resolved FAIL by the owner T020 decision. Dev diagnostic, '
                          'not a release or holdout claim. Judge never sees the v2 labels.')}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    error = None; count = 0
    with dest.open('w') as f:
        for case in cases:
            rec = v2[case]
            try:
                prompt = judge.build_prompt(rec, shots)
                started = time.time()
                res = providers.chat('gemini', judge.MODEL, [{'role': 'user', 'content': prompt}],
                                     judge.TOOL, use_cache=False)
                verdicts = [c['arguments'] for c in res['tool_calls'] if c['name'] == 'submit_verdict']
                if len(verdicts) != 1 or verdicts[0].get('verdict') not in {'PASS', 'FAIL'}:
                    raise ValueError('Missing or invalid forced verdict')
                row = {'case': case, 'variant': 'base', 'task_id': rec['task_id'], 'trial': rec['trial'],
                       'human': human_v2[case]['label'], 'verdict': verdicts[0]['verdict'],
                       'critique': verdicts[0].get('critique', ''),
                       'latency_ms': round(1000 * (time.time() - started), 2),
                       'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                       'usage': res.get('usage')}
                f.write(json.dumps(row) + '\n'); f.flush(); count += 1
                print('JUDGED', case, human_v2[case]['label'], verdicts[0]['verdict'], flush=True)
            except Exception as e:
                error = type(e).__name__ + ': ' + str(e)[:400]
                print('STOP', error, flush=True)
                break
    assert original == {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in original}
    rows = [json.loads(l) for l in dest.read_text().splitlines()]
    pairs = [(r['human'], r['verdict']) for r in rows]
    disagreements = [{'case': r['case'], 'human': r['human'], 'judge': r['verdict'],
                      'critique': r['critique']} for r in rows if r['human'] != r['verdict']]
    report = {'planned_calls': len(cases), 'observed_calls': count,
              'complete': count == len(cases), 'error': error, 'cost_usd': 0,
              'metrics_vs_owner_labels': metrics(pairs) if pairs else None,
              'disagreements': disagreements}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('FULL_V2_REPORT', json.dumps(report))
    return out


if __name__ == '__main__':
    run()
