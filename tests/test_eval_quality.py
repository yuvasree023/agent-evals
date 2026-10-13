import json,tempfile,unittest
from pathlib import Path
import eval_quality as q

class QualityTests(unittest.TestCase):
    def test_schema_type_bool_is_not_integer(self):
        trace=[{'tool':'refund_order','args':{'order_id':'O1015','amount':True,'confirmed':True},'output':{}}]
        self.assertIn('wrong_type:refund_order:amount',q.schema_findings(trace))
        trace[0]['args']['amount']=1
        self.assertEqual(q.schema_findings(trace),[])
        del trace[0]['args']['order_id']
        self.assertIn('missing_argument:refund_order:order_id',q.schema_findings(trace))

    def test_entities_follow_evidence_order(self):
        listed={'tool':'list_orders','args':{},'output':{'orders':[{'id':'O1015'}]}}
        lookup={'tool':'lookup_order','args':{'order_id':'O1015'},'output':{'order':{'id':'O1015'}}}
        self.assertEqual(q.entity_findings('Where is my order?','O1015',[listed,lookup]),[])
        self.assertIn('unsupported_argument_id:O1015',q.entity_findings('Where is my order?','O1015',[lookup,listed]))
        self.assertIn('unsupported_answer_id:O9999',q.entity_findings('O1015','O9999',[]))

    def test_reliability_known_values_and_insufficient_trials(self):
        vals={'a':[True,True,False,False]}
        self.assertEqual(q.reliability(vals,4)['all_k'],0)
        self.assertEqual(q.reliability(vals,4)['at_least_one'],1)
        self.assertAlmostEqual(q.reliability(vals,2)['all_k'],1/6)
        self.assertIsNone(q.reliability(vals,5)['all_k'])
        self.assertIsNone(q.cluster_interval([1]))
        self.assertEqual(q.cluster_interval([1,1]),[1,1])

    def rec(self,version='v1',provider='gemini'):
        return {'task_id':'TX','trial':1,'agent_version':version,'provider':provider,'model':'same','input':'Status O1015','answer':'Order O9999','trace':[], 'grader_v2':{'state':True,'response':True,'policy':True}}

    def test_no_mixed_model_or_holdout_or_duplicate(self):
        tasks={'TX':{'split':'dev','tags':{'feature':'status'}}}
        with self.assertRaises(ValueError):q.compare([self.rec(),self.rec('v2','groq')],tasks)
        with self.assertRaises(ValueError):q.compare([self.rec(),self.rec()],tasks)
        tasks['TX']['split']='holdout'
        with self.assertRaises(ValueError):q.compare([self.rec()],tasks)

    def test_partial_pairs_explicit_and_queue_dedup(self):
        tasks={'TX':{'split':'dev','tags':{'feature':'status'}}};rs=[self.rec(),self.rec('v2')]
        out=q.compare(rs,tasks)
        self.assertEqual(out['paired_deltas']['v1_to_v2']['paired_tasks'],1)
        self.assertIsNone(out['versions']['v1']['reliability'][1]['all_k'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'queue.jsonl'
            self.assertEqual(q.queue(rs,tasks,p),2)
            self.assertEqual(q.queue(rs,tasks,p),0)
            self.assertIsNone(json.loads(p.read_text().splitlines()[0])['human_verdict'])

if __name__=='__main__':unittest.main()
