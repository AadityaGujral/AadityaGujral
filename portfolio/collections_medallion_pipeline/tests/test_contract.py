import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class PipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((ROOT/'data/generation_metadata.json').read_text())
        cls.batch=json.loads((ROOT/'outputs/batch_metrics.json').read_text())
        cls.summary=json.loads((ROOT/'outputs/portfolio_summary.json').read_text())
        cls.validation=json.loads((ROOT/'outputs/validation.json').read_text())
    def test_two_batches(self):self.assertEqual([x['batch'] for x in self.batch],['batch_01','batch_02'])
    def test_exact_quarantine(self):self.assertEqual(sum(x['quarantined_rows'] for x in self.batch),3)
    def test_final_event_grain(self):self.assertEqual(self.batch[-1]['silver_rows_after_merge'],self.meta['canonical_events'])
    def test_unique_event_keys(self):self.assertEqual(self.batch[-1]['silver_rows_after_merge'],self.batch[-1]['distinct_event_ids_after_merge'])
    def test_event_subtotals(self):self.assertEqual(self.summary['events'],self.summary['payment_events']+self.summary['contact_events'])
    def test_balance_identity(self):self.assertEqual(self.summary['starting_balance_cents'],self.summary['payments_cents']+self.summary['remaining_balance_cents'])
    def test_all_independent_checks(self):self.assertTrue(all(self.validation['checks'].values()))
    def test_seed_fixed(self):self.assertEqual(self.meta['seed'],20261012)

if __name__=='__main__':unittest.main()
