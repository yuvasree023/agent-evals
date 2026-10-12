"""Confirmation gate for write tools (agent v2, improvement round 1).

Policy.md: refunds, address changes and cancellations require explicit
confirmation in the customer request, and a missing or ambiguous order ID
requires clarification. In this single-turn fixture, confirmation is an
explicit yes/confirm in the customer's own message; the model's confirmed
argument is never evidence. A request naming several order IDs is ambiguous
and must be clarified before any write.

check_write sits between the model and the environment. A blocked write is
never executed; the model gets a synthetic tool error telling it to ask the
customer instead. graders_v2.policy_v2 scores the same rules from saved
traces; the two must stay consistent (same regex definitions by import).
"""
import graders_v2 as g2

WRITES = g2.WRITES
user_confirmed = g2.user_confirmed
order_ids = g2.order_ids

def check_write(user_text, call):
    """Return a synthetic tool-error dict if the write is blocked, else None.

    Only called for model tool calls; never sees expected answers or tags.
    """
    name = call["name"]
    if name not in WRITES:
        return None
    ids = order_ids(user_text)
    oid = str(call["arguments"].get("order_id", ""))
    if len(ids) > 1:
        return {"error": "gate_ambiguous_request",
                "detail": ("Blocked by the confirmation gate: the customer "
                           "named several order IDs (" + ", ".join(sorted(ids)) +
                           "). Do not retry this write. Ask the customer which "
                           "order they mean and wait for their answer.")}
    if not user_confirmed(user_text):
        return {"error": "gate_confirmation_missing",
                "detail": ("Blocked by the confirmation gate: the customer's "
                           "message has no explicit yes/confirm. Do not retry "
                           "this write and do not set confirmed=true yourself. "
                           "Ask the customer to confirm, then stop.")}
    if oid not in ids:
        return {"error": "gate_id_not_in_request",
                "detail": ("Blocked by the confirmation gate: " + (oid or "this order") +
                           " is not an order ID from the customer's message. "
                           "Do not retry this write. Ask the customer for the "
                           "order ID they mean.")}
    return None
