import json,tempfile,unittest
from pathlib import Path
import regression_suite as r
class RegressionSuiteTests(unittest.TestCase):
    def test_scripted_regressions_pass_without_provider(self):
        rows=r.load();self.assertEqual(len(rows),12)
        self.assertTrue(all(r.evaluate(c)['passed'] for c in rows))
    def test_duplicate_and_nondev_rejected(self):
        row=r.load()[0]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tasks.jsonl';p.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
            with self.assertRaises(ValueError):r.load(p)
            row['split']='holdout';p.write_text(json.dumps(row)+'\n')
            with self.assertRaises(ValueError):r.load(p)
if __name__=='__main__':unittest.main()
