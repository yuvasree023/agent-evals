import unittest
from unittest import mock
import safety
import agent_v2

FIXTURE = {"customer":"C1","orders":[
    {"id":"O1015","customer":"C1","status":"delivered","total":10000,"refunded":0,"days":10,"address":"10 Sample Road"},
    {"id":"O1040","customer":"C1","status":"pending","total":5000,"refunded":0,"days":1,"address":"10 Sample Road"}]}

def task(text):
    return {"id":"TX","split":"dev","input":text,"fixture":FIXTURE,
            "expected":{"unchanged":True,"state":[],"response_any":[]},"tags":{}}

def refund_call(order_id="O1015"):
    return {"id":"c1","name":"refund_order","arguments":{"order_id":order_id,"amount":4000,"confirmed":True}}

def fake_provider(calls_then_answer):
    """providers.chat stub: play scripted tool-call turns, then a final answer."""
    turns = list(calls_then_answer)
    def chat(provider, model, messages, tools, **kw):
        if turns:
            return {"content":"", "tool_calls":[turns.pop(0)], "usage":{}, "raw":{}}
        return {"content":"Asking the customer to confirm.", "tool_calls":[], "usage":{}, "raw":{}}
    return chat

class GateTests(unittest.TestCase):
    def test_allows_confirmed_single_id(self):
        self.assertIsNone(safety.check_write("Refund 4000 cents for O1015; yes, confirm.", refund_call()))
    def test_blocks_missing_confirmation(self):
        out = safety.check_write("Refund 4000 cents for O1015.", refund_call())
        self.assertEqual(out["error"], "gate_confirmation_missing")
    def test_blocks_negated_confirmation(self):
        out = safety.check_write("Refund O1015, but do not confirm anything.", refund_call())
        self.assertEqual(out["error"], "gate_confirmation_missing")
    def test_blocks_ambiguous_ids_even_when_confirmed(self):
        out = safety.check_write("Cancel O1040 or O9999; yes, confirm.",
                                 {"name":"cancel_order","arguments":{"order_id":"O1040","confirmed":True}})
        self.assertEqual(out["error"], "gate_ambiguous_request")
    def test_blocks_id_not_in_text(self):
        out = safety.check_write("Refund 4000 cents for O1015; yes, confirm.", refund_call("O1040"))
        self.assertEqual(out["error"], "gate_id_not_in_request")
    def test_ignores_read_tools(self):
        self.assertIsNone(safety.check_write("Where is my order?", {"name":"lookup_order","arguments":{"order_id":"O1015"}}))

class AgentV2LoopTests(unittest.TestCase):
    def test_unconfirmed_write_never_reaches_store(self):
        t = task("Refund 4000 cents for O1015.")
        with mock.patch("providers.chat", side_effect=fake_provider([refund_call()])):
            answer, env, messages = agent_v2.run_task(t, "groq", "m", use_cache=False)
        self.assertEqual(env.state()[0]["refunded"], 0)
        gated = [c for c in env.trace if c.get("gate") == "blocked"]
        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0]["output"]["error"], "gate_confirmation_missing")
        self.assertIn("confirm", answer)
    def test_confirmed_write_executes(self):
        t = task("Refund 4000 cents for O1015; yes, confirm.")
        seq = [ {"id":"c0","name":"lookup_order","arguments":{"order_id":"O1015"}}, refund_call() ]
        with mock.patch("providers.chat", side_effect=fake_provider(seq)):
            answer, env, messages = agent_v2.run_task(t, "groq", "m", use_cache=False)
        self.assertEqual(env.state()[0]["refunded"], 4000)
        self.assertFalse(any(c.get("gate") == "blocked" for c in env.trace))
    def test_ambiguous_cancel_blocked(self):
        t = task("Cancel O1040 or O9999; yes, confirm.")
        call = {"id":"c1","name":"cancel_order","arguments":{"order_id":"O1040","confirmed":True}}
        with mock.patch("providers.chat", side_effect=fake_provider([call])):
            answer, env, messages = agent_v2.run_task(t, "groq", "m", use_cache=False)
        self.assertEqual(env.state()[1]["status"], "pending")
        self.assertEqual(env.trace[-1]["output"]["error"], "gate_ambiguous_request")

if __name__ == "__main__":
    unittest.main()
