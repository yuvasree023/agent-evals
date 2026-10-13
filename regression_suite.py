"""Separate scripted development regressions, not holdout or model results.

Dataset v0.2-regression supplements, never replaces, the frozen v0.1 tasks.
Expectations execute only in this test harness, never in model messages.
"""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import agent_candidates

PATH=Path(__file__).parent/'evals/regressions-v0.2.jsonl'


def load(path=PATH):
    rows=[json.loads(l) for l in Path(path).read_text().splitlines() if l]
    ids=set(); hashes=set()
    for r in rows:
        if r['split']!='dev-regression':raise ValueError('Regression data must remain development-only')
        if r['id'] in ids:raise ValueError('Duplicate regression ID')
        ids.add(r['id'])
        fingerprint=hashlib.sha256(json.dumps({'input':r['input'],'fixture':r['fixture'],'script':r['script']},sort_keys=True).encode()).hexdigest()
        if fingerprint in hashes:raise ValueError('Exact duplicate regression evidence')
        hashes.add(fingerprint)
    return rows


def evaluate(case):
    turns=[{'content':'','tool_calls':[call],'raw':{}} for call in case['script']]
    turns.append({'content':case['scripted_answer'],'tool_calls':[],'raw':{}})
    with patch('providers.chat',side_effect=turns):
        answer,env,_=agent_candidates.run_task(case,'gemini','scripted-no-api',version=case['candidate'])
    expected=case['expected'];index={o['id']:o for o in env.state()}
    checks={}
    checks['state']=all(index[a['order_id']][a['field']]==a['equals'] for a in expected['state'])
    checks['answer']=all(word in answer for word in expected['answer_contains'])
    checks['blocked']=all(any(c.get('output',{}).get('error')==error for c in env.trace) for error in expected['blocked_errors'])
    env.db.close()
    return {'id':case['id'],'family':case['family'],'candidate':case['candidate'],'checks':checks,'passed':all(checks.values()),'evidence':'scripted offline path test; not model behavior'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out');a=p.parse_args()
    rows=[evaluate(r) for r in load()]
    result={'dataset':'0.2-regression','api_calls':0,'holdout_executed':False,'runs':rows,'passes':sum(r['passed'] for r in rows),'total':len(rows),'scope':'scripted controls only, no improvement-rate claim'}
    if a.out:Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passes'],'total':result['total'],'api_calls':0}))
    if result['passes']!=result['total']:raise SystemExit(1)

if __name__=='__main__':main()
