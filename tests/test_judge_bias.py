import unittest
import judge_bias as b
class BiasTests(unittest.TestCase):
    def test_variants_preserve_trace_and_original(self):
        r={'case':'V01','input':'x','trace':[{'tool':'x'}],'answer':'Yes'}
        jobs=b.prepare([r],[{'case':'a'},{'case':'z'}])
        self.assertEqual(r['answer'],'Yes');self.assertEqual(jobs[2]['payload']['examples'][0]['case'],'z')
        self.assertEqual(jobs[3]['payload']['record']['trace'],r['trace'])
        self.assertEqual(jobs[3]['payload']['record']['answer'],'Yes\n\nYes\n\nYes')
    def test_blank_or_incomplete_rejected_and_flip(self):
        jobs=b.prepare([{'case':'V01','input':'x','trace':[],'answer':'Yes'}],[])
        with self.assertRaises(ValueError):b.analyze(jobs)
        for j in jobs:j['verdict']='PASS'
        jobs[2]['verdict']='FAIL';self.assertEqual(b.analyze(jobs)['variants']['reversed_examples']['flips'],1)
        with self.assertRaises(ValueError):b.analyze(jobs[:2])
if __name__=='__main__':unittest.main()
