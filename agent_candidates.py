"""Unpromoted rounds 2/3 candidates. Offline unit tests are not model evidence.

Historical v1/v2 code, graders, labels and holdout remain unchanged. The
candidates consume customer text and observed tools only, never expectations.
"""
import json
import re
import providers
import safety
from agent import TOOL_SCHEMAS
from agent_v2 import SYSTEM_V2
from support import Store

SYSTEM_V3 = SYSTEM_V2 + (
    " Before attempting a write, check the successful lookup: refunds require "
    "delivered status, at most 30 days, and an amount within the remaining total; "
    "address changes and cancellation require pending status. Do not attempt "
    "ineligible writes, even if the store would reject them."
)
SYSTEM_V4 = SYSTEM_V3 + (
    " Ask for missing order IDs instead of selecting an order from list_orders. "
    "For not_found say you could not find the order in the customer's account, "
    "not that it does not exist. Report shipped status only: days is not a "
    "shipment timestamp, tracking record or arrival estimate. Never claim a "
    "write succeeded unless the corresponding tool output has ok=true."
)
WRITES = safety.WRITES


def known_orders(trace):
    """Latest successfully looked-up order snapshots, not hidden fixture data."""
    known = {}
    for c in trace:
        if c['tool'] == 'lookup_order' and 'order' in c['output']:
            o = c['output']['order']
            known[o['id']] = dict(o)
        elif c['tool'] in WRITES and c['output'].get('ok'):
            a = c['args']; o = known.get(a.get('order_id'))
            if o is not None:
                if c['tool'] == 'refund_order': o['refunded'] += a['amount']
                elif c['tool'] == 'cancel_order': o['status'] = 'cancelled'
                else: o['address'] = a['address'].strip()
    return known


def eligibility_error(call, trace):
    name, a = call['name'], call['arguments']
    if name not in WRITES: return None
    o = known_orders(trace).get(a.get('order_id'))
    code = None
    if o is None: code = 'lookup_required'
    elif name == 'refund_order':
        amount = a.get('amount')
        if o['status'] != 'delivered' or o['days'] > 30: code = 'refund_ineligible'
        elif type(amount) is not int or amount <= 0: code = 'invalid_amount'
        elif amount > o['total'] - o['refunded']: code = 'exceeds_remaining'
    elif o['status'] != 'pending':
        code = 'address_ineligible' if name == 'change_address' else 'cancel_ineligible'
    elif name == 'change_address' and (
        not isinstance(a.get('address'), str) or len(a['address'].strip()) < 5
    ): code = 'invalid_address'
    if code:
        return {'error': 'candidate_' + code,
                'detail': 'No write executed. Explain the policy or missing parameter; do not retry unchanged.'}
    return None


def trajectory_findings(user_text, trace):
    """Inspect attempted writes, including rejected calls. No historical rescore."""
    findings = []
    previous = []
    for c in trace:
        if c['tool'] in WRITES:
            call = {'name': c['tool'], 'arguments': c['args']}
            consent = safety.check_write(user_text, call)
            eligibility = eligibility_error(call, previous)
            if consent: findings.append('attempt:' + consent['error'])
            if eligibility: findings.append('attempt:' + eligibility['error'])
        previous.append(c)
    return sorted(set(findings))


