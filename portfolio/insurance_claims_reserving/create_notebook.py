"""Create and execute a readable notebook; disclose any kernel restrictions.

The fresh-process fallback executes every code cell top-to-bottom, with captured
tables and figure outputs. It is not represented as Jupyter-kernel execution.
"""
import base64
import atexit
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parent

def make_notebook():
    nb=nbformat.v4.new_notebook()
    cells=[]
    def md(text):cells.append(nbformat.v4.new_markdown_cell(text))
    def code(text):cells.append(nbformat.v4.new_code_cell(text))
    md('# Insurance Claims Reserving & Runoff Analytics\n**Aditya Gujral · Synthetic insurance / Python**\n\n## Summary\nAt December 31, 2025, the simulation estimates **$138.95 million** outstanding and **$43.12 million** in 2026 existing-claim payments. Calendar-holdout WAPE is **1.88%**. These values reflect a deliberately stable synthetic payment process, not insurer performance.\n\nThis notebook is the executed companion to the reusable implementation and exact CSV outputs.')
    md('## Context & Methods\nBuild cumulative paid triangles and fit volume-weighted factors separately for Auto and Liability. Use historical cutoffs to evaluate next-year payment forecasts.\n\n### Key assumptions\nAll data are generated; all claims finish by development age nine; no reporting delay, case reserves or expenses exist. Outstanding is ultimate minus paid, not pure IBNR. Scenarios are deterministic and do not quantify uncertainty.\n\n[Methodological contract](docs/METHODOLOGY.md) · [CAS chain-ladder tutorial](https://opensourcesoftware.casact.org/chain-ladder) · [CAS tail-factor report](https://www.casact.org/sites/default/files/database/forum_13fforum_02-tail-factors-working-party.pdf)')
    md('### 1. Rebuild all inputs and computations\nRun from the project directory. The pipeline includes eight unit tests and twelve reconciliation checks. This cell intentionally regenerates project outputs.')
    code("from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom run_project import run\nroot = Path.cwd()\nassert (root / 'run_project.py').exists(), 'Open the notebook in the project directory'\nvalidation = run(root)\nprint('Validation status:', validation['status'])")
    md('## Data\nThe input CSV grain is claim_id + development_age. Unknown future cells remain missing. Hidden simulated severities and future payments are segregated for evaluation.')
    code("metadata = json.loads((root / 'data/generation_metadata.json').read_text())\nprint('Claims:', metadata['claims'])\nprint('Observed payment rows:', metadata['observed_payment_rows'])\nprint('Cutoff:', metadata['valuation_year'])\nobserved = pd.read_csv(root / 'data/observed_payments.csv')\ndisplay(observed.head(6))")
    md('## Results\n### 2. Outstanding estimate by line\nAmounts are undiscounted USD. Liability dominates outstanding because the generator explicitly assigns it larger severity and slower payment timing.')
    code("summary = pd.read_csv(root / 'outputs/reserve_summary.csv')\ndisplay(summary.round(2))\ncohorts = pd.read_csv(root / 'outputs/cohort_estimates.csv')\npivot = cohorts.pivot(index='accident_year', columns='line', values='outstanding_estimate_cents') / 1e8\nfig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')\npivot.plot.bar(stacked=True, ax=ax, color=['#275E8E', '#B57918'], rot=0)\nax.set(title='Estimated outstanding by accident year | Synthetic data', xlabel='Accident year', ylabel='Estimated outstanding ($ millions)')\nax.set_ylim(bottom=0)\nax.grid(axis='y', alpha=.2)\ndisplay(fig)\nplt.close(fig)")
    md('### 3. Existing-claim runoff\nThe base forecast excludes new accident years after 2025 and sums to the outstanding estimate. It has no extra-tail cashflow timing.')
    code("cashflow = pd.read_csv(root / 'outputs/cashflow_summary.csv')\npivot = cashflow.pivot(index='payment_year', columns='line', values='predicted_payment_cents') / 1e8\nfig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')\npivot.plot.bar(stacked=True, ax=ax, color=['#275E8E', '#B57918'], rot=0)\nax.set(title='Expected existing-claim runoff | Base model', xlabel='Payment year', ylabel='Predicted payments ($ millions)')\nax.set_ylim(bottom=0)\nax.grid(axis='y', alpha=.2)\ndisplay(fig)\nplt.close(fig)")
    md('### 4. Historical calendar holdouts\nFit only payments available at each cutoff. Compare forecast and actual next-year payments for existing accident years. WAPE combines absolute origin-level errors; later observed diagonals are not used during each fit.')
    code("backtests = pd.read_csv(root / 'outputs/backtest_summary.csv')\ndisplay(backtests.round(3))\ndetail = pd.read_csv(root / 'outputs/backtest_detail.csv')\nwape = 100 * detail.error_cents.abs().sum() / detail.actual_payment_cents.sum()\nprint(f'Pooled cohort WAPE: {wape:.2f}%')\nprint('Zero-payment baseline WAPE: 100%')")
    md('### 5. Sensitivity and evidence\nThe ±5% cases change each development factor\'s excess above one. The tail case multiplies ultimate by 1.02. These are not confidence intervals.')
    code("scenarios = pd.read_csv(root / 'outputs/sensitivity_scenarios.csv')\ndisplay(scenarios.pivot(index='scenario', columns='line', values='outstanding_estimate_usd').round(2))\nprint(json.dumps(validation['data_checks'], indent=2))\nprint('Unit tests:', validation['unit_tests'])")
    md('## Takeaways\nUse separate line-specific patterns, inspect recent Liability accident years, and review the cashflow schedule alongside sensitivity scenarios. The favorable errors are measured only in this simulation.\n\nReal implementation requires reporting and case-reserve data, changing settlement/inflation analysis, empirical tail selection, expense/recovery treatment and actuarial review. The base tail is 1.00 by construction; no probabilistic reserve interval, production adequacy or savings claim is made.\n\n[Exact findings](FINDINGS.md) · [Validation](outputs/validation.json) · [Source generator](src/generate_data.py)')
    nb.cells=cells
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
    nbformat.validate(nb)
    nbformat.write(nb,ROOT/'claims_reserving.ipynb')

