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

import json, os
from unittest import mock
import providers

class ProviderTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("GROQ_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
    def messages(self):
        return [{"role":"user","content":"status of O1001?"}]
    def tools(self):
        return [{"name":"lookup_order","description":"Look up one order",
                 "parameters":{"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}}]
    def test_missing_key_refused(self):
        with self.assertRaises(providers.ProviderError):
            providers.chat("groq","openai/gpt-oss-120b",self.messages(),self.tools())
    def test_non_free_model_refused(self):
        os.environ["GROQ_API_KEY"]="test"
        with self.assertRaises(providers.ProviderError):
            providers.chat("groq","llama3-70b-8192",self.messages(),self.tools())
    def test_cache_deterministic_and_key_mixed(self):
        p1=providers._cache_path("/tmp/c","groq","m",{"a":1},"key-one")
        p2=providers._cache_path("/tmp/c","groq","m",{"a":1},"key-one")
        p3=providers._cache_path("/tmp/c","groq","m",{"a":1},"key-two")
        self.assertEqual(p1,p2)
        self.assertNotEqual(p1,p3)
    def test_groq_parse_tool_call(self):
        _,_,payload,parse=providers._groq_request("openai/gpt-oss-120b",self.messages(),self.tools(),"k")
        self.assertEqual(payload["tools"][0]["function"]["name"],"lookup_order")
        fake={"choices":[{"message":{"content":None,"tool_calls":[{"id":"c1","type":"function","function":{"name":"lookup_order","arguments":"{\"order_id\": \"O1001\"}"}}]}}],"usage":{"total_tokens":10}}
        out=parse(fake)
        self.assertEqual(out["tool_calls"][0]["arguments"],{"order_id":"O1001"})
    def test_gemini_parse_tool_call_and_raw_replay(self):
        _,_,payload,parse=providers._gemini_request("gemini-3.5-flash-lite",self.messages(),self.tools(),"k")
        decl=payload["tools"][0]["functionDeclarations"][0]
        self.assertEqual(decl["name"],"lookup_order")
        raw={"role":"model","parts":[{"functionCall":{"name":"lookup_order","args":{"order_id":"O1001"},"id":"call_1"},"thoughtSignature":"sig"}]}
        out=parse({"candidates":[{"content":raw}],"usageMetadata":{"totalTokenCount":5}})
        self.assertEqual(out["tool_calls"][0]["name"],"lookup_order")
        replay=providers._gemini_content({"role":"assistant","content":"","tool_calls":out["tool_calls"],"raw":out["raw"]})
        self.assertEqual(replay["parts"][0]["thoughtSignature"],"sig")
    def test_gemini_tool_response_shape(self):
        m=providers._gemini_content({"role":"tool","tool_call_id":"call_1","name":"lookup_order","content":"{\"order\": {}}"})
        part=m["parts"][0]["functionResponse"]
        self.assertEqual(part["name"],"lookup_order")
        self.assertEqual(part["id"],"call_1")
    def test_retry_after_honored(self):
        os.environ["GROQ_API_KEY"]="test"
        err=urllib_error=__import__("urllib.error",fromlist=["HTTPError"]).HTTPError
        e=err("https://x",429,"rate",hdrs=__import__("email").message_from_string("retry-after: 0\r\n\r\n"),fp=open("/dev/null","rb"))
        good=mock.MagicMock(); good.status=200; good.headers={}
        good.read.return_value=json.dumps({"choices":[{"message":{"content":"ok","tool_calls":[]}}],"usage":{}}).encode()
        good.__enter__.return_value=good
        providers._last_call.clear()
        with mock.patch("urllib.request.urlopen",side_effect=[e,good]):
            with mock.patch("time.sleep") as s:
                out=providers.chat("groq","openai/gpt-oss-120b",self.messages(),self.tools(),cache_dir="/tmp/c-test",use_cache=False)
        self.assertEqual(out["content"],"ok")
        self.assertIn(mock.call(0.0),s.call_args_list)
    def test_rpd_zero_raises_quota(self):
        os.environ["GROQ_API_KEY"]="test"
        err=__import__("urllib.error",fromlist=["HTTPError"]).HTTPError
        e=err("https://x",429,"rate",hdrs=__import__("email").message_from_string("x-ratelimit-remaining-requests: 0\r\n\r\n"),fp=open("/dev/null","rb"))
        providers._last_call.clear()
        with mock.patch("urllib.request.urlopen",side_effect=e):
            with self.assertRaises(providers.DailyQuotaExhausted):
                providers.chat("groq","openai/gpt-oss-120b",self.messages(),self.tools(),cache_dir="/tmp/c-test",use_cache=False)
    def test_holdout_blocked_for_model_agents(self):
        import run
        with self.assertRaises(RuntimeError):
            run.run_live([],type("A",(),{"split":"holdout","agent":"groq","model":"openai/gpt-oss-120b","cache_dir":"/tmp/c"})(),{"max_steps":8})
