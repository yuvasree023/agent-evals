"""Position/verbosity bias preparation and offline result comparison.

No model calls, no new rubric, no human labels. Changes only example order
or repeats the same answer; tools/effects/customer input remain identical.
"""
import hashlib
import json
import argparse
from pathlib import Path
import copy


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def prepare(runs, shots):
    jobs=[]
    for record in runs:
        for variant in ('base','reversed_examples','verbose_repeat'):
            r=copy.deepcopy(record);examples=copy.deepcopy(shots)
            if variant=='reversed_examples':examples=list(reversed(examples))
            if variant=='verbose_repeat':r['answer']='\n\n'.join([r['answer']]*3)
            payload={'record':r,'examples':examples}
            jobs.append({'case':record['case'],'variant':variant,'original_trace_sha256':fingerprint(record),'payload_sha256':fingerprint(payload),'payload':payload,'verdict':None,'critique':None})
    return jobs


def analyze(jobs):
    by={}
    for j in jobs:
        if j.get('verdict') not in {'PASS','FAIL'}:raise ValueError('Observed verdict required; never infer blank')
        key=(j['case'],j['variant'])
        if key in by:raise ValueError('Duplicate bias job')
        if fingerprint(j['payload'])!=j['payload_sha256']:raise ValueError('Payload changed after verdict collection')
        by[key]=j
    cases=sorted({c for c,v in by})
    if any((c,v) not in by for c in cases for v in ('base','reversed_examples','verbose_repeat')):raise ValueError('Complete matched variants required')
    out={'cases':len(cases),'human_accuracy':None,'scope':'self-consistency under order/repeated verbosity only; not accuracy or semantic invariance proof','variants':{}}
    for v in ('reversed_examples','verbose_repeat'):
        flips=[c for c in cases if by[c,'base']['verdict']!=by[c,v]['verdict']]
        out['variants'][v]={'flips':len(flips),'total':len(cases),'flip_rate':len(flips)/len(cases) if cases else None,'cases':flips}
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--shots');p.add_argument('--analyze',action='store_true');a=p.parse_args()
    rows=[json.loads(l) for l in Path(a.input).read_text().splitlines() if l]
    if a.analyze:Path(a.out).write_text(json.dumps(analyze(rows),indent=2)+'\n')
    else:
        shots=json.loads(Path(a.shots).read_text()) if a.shots else []
        Path(a.out).write_text(''.join(json.dumps(j)+'\n' for j in prepare(rows,shots)))

if __name__=='__main__':main()
