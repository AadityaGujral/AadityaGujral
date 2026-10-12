# Synthetic source data

Run `python -m src.generate_data` to recreate the inputs with seed `20261012`.

- `raw/accounts.csv`: 50,000 fictional account master records.
- `raw/batch_01/events.jsonl`: first delivery batch.
- `raw/batch_02/events.jsonl`: second delivery batch, including 272 repeated event deliveries and three invalid records.
- `generation_metadata.json`: counts, period, seed, and disclosure.

Raw files are excluded from Git because they are about 60 MB and fully reproducible. There are no names, addresses, contact details, SSNs, or real financial records.

Payment and contact events are independently generated. A promise-to-pay is counted as a right-party contact for KPI purposes, but contact outcomes do not cause payments in the simulation. Do not interpret channel comparisons as campaign effectiveness.
