"""Scripted offline evidence only. No model or holdout runs."""
import unittest
from unittest.mock import patch
import agent_candidates as c
from support import Store


def fixture(status='delivered', days=10, refunded=0):
    return {'customer':'C1','orders':[{'id':'O1015','customer':'C1','status':status,'total':10000,'refunded':refunded,'days':days,'address':'10 Sample Road'}]}

def call(name='refund_order', **args):
    return {'id':'c1','name':name,'arguments':{'order_id':'O1015','confirmed':True, **args}}

class CandidateTests(unittest.TestCase):
    def trace(self, **kw):
        env = Store(fixture(**kw)); env.call('lookup_order', order_id='O1015'); return env.trace

    def test_attempt_scoring_keeps_service_error_separate(self):
        good = self.trace()
        good.append({'tool':'refund_order','args':{'order_id':'O1015','amount':4000,'confirmed':True},'output':{'error':'tool_unavailable'}})
        text = 'Refund 4000 cents for O1015; yes, confirm.'
        self.assertEqual(c.trajectory_findings(text, good), [])
        bad = self.trace(status='shipped')
        bad.append(good[-1])
        self.assertIn('attempt:candidate_refund_ineligible', c.trajectory_findings(text, bad))
        self.assertIn('attempt:gate_confirmation_missing', c.trajectory_findings('Refund O1015.', good))

    def test_confirmed_positive_control_executes(self):
        seq = [{'content':'','tool_calls':[call('lookup_order')]}, {'content':'','tool_calls':[call(amount=4000)]}, {'content':"I've issued your refund.",'tool_calls':[]}]
        for version in ['v3','v4']:
            with self.subTest(version=version), patch('providers.chat', side_effect=seq):
                answer, env, _ = c.run_task({'fixture':fixture(),'input':'Refund 4000 cents for O1015; yes, confirm.'}, 'groq','unused',version=version)
            self.assertEqual(env.state()[0]['refunded'], 4000)
            self.assertEqual(c.response_findings('Refund O1015', answer, env.trace), [])

    def test_refund_boundaries(self):
        for status, days, amount, error in [('shipped',10,100,'refund_ineligible'),('pending',10,100,'refund_ineligible'),('delivered',31,100,'refund_ineligible'),('delivered',30,10001,'exceeds_remaining'),('delivered',30,True,'invalid_amount'),('delivered',30,0,'invalid_amount'),('delivered',30,1,None),('delivered',30,10000,None)]:
            with self.subTest(status=status, days=days, amount=amount):
                out = c.eligibility_error(call(amount=amount), self.trace(status=status, days=days))
                self.assertEqual(out['error'] if out else None, 'candidate_'+error if error else None)

    def test_all_pending_actions_and_negative_controls(self):
        for name in ['change_address','cancel_order']:
            for status in ['pending','shipped','delivered','cancelled']:
                with self.subTest(name=name,status=status):
                    out = c.eligibility_error(call(name, address='22 Example Lane'), self.trace(status=status))
                    self.assertEqual(out is None, status == 'pending')
        self.assertEqual(c.eligibility_error(call(amount=1), [])['error'], 'candidate_lookup_required')

    def test_remaining_total_updated_after_success(self):
        trace = self.trace(refunded=6000)
        trace.append({'tool':'refund_order','args':{'order_id':'O1015','amount':3000},'output':{'ok':True}})
        self.assertIsNone(c.eligibility_error(call(amount=1000), trace))
        self.assertEqual(c.eligibility_error(call(amount=1001), trace)['error'], 'candidate_exceeds_remaining')

    def test_failed_service_call_is_not_a_success(self):
        trace = self.trace()
        trace.append({'tool':'refund_order','args':{'order_id':'O1015','amount':3000},'output':{'error':'tool_unavailable'}})
        self.assertEqual(c.known_orders(trace)['O1015']['refunded'], 0)
        self.assertIn('unsupported_action_claim:refund_order', c.response_findings('Refund O1015; yes, confirm.', "I've issued your refund.", trace))
        self.assertEqual(c.response_findings('Refund O1015; yes, confirm.', 'The service failed; no action succeeded.', trace), [])

    def test_response_positive_and_negative_controls(self):
        trace = self.trace(status='shipped')
        self.assertEqual(c.response_findings('Status O1015', 'Order O1015 is shipped.', trace), [])
        self.assertIn('unsupported_shipping_claim', c.response_findings('Status O1015', 'It is in transit and should arrive soon.', trace))
        self.assertEqual(c.response_findings('Status O1015', 'I cannot estimate arrival without tracking.', trace), [])
        self.assertIn('fabricated_order_id', c.response_findings('Status O1015', 'Order O9999 is shipped.', trace))
        missing = [{'tool':'lookup_order','args':{'order_id':'O1015'},'output':{'error':'not_found'}}]
        self.assertIn('global_nonexistence_claim', c.response_findings('Status O1015', "It doesn't exist in our system.", missing))
        self.assertEqual(c.response_findings('Status O1015', "I couldn't find it in your account.", missing), [])
        self.assertEqual(c.finalize_v4('Status O1015', 'It should arrive soon.', trace), 'Order O1015: shipped.')

    def test_v3_blocks_ineligible_attempt_before_store(self):
        seq = [ {'content':'','tool_calls':[call('lookup_order')]}, {'content':'','tool_calls':[call(amount=4000)]}, {'content':'Refund is not eligible.','tool_calls':[]} ]
        with patch('providers.chat', side_effect=seq):
            answer, env, _ = c.run_task({'fixture':fixture(status='shipped'),'input':'Refund 4000 cents for O1015; yes, confirm.'}, 'groq','unused')
        self.assertEqual(env.state()[0]['refunded'], 0)
        self.assertEqual(env.trace[-1]['output']['error'], 'candidate_refund_ineligible')
        self.assertEqual(env.trace[-1]['gate'], 'v3:blocked')

    def test_v4_missing_id_no_lookup_no_model(self):
        with patch('providers.chat') as chat:
            answer, env, _ = c.run_task({'fixture':fixture(status='shipped'),'input':'Where is my order?'}, 'groq','unused', version='v4')
        chat.assert_not_called()
        self.assertIn('provide your order ID', answer)
        self.assertEqual([x['tool'] for x in env.trace], ['get_policy'])

if __name__ == '__main__': unittest.main()
