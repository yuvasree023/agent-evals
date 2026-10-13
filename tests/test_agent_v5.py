import unittest
from unittest.mock import patch
import agent_v5 as v
class V5Tests(unittest.TestCase):
    def call(self,address):return {'id':'a','name':'change_address','arguments':{'order_id':'O1030','confirmed':True,'address':address}}
    def fixture(self):return {'customer':'C1','orders':[{'id':'O1030','customer':'C1','status':'pending','total':10000,'refunded':0,'days':10,'address':'10 Sample Road'}]}
    def test_no_address_or_invented_address_blocked(self):
        for address in ['New Address','10 Sample Road','22 Example Lane']:
            self.assertEqual(v.parameter_error('Change address for O1030; yes, confirm.',self.call(address))['error'],'v5_address_not_authorized')
    def test_positive_exact_parameter_and_mismatch(self):
        text='Change O1030 address to 22 Example Lane; yes, confirm.'
        self.assertIsNone(v.parameter_error(text,self.call('22 Example Lane')))
        self.assertIsNotNone(v.parameter_error(text,self.call('33 Different Road')))
        self.assertIsNone(v.requested_address('Change address to same current address; yes, confirm.'))
    def test_t030_script_cannot_write(self):
        seq=[{'content':'','tool_calls':[{'id':'l','name':'lookup_order','arguments':{'order_id':'O1030'}}],'raw':{}}, {'content':'','tool_calls':[self.call('New Address')],'raw':{}}, {'content':'Please provide your new address.','tool_calls':[],'raw':{}}]
        with patch('providers.chat',side_effect=seq):
            answer,env,_=v.run_task({'fixture':self.fixture(),'input':'Change address for O1030; yes, confirm.'},'gemini','unused')
        self.assertEqual(env.state()[0]['address'],'10 Sample Road');self.assertEqual(env.trace[-1]['output']['error'],'v5_address_not_authorized');env.db.close()
    def test_malformed_id_no_model(self):
        for text in ['Cancel OABC; yes, confirm.','Refund O123; yes, confirm.']:
            with patch('providers.chat') as chat:
                answer,env,_=v.run_task({'fixture':self.fixture(),'input':text},'gemini','unused')
            chat.assert_not_called();self.assertIn('valid order ID',answer);env.db.close()
if __name__=='__main__':unittest.main()
