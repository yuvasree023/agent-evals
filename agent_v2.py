"""Agent v2: same model -> tool -> result loop as agent.py, with the
confirmation gate from safety.py enforcing policy.md between the model and
the environment.

v1 relied on the model to pass confirmed=true honestly; the M1 rescore
(m1-rescore-v2-2026-10-12.md) showed it refunds, changes addresses and
cancels without a yes/confirm in the customer message, and cancels one of
two named orders instead of asking which. v2 keeps the loop and tool schemas
identical, adds one instruction sentence, and lets the gate reject a write
that lacks confirmation evidence in the customer message. A rejected write
is recorded in the trace with gate:"blocked" and never reaches the store.
"""
import json
import providers
import safety
from agent import TOOL_SCHEMAS, SYSTEM
from support import Store

SYSTEM_V2 = SYSTEM + (
    " A runtime confirmation gate rejects any refund, address change, or "
    "cancellation unless the customer's own message contains an explicit "
    "yes/confirm and names exactly one order ID, the one you pass. If the "
    "gate rejects a call, ask the customer to confirm or clarify instead of "
    "retrying the write."
)

GATE_VERSION = "2.0"


def run_task(task, provider, model, max_steps=8, cache_dir=".cache/llm", use_cache=True):
    env = Store(task["fixture"])
    policy = env.call("get_policy")["policy"]
    user_text = task["input"]
    messages = [
        {"role": "user", "content": SYSTEM_V2 + "\n\nPolicy:\n" + policy +
         "\n\nCustomer message:\n" + user_text},
    ]
    answer, steps = "", 0
    while steps < max_steps:
        steps += 1
        result = providers.chat(provider, model, messages, TOOL_SCHEMAS,
                                cache_dir=cache_dir, use_cache=use_cache)
        assistant = {"role": "assistant", "content": result["content"],
                     "tool_calls": result["tool_calls"], "raw": result["raw"]}
        messages.append(assistant)
        if not result["tool_calls"]:
            answer = result["content"]
            break
        for call in result["tool_calls"]:
            blocked = safety.check_write(user_text, call)
            if blocked is not None:
                output = blocked
                env.trace.append({"tool": call["name"], "args": call["arguments"],
                                  "output": output, "gate": "blocked"})
            else:
                output = env.call(call["name"], **call["arguments"])
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "name": call["name"],
                             "content": json.dumps(output)})
    else:
        answer = "Step limit reached; no final answer produced."
    # Traces store the transcript without any key material; raw model turns
    # contain only message content.
    return answer, env, messages
