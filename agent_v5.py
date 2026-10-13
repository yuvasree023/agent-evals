"""Unmeasured parameter-provenance candidate. v1-v4 stay unchanged.

Single-turn explicit-parameter policy guard. Address extraction deliberately
supports a narrow 'address to ...' syntax. Other forms ask for clarification;
substring inclusion alone does not establish destination intent.
"""
import json
import re
import agent_candidates as c
import providers
from support import Store

SYSTEM_V5 = c.SYSTEM_V4 + (
    " Never invent a replacement address. Address writes require an explicit "
    "new address in the customer's message, exactly matching the tool argument. "
    "For a malformed order ID ask for a valid O followed by four digits."
)


def requested_address(text):
    match = re.search(r'\baddress\s+to\s+(.+?)(?:[;\n]|$)', text, re.I)
    if not match:return None
    value=match.group(1).strip().rstrip('.')
    # Do not turn contradictory, missing or vague parameters into authorization.
    if re.search(r"\b(don't|do not|not|instead|or|maybe|same|current)\b", value, re.I):return None
    return value if len(value)>=5 else None


def parameter_error(text,call):
    if call['name']!='change_address':return None
    value=requested_address(text)
    if value is None or call['arguments'].get('address','').strip()!=value:
        return {'error':'v5_address_not_authorized',
                'detail':'No write executed. Ask the customer for the exact new address and confirmation; do not invent or reuse an address.'}
    return None


def run_task(task,provider,model,max_steps=8,cache_dir='.cache/llm',use_cache=True):
    env=Store(task['fixture']);text=task['input'];policy=env.call('get_policy')['policy']
    if not c.safety.order_ids(text):
        if re.search(r'\bO[A-Za-z0-9]+\b',text):
            return 'Please provide a valid order ID: O followed by four digits.',env,[]
        if re.search(r'where is my order',text,re.I):
            return 'Please provide your order ID.',env,[]
    messages=[{'role':'user','content':SYSTEM_V5+'\n\nPolicy:\n'+policy+'\n\nCustomer message:\n'+text}]
    answer=''
    for _ in range(max_steps):
        result=providers.chat(provider,model,messages,c.TOOL_SCHEMAS,cache_dir=cache_dir,use_cache=use_cache)
        messages.append({'role':'assistant','content':result['content'],'tool_calls':result['tool_calls'],'raw':result.get('raw')})
        if not result['tool_calls']:
            answer=result['content'];break
        for call in result['tool_calls']:
            blocked=c.safety.check_write(text,call)
            if blocked is None:blocked=parameter_error(text,call)
            if blocked is None:blocked=c.eligibility_error(call,env.trace)
            if blocked:
                output=blocked;env.trace.append({'tool':call['name'],'args':call['arguments'],'output':output,'gate':'v5:blocked'})
            else:output=env.call(call['name'],**call['arguments'])
            messages.append({'role':'tool','tool_call_id':call['id'],'name':call['name'],'content':json.dumps(output)})
    else:answer='Step limit reached; no final answer produced.'
    return c.finalize_v4(text,answer,env.trace),env,messages
