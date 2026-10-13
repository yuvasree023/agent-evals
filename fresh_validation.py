"""Offline validation for separately supplied human/judge verdicts.

Does not call a judge, infer labels, modify a rubric or replace old reports.
Requires exact case coverage and trace hashes to prevent accidental mismatch.
Failure is the positive class; historical validate.py used PASS-positive.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True,separators=(',',':')).encode()).hexdigest()


def wilson(k,n,z=1.96):
    if not n: return None
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def evaluate(runs,human,judge):
    originals={r['case']:r for r in runs}
    if len(originals)!=len(runs):raise ValueError('Duplicate trace case')
    maps=[]
    for rows in (human,judge):
        m={r['case']:r for r in rows}
        if len(m)!=len(rows) or set(m)!=set(originals):raise ValueError('Exact unique case coverage required')
        for cid,r in m.items():
            if r.get('verdict') not in {'PASS','FAIL'}:raise ValueError('Explicit PASS/FAIL required, never infer blanks')
            if r.get('trace_sha256')!=digest(originals[cid]):raise ValueError('Trace fingerprint mismatch')
        maps.append(m)
    hm,jm=maps
    pairs=[(hm[c]['verdict'],jm[c]['verdict']) for c in sorted(originals)]
    tp=sum(h=='FAIL' and j=='FAIL' for h,j in pairs)
    tn=sum(h=='PASS' and j=='PASS' for h,j in pairs)
    fp=sum(h=='PASS' and j=='FAIL' for h,j in pairs)
    fn=sum(h=='FAIL' and j=='PASS' for h,j in pairs)
    p=tp+fn;n=tn+fp;total=p+n
    agreement=(tp+tn)/total if total else None
    chance=((p*(tp+fp)+n*(tn+fn))/(total*total)) if total else None
    return {'positive_class':'FAIL','n':total,'human_fail':p,'human_pass':n,'tp':tp,'tn':tn,'fp':fp,'fn':fn,
            'failure_detection_tpr':tp/p if p else None,'tpr_wilson_95pct':wilson(tp,p),
            'pass_acceptance_tnr':tn/n if n else None,'tnr_wilson_95pct':wilson(tn,n),
            'precision':tp/(tp+fp) if tp+fp else None,'agreement':agreement,
            'kappa':(agreement-chance)/(1-chance) if chance is not None and chance<1 else None,
            'disagreements':[c for c in sorted(originals) if hm[c]['verdict']!=jm[c]['verdict']],
            'caveat':'Metrics do not establish independence, representative sampling or clean rubric freezing; verify provenance separately.'}


def load(path):return [json.loads(l) for l in Path(path).read_text().splitlines() if l]

def main():
    p=argparse.ArgumentParser();p.add_argument('runs');p.add_argument('--human');p.add_argument('--judge');p.add_argument('--out',required=True);p.add_argument('--blank',action='store_true')
    a=p.parse_args();runs=load(a.runs)
    if a.blank:
        rows=[{'case':r['case'],'trace_sha256':digest(r),'verdict':None,'reason':''} for r in runs]
        Path(a.out).write_text(''.join(json.dumps(r)+'\n' for r in rows));return
    if not a.human or not a.judge:p.error('--human and --judge required for validation')
    result=evaluate(runs,load(a.human),load(a.judge))
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
