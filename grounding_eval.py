"""Offline tool-reference and atomic-claim annotation workflow.

No API calls or inferred references/labels. Scores require reviewed exact-case
annotations. Tool-call multiset P/R measures named tool/argument matches, not
trajectory order, consent or policy compliance. Claim support is separate.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def fingerprint(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def blank(records):
    seen=set(); out=[]
    for r in records:
        case=r.get('case') or r.get('run_id')
        if not case or case in seen:raise ValueError('Unique case key required')
        seen.add(case)
        # Identifies the complete supplied evidence record, not only the answer.
        out.append({'case':case, 'evidence_sha256':fingerprint(r),
                    'reference_tool_sequences':None, 'claims':None,
                    'reference_reviewer':None, 'claim_reviewer':None})
    return out


def tool_key(call):
    if not isinstance(call,dict) or not isinstance(call.get('tool'),str) or not isinstance(call.get('args'),dict):
        raise ValueError('Tool reference requires tool and args')
    return json.dumps({'tool':call['tool'],'args':call['args']},sort_keys=True,separators=(',',':'))


def tool_score(actual, reference):
    a=collections.Counter(tool_key(c) for c in actual)
    b=collections.Counter(tool_key(c) for c in reference)
    tp=sum((a & b).values()); n=sum(a.values()); m=sum(b.values())
    p=tp/n if n else (1.0 if not m else 0.0)
    r=tp/m if m else (1.0 if not n else 0.0)
    return {'matched':tp,'actual':n,'reference':m,'precision':p,'recall':r,
            'f1':2*p*r/(p+r) if p+r else 0.0}


def analyze(records, annotations):
    evidence={}
    for r in records:
        case=r.get('case') or r.get('run_id')
        if not case or case in evidence:raise ValueError('Unique evidence case required')
        evidence[case]=r
    by={}
    for a in annotations:
        case=a.get('case')
        if case in by:raise ValueError('Duplicate annotation')
        by[case]=a
    if set(evidence)!=set(by):raise ValueError('Exact annotation coverage required')
    scores=[]; totals=collections.Counter()
    for case,r in evidence.items():
        a=by[case]
        if a.get('evidence_sha256')!=fingerprint(r):raise ValueError('Evidence changed: '+case)
        refs=a.get('reference_tool_sequences')
        if not a.get('reference_reviewer') or not isinstance(refs,list) or not refs or any(not isinstance(x,list) for x in refs):
            raise ValueError('Reviewed nonempty alternatives list required: '+case)
        claims=a.get('claims')
        if not a.get('claim_reviewer') or not isinstance(claims,list):raise ValueError('Reviewed claim list required: '+case)
        actual=r.get('trace')
        if not isinstance(actual,list):raise ValueError('Observed trace required')
        # The failure ledger omits policy calls, so it is not eligible for exact-call scoring.
        if 'source_trace_sha256' in r:raise ValueError('Use full source trace, not trimmed failure ledger')
        alternatives=[tool_score(actual,ref) for ref in refs]
        best=max(range(len(alternatives)),key=lambda i:(alternatives[i]['f1'],alternatives[i]['recall'],alternatives[i]['precision']))
        ids=set()
        for c in claims:
            if not isinstance(c,dict) or not c.get('claim_id') or c['claim_id'] in ids:raise ValueError('Unique claim IDs required')
            ids.add(c['claim_id'])
            text=c.get('text');start=c.get('start');end=c.get('end')
            if type(start) is not int or type(end) is not int or not isinstance(text,str) or not text or start<0 or end<=start or end>len(r['answer']) or r['answer'][start:end]!=text:
                raise ValueError('Claim must bind exact answer span')
            status=c.get('support')
            if status not in {'supported','unsupported','unknown'}:raise ValueError('Reviewed support status required')
            if not c.get('reason'):raise ValueError('Support reason required')
            pointers=c.get('evidence',[])
            if not isinstance(pointers,list):raise ValueError('Evidence pointer list required')
            if status=='supported' and not pointers:raise ValueError('Supported claim needs evidence')
            for pointer in pointers:
                # Input and policy are valid sources; tool evidence identifies its chronological index.
                if isinstance(pointer,str) and pointer in {'input','policy'}:continue
                if not isinstance(pointer,str) or not pointer.startswith('trace:') or not pointer[6:].isdigit() or int(pointer[6:])>=len(actual):
                    raise ValueError('Invalid support pointer')
            totals[status]+=1
        scores.append({'case':case,'selected_reference_alternative':best,'tools':alternatives[best],
                       'claims':len(claims),'order_checked':False})
    n=sum(totals.values()); known=totals['supported']+totals['unsupported']
    return {'cases':len(scores),'per_case':scores,
            'macro_tool_precision':sum(s['tools']['precision'] for s in scores)/len(scores) if scores else None,
            'macro_tool_recall':sum(s['tools']['recall'] for s in scores)/len(scores) if scores else None,
            'claim_counts':dict(totals),'claim_support_rate_all':totals['supported']/n if n else None,
            'claim_support_rate_known':totals['supported']/known if known else None,
            'claim_review_coverage':known/n if n else None,
            'scope':'Reviewed reference-call multiset and annotated answer claims only; not sequence correctness, accuracy, safety or general hallucination rate'}


def main():
    p=argparse.ArgumentParser();p.add_argument('evidence');p.add_argument('--annotations');p.add_argument('--blank',action='store_true');p.add_argument('--out',required=True);a=p.parse_args()
    records=[json.loads(l) for l in Path(a.evidence).read_text().splitlines() if l]
    if a.blank:Path(a.out).write_text(''.join(json.dumps(x)+'\n' for x in blank(records)))
    else:
        if not a.annotations:p.error('--annotations required for scoring')
        rows=[json.loads(l) for l in Path(a.annotations).read_text().splitlines() if l]
        Path(a.out).write_text(json.dumps(analyze(records,rows),indent=2)+'\n')

if __name__=='__main__':main()