def fallback_execute():
    nb=nbformat.read(ROOT/'claims_reserving.ipynb',as_version=4)
    namespace={'__name__':'__notebook__'}
    os.chdir(ROOT)
    count=0
    for cell in nb.cells:
        if cell.cell_type!='code':continue
        count+=1; outputs=[]
        def display(value):
            if hasattr(value,'savefig'):
                buf=io.BytesIO();value.savefig(buf,format='png',dpi=110,bbox_inches='tight')
                outputs.append(nbformat.v4.new_output('display_data',data={'image/png':base64.b64encode(buf.getvalue()).decode(),'text/plain':'Matplotlib figure'}))
            elif hasattr(value,'to_html'):
                outputs.append(nbformat.v4.new_output('display_data',data={'text/html':value.to_html(index=False),'text/plain':value.to_string(index=False)}))
            else:
                outputs.append(nbformat.v4.new_output('display_data',data={'text/plain':str(value)}))
        namespace['display']=display
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(compile(cell.source,f'<notebook-cell-{count}>','exec'),namespace)
        if buf.getvalue():outputs.insert(0,nbformat.v4.new_output('stream',name='stdout',text=buf.getvalue()))
        cell.execution_count=count;cell.outputs=outputs
    nbformat.validate(nb);nbformat.write(nb,ROOT/'claims_reserving.ipynb')
    return count

def main():
    make_notebook()
    route='Jupyter kernel via nbclient';reason=None
    try:
        nb=nbformat.read(ROOT/'claims_reserving.ipynb',as_version=4)
        client=NotebookClient(nb,timeout=120,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
        try:
            client.execute()
        finally:
            atexit.unregister(client._cleanup_kernel)
        nbformat.validate(nb);nbformat.write(nb,ROOT/'claims_reserving.ipynb')
    except (OSError,RuntimeError) as exc:
        route='Fresh Python subprocess; sequential code-cell execution'
        reason=f'{type(exc).__name__}: {str(exc)[:240]}'
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--fallback'],check=True,cwd=ROOT)
    nb=nbformat.read(ROOT/'claims_reserving.ipynb',as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    errors=[o for c in code for o in c.outputs if o.output_type=='error']
    assert not errors and all(c.execution_count for c in code)
    report={'format_valid':True,'executed_code_cells':len(code),'errors':len(errors),'execution_route':route,
            'kernel_limitation':reason,'visual_inspection':'Figure PNGs inspected separately; complete notebook viewer not available'}
    (ROOT/'outputs/notebook_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    if '--fallback' in sys.argv: fallback_execute()
    else:main()
