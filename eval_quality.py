"""Offline dev diagnostics and review queue. No API calls; not an LLM judge.

New signals are separate from historical grader_v2. Regex response checks
are incomplete and only identify selected failure patterns. Never infer
human labels or inspect holdout outcomes for tuning.
"""
import argparse
import collections
import hashlib
import json
import random
from pathlib import Path
import agent_candidates as candidates
from agent import TOOL_SCHEMAS

SCHEMAS = {t['name']: t['parameters'] for t in TOOL_SCHEMAS}


def schema_findings(trace):
    out = []
    for c in trace:
        name, args = c['tool'], c.get('args', {})
        if name not in SCHEMAS:
            out.append('unknown_tool:' + name); continue
        s = SCHEMAS[name]
        if not isinstance(args, dict):
            out.append('arguments_not_object:' + name); continue
        for field in s.get('required', []):
            if field not in args: out.append('missing_argument:' + name + ':' + field)
        for field, value in args.items():
            prop = s['properties'].get(field)
            if prop is None:
                # Schemas permit extra properties unless explicitly disabled.
                if s.get('additionalProperties') is False:
                    out.append('extra_argument:' + name + ':' + field)
                continue
            typ = prop.get('type')
            valid = {'string': isinstance(value, str), 'integer': type(value) is int,
                     'boolean': type(value) is bool, 'number': type(value) in (int,float),
                     'object': isinstance(value,dict), 'array': isinstance(value,list)}.get(typ, True)
            if not valid: out.append('wrong_type:' + name + ':' + field)
            if 'enum' in prop and value not in prop['enum']:
                out.append('invalid_enum:' + name + ':' + field)
    return sorted(set(out))


def entity_findings(user_text, answer, trace):
    # Earlier read evidence only: later calls cannot retroactively support an ID.
    seen = set(candidates.safety.order_ids(user_text)); findings = []
    for c in trace:
        oid = c.get('args', {}).get('order_id')
        if oid and oid not in seen: findings.append('unsupported_argument_id:' + str(oid))
        output = c.get('output', {})
        if 'order' in output: seen.add(output['order']['id'])
        for o in output.get('orders', []): seen.add(o['id'])
    for oid in sorted(candidates.safety.order_ids(answer) - seen):
        findings.append('unsupported_answer_id:' + oid)
    return sorted(set(findings))


def signals(rec):
    trace = rec['trace']; text = rec['input']; answer = rec['answer']
    return {'schema': schema_findings(trace),
            'trajectory': candidates.trajectory_findings(text, trace),
            'entities': entity_findings(text, answer, trace),
            'response_patterns': candidates.response_findings(text, answer, trace)}


def reliability(outcomes, k):
    """Unbiased finite-n estimators, only for tasks with at least k trials."""
    import math
    if k < 1: raise ValueError('k must be positive')
    scored=[]
    for task, vals in outcomes.items():
        n=len(vals); c=sum(vals)
        if n < k: continue
        denominator=math.comb(n,k)
        scored.append((math.comb(c,k)/denominator if c>=k else 0,
                       1-(math.comb(n-c,k)/denominator if n-c>=k else 0)))
    return {'k':k,'eligible_tasks':len(scored),'all_k':sum(x[0] for x in scored)/len(scored) if scored else None,
            'at_least_one':sum(x[1] for x in scored)/len(scored) if scored else None}


def cluster_interval(values, seed=1729, samples=2000):
    """Task bootstrap, equal task weights. Not independent-trial uncertainty."""
    if len(values)<2: return None
    rng=random.Random(seed); boots=[]
    for _ in range(samples):
        boots.append(sum(rng.choice(values) for _ in values)/len(values))
    boots.sort()
    return [boots[int(.025*samples)], boots[min(samples-1,int(.975*samples))]]


