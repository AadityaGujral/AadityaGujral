"""Create and execute the compact analytical notebook from saved evidence outputs."""
from __future__ import annotations
import atexit, base64, contextlib, io, json, os, subprocess, sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parent

def scaffold():
    nb=nbformat.v4.new_notebook();cells=[]
    md=lambda x:cells.append(nbformat.v4.new_markdown_cell(x))
    code=lambda x:cells.append(nbformat.v4.new_code_cell(x))
    md('# Collections Medallion Pipeline\n**PySpark data engineering · synthetic collections operations**\n\n## tl;dr\nThe locally executed Spark pipeline reconciles 300,275 deliveries to 300,000 canonical events, quarantines three invalid rows, and publishes $25.30M in generated payments. All 12 independent reconciliations and eight tests pass. These results demonstrate engineering mechanics, not real portfolio performance.')
    md('## Context & Methods\nThe pipeline uses explicit schemas and Parquet Bronze/Silver/Gold layers. The second Silver version unions the first with the new batch and deduplicates by stable event ID. Saved outputs below come from Spark 4.0.1.\n\n### Key assumptions\nAll data are synthetic. Contact outcomes and payments are independently generated. Channel differences are not causal. [Definitions and architecture](docs/ARCHITECTURE.md).')
    code("from pathlib import Path\nimport json\nimport pandas as pd\nimport matplotlib.pyplot as plt\nroot=Path.cwd()\nsummary=json.loads((root/'outputs/portfolio_summary.json').read_text())\nvalidation=json.loads((root/'outputs/validation.json').read_text())\nprint('Canonical events:',f\"{summary['events']:,}\")\nprint('Payments:',f\"${summary['payments_cents']/100:,.2f}\")\nprint('Independent checks:',validation['passed_checks'])")
    md('## Data\n### Incremental ingestion evidence\nThe second delivery contains redeliveries and three deliberately invalid records. Canonical grain remains one row per event ID.')
    code("batches=pd.read_json(root/'outputs/batch_metrics.json')\ndisplay(batches)")
    md('## Results\n### Monthly generated payments')
    code("monthly=pd.read_csv(root/'outputs/monthly_kpis.csv')\ntrend=monthly.groupby('event_month',as_index=False).payments_cents.sum()\nfig,ax=plt.subplots(figsize=(10,4),layout='constrained')\nax.plot(trend.event_month,trend.payments_cents/1e8,marker='o',color='#285f8f')\nax.set(title='Monthly payments | Synthetic 2025 events',xlabel='Month',ylabel='Payments ($ millions)')\nax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)\ndisplay(fig);plt.close(fig)")
    md('### Channel contact metrics\nPromise-to-pay counts as a right-party contact. Differences reflect random variation around the same generator distribution.')
    code("channel=pd.read_csv(root/'outputs/channel_performance.csv').sort_values('rpc_rate')\ndisplay(channel.round(4))\nfig,ax=plt.subplots(figsize=(8,4),layout='constrained')\nax.barh(channel.channel,channel.rpc_rate*100,color='#b87816')\nax.set(title='Right-party contact rate by channel',xlabel='RPC / attempts (%)',ylabel='Channel');ax.set_xlim(left=0);ax.grid(axis='x',alpha=.2)\ndisplay(fig);plt.close(fig)")
    md('## Takeaways\nThe pipeline proves schema enforcement, quarantine routing, duplicate-safe incremental versioning, partitioned Parquet output, Gold KPI construction, and independent reconciliation. It does not prove outreach effectiveness or production scalability. A production design needs transactional lakehouse storage, orchestration, concurrency controls, governance, monitoring, and late-event rules.\n\n[Full findings](FINDINGS.md) · [Validation](outputs/validation.json)')
    nb.cells=cells;nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
    nbformat.validate(nb);nbformat.write(nb,ROOT/'collections_pipeline_analysis.ipynb')

def fallback():
    nb=nbformat.read(ROOT/'collections_pipeline_analysis.ipynb',as_version=4);os.chdir(ROOT);ns={};count=0
    for cell in nb.cells:
        if cell.cell_type!='code':continue
        count+=1;outs=[]
        def display(x):
            if hasattr(x,'savefig'):
                b=io.BytesIO();x.savefig(b,format='png',dpi=110,bbox_inches='tight');outs.append(nbformat.v4.new_output('display_data',data={'image/png':base64.b64encode(b.getvalue()).decode(),'text/plain':'Matplotlib figure'}))
            elif hasattr(x,'to_html'):outs.append(nbformat.v4.new_output('display_data',data={'text/html':x.to_html(index=False),'text/plain':x.to_string(index=False)}))
            else:outs.append(nbformat.v4.new_output('display_data',data={'text/plain':str(x)}))
        ns['display']=display;b=io.StringIO()
        with contextlib.redirect_stdout(b):exec(compile(cell.source,f'<cell-{count}>','exec'),ns)
        if b.getvalue():outs.insert(0,nbformat.v4.new_output('stream',name='stdout',text=b.getvalue()))
        cell.execution_count=count;cell.outputs=outs
    nbformat.validate(nb);nbformat.write(nb,ROOT/'collections_pipeline_analysis.ipynb')

def main():
    scaffold();route='Jupyter kernel';limitation=None
    try:
        nb=nbformat.read(ROOT/'collections_pipeline_analysis.ipynb',as_version=4)
        client=NotebookClient(nb,timeout=90,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
        try:client.execute()
        finally:atexit.unregister(client._cleanup_kernel)
        nbformat.write(nb,ROOT/'collections_pipeline_analysis.ipynb')
    except Exception as exc:
        route='Fresh Python subprocess; sequential code-cell execution';limitation=f'{type(exc).__name__}: {str(exc)[:200]}'
        subprocess.run([sys.executable,str(Path(__file__).resolve()),'--fallback'],cwd=ROOT,check=True)
    nb=nbformat.read(ROOT/'collections_pipeline_analysis.ipynb',as_version=4);code=[c for c in nb.cells if c.cell_type=='code']
    errors=[o for c in code for o in c.outputs if o.output_type=='error'];assert not errors and all(c.execution_count for c in code)
    result={'format_valid':True,'executed_code_cells':len(code),'errors':0,'execution_route':route,'kernel_limitation':limitation,'visual_inspection':'Static project figures inspected separately'}
    (ROOT/'outputs/notebook_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    if '--fallback' in sys.argv:fallback()
    else:main()
