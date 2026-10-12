"""Offline environment and smoke baseline. No model calls or expected labels."""
import re
import sqlite3

TOOLS = ("lookup_order", "list_orders", "refund_order", "change_address",
         "cancel_order", "get_policy")

class Store:
    def __init__(self, fixture):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, customer TEXT, status TEXT, total INTEGER, refunded INTEGER, days INTEGER, address TEXT)")
        self.db.executemany("INSERT INTO orders VALUES (:id,:customer,:status,:total,:refunded,:days,:address)", fixture["orders"])
        self.customer = fixture["customer"]
        self.errors = fixture.get("tool_errors", [])
        self.trace = []
        self.seen = set()

    def state(self):
        return [dict(x) for x in self.db.execute("SELECT * FROM orders ORDER BY id")]

    def call(self, name, **args):
        result = self._call(name, args)
        self.trace.append({"tool": name, "args": args, "output": result})
        return result

    def _call(self, name, a):
        if name not in TOOLS:
            return {"error": "unknown_tool"}
        if name in self.errors:
            return {"error": "tool_unavailable"}
        if name == "get_policy":
            from pathlib import Path
            return {"policy": Path(__file__).with_name("policy.md").read_text()}
        if name == "list_orders":
            return {"orders": [x for x in self.state() if x["customer"] == self.customer]}
        oid = a.get("order_id", "")
        if not re.fullmatch(r"O[0-9]{4}", str(oid)):
            return {"error": "invalid_id"}
        row = self.db.execute("SELECT * FROM orders WHERE id=? AND customer=?", (oid,self.customer)).fetchone()
        if row is None:
            return {"error": "not_found"}
        o = dict(row)
        if name == "lookup_order":
            self.seen.add(oid)
            return {"order": o}
        if oid not in self.seen:
            return {"error": "lookup_required"}
        if a.get("confirmed") is not True:
            return {"error": "confirmation_required"}
        if name == "refund_order":
            amount = a.get("amount")
            if type(amount) is not int or amount <= 0:
                return {"error": "invalid_amount"}
            if o["status"] != "delivered" or o["days"] > 30:
                return {"error": "refund_ineligible"}
            if amount > o["total"] - o["refunded"]:
                return {"error": "exceeds_remaining"}
            self.db.execute("UPDATE orders SET refunded=refunded+? WHERE id=?", (amount,oid))
        elif name == "change_address":
            if o["status"] != "pending":
                return {"error": "address_ineligible"}
            address = a.get("address")
            if not isinstance(address,str) or len(address.strip()) < 5:
                return {"error": "invalid_address"}
            self.db.execute("UPDATE orders SET address=? WHERE id=?", (address.strip(),oid))
        elif name == "cancel_order":
            if o["status"] != "pending":
                return {"error": "cancel_ineligible"}
            self.db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
        return {"ok": True}


def baseline(text, store, max_steps=8):
    """Limited regex baseline. It does not read task.expected or task.tags."""
    lower = text.lower()
    if "policy" in lower or "window" in lower:
        result = store.call("get_policy")
        return result.get("policy", "Tool unavailable; no action taken.")
    ids = re.findall(r"\bO[0-9]{4}\b", text)
    if len(ids) != 1:
        store.call("list_orders")
        return "Please provide one order ID to clarify. No action taken."
    oid = ids[0]
    result = store.call("lookup_order", order_id=oid)
    if "error" in result:
        return result["error"] + "; no action taken."
    if "payment" in lower:
        return "Payment-method changes are unsupported. No action taken."
    confirmed = bool(re.search(r"\b(yes|confirm)\b", lower))
    if "refund" in lower:
        amount = re.search(r"(\d+) cents", lower)
        if not amount:
            return "Please provide the refund amount in cents. No action taken."
        name, args = "refund_order", {"amount": int(amount.group(1))}
    elif "address" in lower:
        match = re.search(r"address to (.+?)(?:[.;]|$)", text, re.I)
        name, args = "change_address", {"address": match.group(1).strip() if match else ""}
    elif "cancel" in lower:
        name, args = "cancel_order", {}
    else:
        return "Order status: " + result["order"]["status"]
    if len(store.trace) >= max_steps:
        return "Step limit; no action taken."
    result = store.call(name, order_id=oid, confirmed=confirmed, **args)
    return "Action completed." if result.get("ok") else result["error"] + "; no action taken."
