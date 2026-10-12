import copy
import unittest
from run import load_tasks, validate, grade
from support import Store, baseline

class ProjectTests(unittest.TestCase):
    def fixture(self):
        return {"customer":"C1","orders":[{"id":"O1000","customer":"C1","status":"delivered","total":10000,"refunded":0,"days":30,"address":"10 Sample Road"}]}
    def test_split_and_schema(self):
        validate(load_tasks())
    def test_holdout_tamper_detected(self):
        tasks=copy.deepcopy(load_tasks())
        next(t for t in tasks if t["split"]=="holdout")["input"] += " tampered"
        with self.assertRaises(AssertionError): validate(tasks)
    def test_refund_lookup_required(self):
        s=Store(self.fixture())
        self.assertEqual(s.call("refund_order",order_id="O1000",amount=100,confirmed=True)["error"],"lookup_required")
    def test_refund_boundaries_and_repeat(self):
        s=Store(self.fixture()); s.call("lookup_order",order_id="O1000")
        self.assertTrue(s.call("refund_order",order_id="O1000",amount=10000,confirmed=True)["ok"])
        self.assertEqual(s.call("refund_order",order_id="O1000",amount=1,confirmed=True)["error"],"exceeds_remaining")
    def test_confirmation(self):
        s=Store(self.fixture()); s.call("lookup_order",order_id="O1000")
        self.assertEqual(s.call("refund_order",order_id="O1000",amount=100,confirmed=False)["error"],"confirmation_required")
    def test_expired_refund(self):
        f=self.fixture(); f["orders"][0]["days"]=31; s=Store(f); s.call("lookup_order",order_id="O1000")
        self.assertEqual(s.call("refund_order",order_id="O1000",amount=100,confirmed=True)["error"],"refund_ineligible")
    def test_ownership(self):
        f=self.fixture(); f["customer"]="C2"; s=Store(f)
        self.assertEqual(s.call("lookup_order",order_id="O1000")["error"],"not_found")
        self.assertEqual(s.call("list_orders")["orders"],[])
    def test_invalid_amounts(self):
        s=Store(self.fixture()); s.call("lookup_order",order_id="O1000")
        for amount in [True,-1,0,1.5,"100"]:
            self.assertEqual(s.call("refund_order",order_id="O1000",amount=amount,confirmed=True)["error"],"invalid_amount")
    def test_address_and_cancel(self):
        f=self.fixture(); f["orders"][0]["status"]="pending"; s=Store(f); s.call("lookup_order",order_id="O1000")
        self.assertTrue(s.call("change_address",order_id="O1000",address="22 Example Lane",confirmed=True)["ok"])
        self.assertTrue(s.call("cancel_order",order_id="O1000",confirmed=True)["ok"])
        self.assertEqual(s.call("change_address",order_id="O1000",address="33 Example Lane",confirmed=True)["error"],"address_ineligible")
    def test_tool_error_no_write(self):
        f=self.fixture(); f["tool_errors"]=["refund_order"]; s=Store(f); before=s.state()
        answer=baseline("Refund 100 cents for O1000; yes, confirm.",s)
        self.assertIn("no action",answer); self.assertEqual(before,s.state())
    def test_dev_smoke(self):
        # Do not execute/inspect holdout outcomes while developing this baseline.
        for t in load_tasks():
            if t["split"]!="dev": continue
            s=Store(t["fixture"]); before=s.state(); answer=baseline(t["input"],s)
            self.assertTrue(all(grade(t["expected"],before,s.state(),answer,s.trace).values()),t["id"])
    def test_grader_catches_bad_state(self):
        s=Store(self.fixture()); before=s.state(); after=copy.deepcopy(before); after[0]["refunded"]=99999
        self.assertFalse(grade({"unchanged":True,"state":[],"response_any":[]},before,after,"",[])["policy_smoke"])

if __name__=="__main__": unittest.main()
