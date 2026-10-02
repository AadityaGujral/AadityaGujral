# Collections performance · Power BI

A native Power BI Project with **four authored pages, 37 visuals, five related tables, and 19 DAX measures**. Built from the same synthetic collections snapshot used in the SQL and Excel portfolio projects.

## Open the report

1. Download the repository ZIP and extract it, preserving folders.
2. Open `Collections.pbip` in a current Power BI Desktop version with Power BI Project support enabled.
3. Refresh the model. All five tables contain embedded, compressed synthetic data; no external data connection or absolute path is required.
4. Review each page and confirm the controls below. Save as PBIX from Desktop if needed.

**Validation boundary:** JSON schemas, visual field bindings, relationship integrity, embedded data, page bounds, and SQL reconciliation passed. Power BI Desktop is unavailable in the build environment. The project has not been opened, refreshed, DAX-compiled, or rendered in Desktop. A PBIX and native screenshots are therefore not included.

## Pages

| Page | Contents |
|---|---|
| Executive | Placed, collected, outstanding, recovery; monthly payment trend; portfolio comparison |
| Collectors | Recovery, RPC coverage, dollars per RPC; collector chart and comparison table |
| Risk | 90+ exposure, unpaid accounts, PTP coverage; aging and score-band charts |
| Account detail | Account selector, attributes, payment history, and contact history |

Portfolio, region, and assigned collector dropdowns filter each page. Account detail uses an explicit account selector, rather than relying on drillthrough setup. Select an account to inspect its payment/contact history.

## Model and definitions

`Collectors → Accounts → Payments / Contacts`; `Dates → Payments / Contacts`. All relationships filter in one direction. Collector attribution is the account’s snapshot assignment. Activity dates span January–June 2026. The monthly axis uses a month-number sort column.

- **Recovery rate:** total collected / total placed.
- **RPC coverage:** accounts with at least one RPC or PTP contact / assigned accounts.
- **Dollars per RPC:** collected / count of RPC and PTP contacts.
- **90+ exposure:** outstanding balance where days past due ≥90. The separate 61–90 aging bucket includes day 90; it is not interchangeable with the 90+ calculation.
- **PTP coverage:** accounts with any recorded promise / assigned accounts; it does not measure promise fulfillment.
- Snapshot balances and reach metrics remain fixed to June 30. `Period Collections` and period contact measures respond to activity-date context.
- Score bands describe credit scores. They are not predicted risk scores; the Python modeling dataset is separate. No default or settlement flag exists in this dataset.

### Reconciliation controls

| Metric | Expected |
|---|---:|
| Accounts | 1,500 |
| Placed | $18,510,620.97 |
| Collected | $2,346,315.94 |
| Outstanding | $16,164,305.03 |
| 90+ outstanding | $10,310,701.73 |
| Recovery | 12.6755% |
| RPC coverage | 72.1333% |

## Reproduce and inspect

Run `python build.py` from any directory after rebuilding the sibling SQL project if needed. This recreates model/report definitions and the five readable CSV exports. Install `jsonschema`, then run `python validate.py`; validation retrieves Microsoft schemas over HTTPS. See `validation.json` for results. Monetary data is synthetic and derived from source integer cents; report display uses dollar formatting.

## Sources

- [Microsoft: Power BI Projects overview](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Microsoft: report project structure and PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Microsoft: semantic model project structure](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)
- [Microsoft: Fabric JSON schemas](https://developer.microsoft.com/json-schemas/fabric/)
- [Source SQL project and data dictionary](../sql_collections/)
