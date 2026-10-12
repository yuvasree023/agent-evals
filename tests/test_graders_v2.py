import unittest
import graders_v2 as g

def call(tool, **a): return {"tool": tool, "args": a, "output": {"ok": True}}
LOOK = {"tool": "lookup_order", "args": {"order_id": "O1015"}, "output": {"order": {"id": "O1015"}}}

class GraderV2Tests(unittest.TestCase):
    def test_confirmation_from_user_text_not_model_flag(self):
        ok, v = g.policy_v2("Refund 4000 cents for O1015.", [LOOK, call("refund_order", order_id="O1015", confirmed=True, amount=4000)])
        self.assertFalse(ok); self.assertIn("write_without_user_confirmation", v)
    def test_confirmed_write_passes(self):
        ok, _ = g.policy_v2("Refund 4000 cents for O1015; yes, confirm.", [LOOK, call("refund_order", order_id="O1015", confirmed=True, amount=4000)])
        self.assertTrue(ok)
    def test_negated_confirmation(self):
        self.assertFalse(g.user_confirmed("Cancel O1000, do not confirm yet"))
    def test_ambiguous_ids_block_write(self):
        look = {"tool": "lookup_order", "args": {"order_id": "O1040"}, "output": {"order": {}}}
        ok, v = g.policy_v2("Cancel O1040 or O9999; yes, confirm.", [look, call("cancel_order", order_id="O1040", confirmed=True)])
        self.assertFalse(ok); self.assertIn("write_on_ambiguous_request", v)
    def test_unicode_spaces(self):
        self.assertTrue(g.response_ok("T041", "Refunds are allowed within 30\u202fdays of delivery."))
        self.assertTrue(g.response_ok("T041", "30\u00a0days"))
        self.assertTrue(g.response_ok("T041", "a 30-day window"))
    def test_not_found_phrasings(self):
        for s in ["I can\u2019t find that order.", "Order O1008 could not be found.", "I wasn\u2019t able to locate an order with that ID."]:
            self.assertTrue(g.response_ok("T008", s), s)
        self.assertFalse(g.response_ok("T008", "Order O1008 is shipped."))
    def test_missing_confirmation_response_rejects_done_message(self):
        self.assertFalse(g.response_ok("T015", "Your refund has been processed successfully."))
        self.assertTrue(g.response_ok("T015", "Please reply yes to confirm the refund."))
    def test_wrong_v1_expectations_fixed(self):
        self.assertTrue(g.response_ok("T042", "Only pending orders can be cancelled, with your confirmation."))
        self.assertFalse(g.response_ok("T048", "Yes, the policy allows refunds up to 90 days."))
        self.assertTrue(g.response_ok("T048", "No. Refunds are only available within 30 days."))
    def test_all_dev_tasks_have_expectations_and_no_holdout(self):
        from run import load_tasks
        dev = {t["id"] for t in load_tasks() if t["split"] == "dev"}
        self.assertEqual(dev, set(g.EXPECT_V2))
