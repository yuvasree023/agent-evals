"""Separate bounded free-Gemini bias experiment. Preserves frozen judge files."""
import json
import hashlib
import importlib.util
from pathlib import Path
import random
import time
import providers
import judge_bias as bias

CASES=['V01','V04','V07','V10','V13','V14','V15','V16','V19','V21','V25','V27']
VARIANTS=['base','base_repeat','reversed_examples','verbose_repeat']


def run(outdir='results/judge-bias-2026-10-13'):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    dest=out/'verdicts.jsonl'
    if dest.exists():raise ValueError('Existing experiment output: preserve, do not overwrite or rerun')
    spec=importlib.util.spec_from_file_location('frozen_judge','judge/judge.py');judge=importlib.util.module_from_spec(spec);spec.loader.exec_module(judge)
    original={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['judge/judge.py','judge/validate.py','policy.md','labels/dev-human-labels-2026-10-12.jsonl']}
    historical=json.loads(Path('results/judge-validation-dev-2026-10-12.json').read_text())
    labels={r['case']:r for r in map(json.loads,Path('labels/dev-human-labels-2026-10-12.jsonl').read_text().splitlines())}
    v1={r['case']:r for r in map(json.loads,Path('labels/dev-judged-runs-v1.jsonl').read_text().splitlines())}
    shots=[(v1[c],labels[c]['label'],labels[c]['reason']) for c in historical['split']['train']]
    v2={r['case']:r for r in map(json.loads,Path('labels/dev-judged-runs-v2.jsonl').read_text().splitlines())}
    jobs=bias.prepare([v2[c] for c in CASES],shots)
    # Variant order shuffled within each case with a fixed seed, never outcomes.
    rng=random.Random(20261013);ordered=[]
    for case in CASES:
        grp=[j for j in jobs if j['case']==case];rng.shuffle(grp);ordered.extend(grp)
    manifest={'cases':CASES,'variants':VARIANTS,'calls_planned':48,'model':judge.MODEL,'provider':'gemini','uncached':True,'frozen_hashes':original,'few_shot_cases':historical['split']['train'],'few_shot_sha256':bias.fingerprint(shots),'cost_usd':0,'scope':'Groq-generated v2 traces assessed by Gemini; same-family Gemini generation results are not part of this experiment. Same frozen historical rubric, not a fresh accuracy test.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    error=None;count=0
    with dest.open('w') as f:
        for j in ordered:
            try:
                prompt=judge.build_prompt(j['payload']['record'],j['payload']['examples'])
                started=time.time()
                res=providers.chat('gemini',judge.MODEL,[{'role':'user','content':prompt}],judge.TOOL,use_cache=False)
                verdicts=[c['arguments'] for c in res['tool_calls'] if c['name']=='submit_verdict']
                if len(verdicts)!=1 or verdicts[0].get('verdict') not in {'PASS','FAIL'}:raise ValueError('Missing or invalid forced verdict')
                j.update(verdict=verdicts[0]['verdict'],critique=verdicts[0].get('critique',''),latency_ms=round(1000*(time.time()-started),2),prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),usage=res.get('usage'),raw=res.get('raw'))
                f.write(json.dumps(j)+'\n');f.flush();count+=1
            except Exception as e:
                error=type(e).__name__+': '+str(e)[:400];break
    assert original=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in original}
    rows=[json.loads(l) for l in dest.read_text().splitlines()]
    complete=[c for c in CASES if {r['variant'] for r in rows if r['case']==c}==set(VARIANTS)]
    matched=[r for r in rows if r['case'] in complete]
    report={'planned_calls':48,'observed_calls':count,'complete_cases':complete,'complete':count==48,'error':error,'cost_usd':0,'bias':bias.analyze(matched) if matched else None}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BIAS_REPORT',json.dumps(report))
    return out

if __name__=='__main__':run()
