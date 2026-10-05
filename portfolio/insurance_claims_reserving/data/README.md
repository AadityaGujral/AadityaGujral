# Synthetic input data

Run `python run_project.py` from the project directory to generate all inputs.

The CSV inputs are excluded from Git to keep the repository lightweight:

- `claims.csv`: generated claim registry; claim_id, accident_year, line. No final severity field.
- `observed_payments.csv`: payments observable on or before December 31, 2025, in integer USD cents. Grain is claim_id + development_age.
- `evaluation_only/ultimate_truth.csv`: hidden final claim severity, generated solely for evaluating the simulation.
- `evaluation_only/future_payments.csv`: payments after the valuation date, excluded from all forecast fits.
- `generation_metadata.json`: seed, dimensions and explicit simulation assumptions.

No real insurer, employer, policyholder or customer data is used. The generator creates 2014–2025 accident-year cohorts, ten payment-development ages, lognormal severities and Dirichlet payment proportions. The forecasting API has no final-severity input. The runner reads truth only after base forecasts are produced.

The synthetic registry assumes every claim is known at accident year. There is no claim-report delay or unreported-claim arrival model; outstanding payments must not be described as pure IBNR.
