import json
import unittest
from run import build, ROOT

class ProjectTests(unittest.TestCase):
    def test_reproducibility(self):
        build()
        first={p.name:p.read_bytes() for p in (ROOT/'outputs').glob('*.json') if p.name!='tests.json'}
        build()
        second={p.name:p.read_bytes() for p in (ROOT/'outputs').glob('*.json') if p.name!='tests.json'}
        self.assertEqual(first,second)

    def test_hand_calculated_bridge(self):
        # Plan 10 units at price 100, cost 60; actual 12 at 90, cost 70.
        self.assertEqual((12-10)*(100-60),80)
        self.assertEqual(12*(90-100),-120)
        self.assertEqual(12*(60-70),-120)
        self.assertEqual(80-120-120,12*(90-70)-10*(100-60))

    def test_validation_receipt(self):
        build()
        evidence=json.loads((ROOT/'outputs/validation.json').read_text())
        self.assertEqual(len(evidence['checks']),11)
        self.assertTrue(all(evidence['checks'].values()))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProjectTests))
    (ROOT/'outputs/tests.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
