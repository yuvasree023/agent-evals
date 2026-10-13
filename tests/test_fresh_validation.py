import unittest
import fresh_validation as v
class FreshValidationTests(unittest.TestCase):
    def rows(self):
        rs=[{'case':'V01','answer':'x'},{'case':'V02','answer':'y'}]
        human=[{'case':r['case'],'trace_sha256':v.digest(r),'verdict':lab} for r,lab in zip(rs,['FAIL','PASS'])]
        return rs,human
    def test_failure_positive_and_unknown_denominators(self):
        rs,h=self.rows();j=[dict(x) for x in h]
        m=v.evaluate(rs,h,j);self.assertEqual(m['failure_detection_tpr'],1);self.assertEqual(m['kappa'],1)
        h[0]['verdict']='PASS';j[0]['verdict']='PASS'
        self.assertIsNone(v.evaluate(rs,h,j)['failure_detection_tpr'])
    def test_missing_blank_or_wrong_trace_rejected(self):
        rs,h=self.rows();j=[dict(x) for x in h]
        with self.assertRaises(ValueError):v.evaluate(rs,h,j[:1])
        j[0]['verdict']=None
        with self.assertRaises(ValueError):v.evaluate(rs,h,j)
        j[0]['verdict']='FAIL';j[0]['trace_sha256']='wrong'
        with self.assertRaises(ValueError):v.evaluate(rs,h,j)
if __name__=='__main__':unittest.main()
