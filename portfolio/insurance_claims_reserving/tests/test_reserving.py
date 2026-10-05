"""Meaningful deterministic analytical contract tests; no external test runner."""
import unittest
import numpy as np
import pandas as pd
from src.reserving import build_triangle,development_factors,project,validate_payments

class ReservingTests(unittest.TestCase):
    def setUp(self):
        # Ten known factors, with each later cohort one age less mature.
        cumulative=np.array([100,150,180,190,195,197,198,199,199.5,200.0])*100
        self.triangle=pd.DataFrame([np.where(np.arange(10)<=9-i,cumulative,np.nan) for i in range(10)],index=range(2016,2026))

    def test_known_ultimate(self):
        factors=development_factors(self.triangle)
        estimates,_=project(self.triangle,factors)
        np.testing.assert_allclose(estimates.ultimate_estimate_cents,20000,rtol=1e-12)

    def test_factor_uses_only_paired_origins(self):
        triangle=self.triangle.copy()
        triangle.loc[2025,0]=10**12
        factor=development_factors(triangle).iloc[0].factor
        self.assertAlmostEqual(factor,1.5)

    def test_missing_future_remains_missing(self):
        p=pd.DataFrame([[1,2025,'Auto',0,2025,100]],columns=['claim_id','accident_year','line','development_age','payment_year','payment_cents'])
        inc,cum=build_triangle(p,2025)
        self.assertEqual(cum.loc[2025,0],100)
        self.assertTrue(inc.loc[2025,1:].isna().all())
        self.assertTrue(cum.loc[2025,1:].isna().all())

    def test_no_future_leakage(self):
        p=pd.DataFrame([[1,2025,'Auto',1,2026,100]],columns=['claim_id','accident_year','line','development_age','payment_year','payment_cents'])
        with self.assertRaisesRegex(ValueError,'leakage'):validate_payments(p,2025)

    def test_unsupported_age_rejected(self):
        with self.assertRaises(ValueError):development_factors(self.triangle.iloc[-1:])

    def test_mature_origins_have_zero_base_reserve(self):
        estimates,_=project(self.triangle,development_factors(self.triangle))
        self.assertEqual(estimates.iloc[0].outstanding_estimate_cents,0)

    def test_stress_direction(self):
        factors=development_factors(self.triangle)
        base,_=project(self.triangle,factors)
        high,_=project(self.triangle,factors,excess_multiplier=1.05)
        self.assertTrue((high.outstanding_estimate_cents>=base.outstanding_estimate_cents).all())

    def test_tail_on_mature_cohort(self):
        estimates,_=project(self.triangle,development_factors(self.triangle),tail_factor=1.02)
        self.assertAlmostEqual(estimates.iloc[0].outstanding_estimate_cents,400)

if __name__=='__main__':unittest.main()
