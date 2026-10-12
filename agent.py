"""Plain model -> tool -> result loop over the support environment.

The agent sees the task input, the policy, and tool schemas only. It never
sees expected answers, tags, or split information. Every model response and
tool result is appended to one internal transcript that providers.py maps to
each API's shape.
"""
import json
import providers
from support import Store

TOOL_SCHEMAS = [
    {"name": "lookup_order",
     "description": "Look up one order by its ID (format O followed by 4 digits). Must be called before any refund, address change, or cancellation of that order.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"]}},
    {"name": "list_orders",
     "description": "List the current customer's orders.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "refund_order",
     "description": "Refund an order, fully or partially, per policy. Requires a prior lookup and confirmed=true once the customer has confirmed.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"},
                                   "amount": {"type": "integer",
                                              "description": "refund amount in cents"},
                                   "confirmed": {"type": "boolean"}},
                    "required": ["order_id", "amount", "confirmed"]}},
    {"name": "change_address",
     "description": "Change the delivery address of a pending order. Requires a prior lookup and confirmed=true once the customer has confirmed.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"},
                                   "address": {"type": "string"},
                                   "confirmed": {"type": "boolean"}},
                    "required": ["order_id", "address", "confirmed"]}},
    {"name": "cancel_order",
     "description": "Cancel a pending order. Requires a prior lookup and confirmed=true once the customer has confirmed.",
     "parameters": {"type": "object",
                    "properties": {"order_id": {"type": "string"},
                                   "confirmed": {"type": "boolean"}},
                    "required": ["order_id", "confirmed"]}},
    {"name": "get_policy",
     "description": "Read the current support policy.",
     "parameters": {"type": "object", "properties": {}}},
]

SYSTEM = (
    "You are a customer support agent for a small online store. Answer the "
    "customer and act through the tools. Rules: look up an order before "
    "changing it; mutating tools need confirmed=true only after the customer "
    "explicitly confirmed; follow the policy from get_policy exactly, "
    "including eligibility windows; if the request is unclear or unsupported, "
    "ask or say no instead of guessing; never invent order IDs, amounts, or "
    "policy terms. Reply briefly when done."
)


def run_task(task, provider, model, max_steps=8, cache_dir=".cache/llm"):
    env = Store(task["fixture"])
    policy = env.call("get_policy")["policy"]
    messages = [
        {"role": "user", "content": SYSTEM + "\n\nPolicy:\n" + policy +
         "\n\nCustomer message:\n" + task["input"]},
    ]
    answer, steps = "", 0
    while steps < max_steps:
        steps += 1
        result = providers.chat(provider, model, messages, TOOL_SCHEMAS,
                                cache_dir=cache_dir)
        assistant = {"role": "assistant", "content": result["content"],
                     "tool_calls": result["tool_calls"], "raw": result["raw"]}
        messages.append(assistant)
        if not result["tool_calls"]:
            answer = result["content"]
            break
        for call in result["tool_calls"]:
            output = env.call(call["name"], **call["arguments"])
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "name": call["name"],
                             "content": json.dumps(output)})
    else:
        answer = "Step limit reached; no final answer produced."
    # Traces store the transcript without any key material; raw model turns
    # contain only message content.
    return answer, env, messages