def compare(records, tasks):
    """Complete paired task sets only; partial data never becomes a full delta."""
    by=collections.defaultdict(lambda:collections.defaultdict(list))
    breakdown=collections.defaultdict(lambda:collections.Counter())
    requests=collections.Counter()
    diagnostics=[]; seen_records=set()
    providers=set();models=set()
    for rec in records:
        tid=rec['task_id']
        if tid not in tasks or tasks[tid]['split'] != 'dev':
            raise ValueError('dev records only')
        version=rec.get('agent_version','unknown')
        key=(version,tid,rec.get('trial',1))
        if key in seen_records: raise ValueError('duplicate version/task/trial')
        seen_records.add(key)
        providers.add(rec.get('provider'));models.add(rec.get('model'))
        g=rec.get('grader_v2')
        if g is None: raise ValueError('explicit unchanged grader_v2 checks required')
        passed=all(g.values());by[version][tid].append(passed)
        family=tasks[tid]['tags']['feature']
        breakdown[version][family+':runs']+=1
        breakdown[version][family+':passes']+=passed
        sig=signals(rec)
        diagnostics.append({'task_id':tid,'trial':rec.get('trial',1),'agent_version':version,'signals':sig})
    if len(providers)!=1 or len(models)!=1:
        raise ValueError('never pool different providers/models into one comparison')
    versions={}
    for ver,outcomes in by.items():
        rates=[sum(vals)/len(vals) for vals in outcomes.values()]
        versions[ver]={'runs':sum(map(len,outcomes.values())),'tasks':len(outcomes),
                       'grader_v2_task_mean':sum(rates)/len(rates),
                       'task_bootstrap_95pct':cluster_interval(rates),
                       'reliability':[reliability(outcomes,k) for k in (1,2,4)],
                       'by_feature':dict(breakdown[ver])}
    paired={}
    for ver in sorted(by):
        if ver=='v1' or 'v1' not in by: continue
        common=sorted(set(by['v1'])&set(by[ver]))
        deltas=[sum(by[ver][t])/len(by[ver][t])-sum(by['v1'][t])/len(by['v1'][t]) for t in common]
        paired['v1_to_'+ver]={'paired_tasks':len(common),'task_ids':common,
            'equal_trial_counts':all(len(by['v1'][t])==len(by[ver][t]) for t in common),
            'delta':sum(deltas)/len(deltas) if deltas else None,
            'task_bootstrap_95pct':cluster_interval(deltas),
            'scope':'paired observed dev tasks only; not full protocol unless complete'}
    return {'provider':next(iter(providers)),'model':next(iter(models)),
            'framing':'development diagnostic; scoring patterns were tuned on v1 evidence; selected claim patterns are not a validated hallucination rate',
            'versions':versions,'paired_deltas':paired,'diagnostics':diagnostics}


def queue(records, tasks, output):
    """Append deduplicated diagnostic cases. Never creates human verdicts."""
    path=Path(output);existing=set()
    if path.exists():
        existing={json.loads(l)['case_hash'] for l in path.read_text().splitlines() if l}
    added=0
    with path.open('a') as file:
        for rec in records:
            if tasks[rec['task_id']]['split']!='dev': raise ValueError('dev only')
            sig=signals(rec)
            if not any(sig.values()): continue
            evidence={k:rec.get(k) for k in ('task_id','trial','agent_version','provider','model','input','answer','trace','before','after')}
            hash_=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
            if hash_ in existing: continue
            file.write(json.dumps({'case_hash':hash_,'status':'awaiting_human_review','human_verdict':None,'signals':sig,'record':evidence})+'\n')
            existing.add(hash_);added+=1
    return added


def main():
    p=argparse.ArgumentParser();p.add_argument('traces');p.add_argument('--report',required=True);p.add_argument('--queue')
    a=p.parse_args()
    from run import load_tasks
    tasks={t['id']:t for t in load_tasks()}
    records=[json.loads(l) for l in Path(a.traces).read_text().splitlines() if l]
    if not records: raise ValueError('No observed traces; cannot report results')
    result=compare(records,tasks)
    Path(a.report).write_text(json.dumps(result,indent=2)+'\n')
    if a.queue: print('Review cases appended:',queue(records,tasks,a.queue))
    print('Versions:',', '.join(result['versions']))

if __name__=='__main__': main()