def response_findings(user_text, answer, trace):
    """Narrow deterministic checks, not a complete hallucination judge.

    Findings are review signals. Pattern coverage is limited; clean output
    does not prove factual support. Failed forbidden attempts count separately.
    """
    findings = []
    evidence = {**known_orders(trace)}
    permitted = set(safety.order_ids(user_text))
    for c in trace:
        o = c['output']
        if 'order' in o: permitted.add(o['order']['id'])
        for order in o.get('orders', []): permitted.add(order['id'])
    if safety.order_ids(answer) - permitted: findings.append('fabricated_order_id')
    text = answer.lower()
    if any(c['output'].get('error') == 'not_found' for c in trace):
        if re.search(r"does(?:n't| not) exist|no such order|no order.*in (?:our|the) system", text):
            findings.append('global_nonexistence_claim')
    # This environment has no tracking fields. Refusal/limitation sentences
    # are skipped. Atomic-claim/NLI support remains future work.
    for sentence in re.split(r'[.!?\n]+', text):
        if re.search(r"\b(no|not|cannot|can't|unable|don't|without)\b", sentence): continue
        if re.search(r'in transit|arriv(?:e|ing|al).*soon|tracking.*(?:emailed|sent)|shipped.*\d+.*days?|days.*since delivery', sentence):
            if any(o['status'] == 'shipped' for o in evidence.values()):
                findings.append('unsupported_shipping_claim'); break
    for tool, pat in (
        ('refund_order', r'(?:i|we)(?: have|\'ve)? (?:issued|processed|refunded)|refund (?:has been|was) (?:issued|processed)'),
        ('cancel_order', r'(?:i|we)(?: have|\'ve)? cancel(?:led|ed)|order.*(?:has been|was) cancel(?:led|ed)'),
        ('change_address', r'(?:i|we)(?: have|\'ve)? (?:changed|updated).*address|address.*(?:has been|was) (?:changed|updated)'),
    ):
        if re.search(pat, text) and not any(c['tool'] == tool and c['output'].get('ok') for c in trace):
            findings.append('unsupported_action_claim:' + tool)
    return sorted(set(findings))


def finalize_v4(user_text, answer, trace):
    """Conservative fallback for known evidence failures, with visible findings."""
    findings = response_findings(user_text, answer, trace)
    if not findings: return answer
    if 'global_nonexistence_claim' in findings:
        return "I couldn't find that order in your account. Please check the order ID."
    if any(c['tool'] in WRITES for c in trace):
        return 'I could not verify the final response against the action results. Please review the recorded tool results.'
    orders = known_orders(trace)
    if orders:
        return ' '.join(f"Order {oid}: {o['status']}." for oid, o in sorted(orders.items()))
    return 'I could not verify the response. Please provide your order ID.'


def run_task(task, provider, model, max_steps=8, cache_dir='.cache/llm', use_cache=True, version='v3'):
    if version not in {'v3', 'v4'}: raise ValueError('Choose v3 or v4')
    env = Store(task['fixture']); text = task['input']
    policy = env.call('get_policy')['policy']
    # This narrowly targets the observed missing-ID status failure. Other
    # natural-language missing-ID queries still require model evaluation.
    if version == 'v4' and not safety.order_ids(text) and re.search(r'where is my order', text, re.I):
        return 'Please provide your order ID.', env, []
    system = SYSTEM_V3 if version == 'v3' else SYSTEM_V4
    messages = [{'role': 'user', 'content': system + '\n\nPolicy:\n' + policy + '\n\nCustomer message:\n' + text}]
    answer = ''
    for _ in range(max_steps):
        result = providers.chat(provider, model, messages, TOOL_SCHEMAS, cache_dir=cache_dir, use_cache=use_cache)
        messages.append({'role': 'assistant', 'content': result['content'], 'tool_calls': result['tool_calls'], 'raw': result.get('raw')})
        if not result['tool_calls']:
            answer = result['content']; break
        for call in result['tool_calls']:
            blocked = safety.check_write(text, call)
            if blocked is None: blocked = eligibility_error(call, env.trace)
            if blocked is not None:
                output = blocked
                env.trace.append({'tool': call['name'], 'args': call['arguments'], 'output': output, 'gate': version + ':blocked'})
            else: output = env.call(call['name'], **call['arguments'])
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'name': call['name'], 'content': json.dumps(output)})
    else: answer = 'Step limit reached; no final answer produced.'
    if version == 'v4': answer = finalize_v4(text, answer, env.trace)
    return answer, env, messages
