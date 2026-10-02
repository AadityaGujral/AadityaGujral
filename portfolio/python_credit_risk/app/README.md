# Credit Risk Lab · Aditya Gujral

An interactive browser application built around the existing Python credit-risk experiment. It runs exported logistic regression and random forest models locally in the browser; it does not substitute a heuristic for the trained pipelines.

## Features

- Account studio with seven inputs, missing-income imputation, validation and range context.
- Model comparison with test ROC curves, ROC-AUC, average precision, Brier score and validation ROC-AUC.
- Threshold explorer with recomputed precision, recall, flagged counts and confusion matrix.
- Logistic feature contributions in signed log-odds, including the intercept explanation.
- A sorted queue of 500 unlabeled synthetic accounts, filtering, pagination, account inspection and CSV download.
- Methodology and links to official scikit-learn documentation.

The default 26% threshold is the original validation-selected logistic operating point. Moving the slider is scenario exploration on the test set, not a new optimization. The forest shares the slider but has no separately selected threshold. Random forest view shows **global importance from the selected logistic model**, explicitly labeled; no forest-local explanation is claimed.

All data is synthetic. The target is simulated transition to 90+ days past due within 90 days, not legal default. The experiment is independent of the SQL/Excel/Power BI collections dataset. These probabilities are not calibrated to real borrowers or suitable for lending decisions.

## Run locally

Serve `dist/` using a static HTTP server, for example:

```sh
python -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. Serving over HTTP is required for loading `data.json`; double-clicking HTML via a file URL is insufficient. No backend, API key or external data service is needed. Google Fonts is optional; system-font fallbacks are provided.

## Rebuild and verify

Install the exact dependencies in the parent Python project's `requirements.txt`, then run:

```sh
python export_model.py --source ..
node test.mjs
```

`--source` must point to the original Python project with its generated data and outputs. The exporter refits only the original January–March 2025 training split, asserts reproduction of saved test probabilities, and exports imputer/scaler parameters, categories, coefficients and 250 forest trees. It never refits on validation or test data.

Browser tree traversal uses float32 feature values to match scikit-learn's tree prediction behavior. `parity-fixtures.json` contains 995 test and 500 unlabeled scoring records and both Python probabilities. `validation.json` records the independent JavaScript comparison and edge-case checks.

The static site is responsive and uses native accessible form controls. Native browser rendering and WebMCP registration were not tested in this environment. A feature-detected WebMCP tool uses the same account validation, scoring and visible studio state when supported.

## References

- [Original experiment](../README.md)
- [scikit-learn: decision threshold tuning](https://scikit-learn.org/stable/modules/classification_threshold.html)
- [scikit-learn: classification metrics](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [scikit-learn: permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html)
