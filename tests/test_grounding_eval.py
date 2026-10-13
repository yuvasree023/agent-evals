import unittest
from copy import deepcopy
import grounding_eval as g

class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.r={'case':'X','input':'Status O1001?','answer':'It is shipped.','trace':[{'tool':'lookup_order','args':{'order_id':'O1001'},'output':{'order':{'status':'shipped'}}}]}
        self.a=g.blank([self.r])[0]
        self.a.update(reference_reviewer='fixture',claim_reviewer='fixture',reference_tool_sequences=[[{'tool':'lookup_order','args':{'order_id':'O1001'}}]],claims=[{'claim_id':'1','text':'shipped','start':6,'end':13,'support':'supported','reason':'Observed status','evidence':['trace:0']}])
    def test_blank_not_label(self):
        a=g.blank([self.r])[0];self.assertIsNone(a['claims']);self.assertIsNone(a['reference_tool_sequences'])
        with self.assertRaises(ValueError):g.analyze([self.r],[a])
    def test_exact(self):
        x=g.analyze([self.r],[self.a]);self.assertEqual(x['macro_tool_precision'],1);self.assertEqual(x['claim_support_rate_all'],1)
    def test_duplicates_penalized(self):
        x=g.tool_score(self.r['trace']*2,self.r['trace']);self.assertEqual(x['precision'],.5);self.assertEqual(x['recall'],1)
    def test_argument_mismatch(self):
        a=deepcopy(self.r['trace']);a[0]['args']['order_id']='O1002';self.assertEqual(g.tool_score(a,self.r['trace'])['f1'],0)
    def test_empty(self):
        self.assertEqual(g.tool_score([],[])['f1'],1);self.assertEqual(g.tool_score(self.r['trace'],[])['f1'],0)
    def test_fingerprint(self):
        r=deepcopy(self.r);r['answer']='Changed'
        with self.assertRaises(ValueError):g.analyze([r],[self.a])
    def test_claim_span_and_evidence(self):
        for field,value in [('start',0),('evidence',[]),('support',None)]:
            a=deepcopy(self.a);a['claims'][0][field]=value
            with self.assertRaises(ValueError):g.analyze([self.r],[a])
    def test_unknown_and_alternatives(self):
        a=deepcopy(self.a);a['claims'][0]['support']='unknown';a['reference_tool_sequences'].insert(0,[])
        x=g.analyze([self.r],[a]);self.assertEqual(x['per_case'][0]['selected_reference_alternative'],1);self.assertEqual(x['claim_review_coverage'],0);self.assertIsNone(x['claim_support_rate_known'])
    def test_trimmed_ledger_rejected(self):
        r=deepcopy(self.r);r['source_trace_sha256']='test';a=deepcopy(self.a);a['evidence_sha256']=g.fingerprint(r)
        with self.assertRaises(ValueError):g.analyze([r],[a])
    def test_duplicate_and_coverage(self):
        with self.assertRaises(ValueError):g.blank([self.r,self.r])
        with self.assertRaises(ValueError):g.analyze([self.r],[])

if __name__=='__main__':unittest.main()
