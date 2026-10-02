"""Build and execute the portfolio notebook from a clean kernel."""
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from generate_data import ROOT
md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
nb=nbformat.v4.new_notebook()
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
nb.cells=[
md('# Credit Risk: Predicting 90-Day Delinquency\nAditya Gujral · Python analytics portfolio · 100% synthetic data\n\n## tl;dr\nLogistic Regression was selected using validation ROC-AUC. On the untouched test cohort its ROC-AUC is **0.721**, versus **0.712** for Random Forest. The figures below show discrimination and the review-threshold tradeoff. No real-world predictive performance is claimed.'),
md('## Context & Methods\nPredict whether a fictional account with starting DPD below 90 transitions to 90+ DPD within 90 days. This is a delinquency proxy, not legal default.\n\n### Key Assumptions\nOne snapshot per customer. Features are generated as snapshot attributes; the future outcome is a stochastic simulation using those attributes plus unobserved noise. Training outcomes must mature before validation begins, and validation outcomes before test begins. The intervening embargo rows are intentionally excluded. Training-only imputation/scaling prevents preprocessing leakage. Select the model and threshold on validation only. No parameters are tuned to test results.\n\nSources: [data generator](generate_data.py), [pipeline](model.py), [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage).'),
code('from pathlib import Path\nimport pandas as pd\nfrom IPython.display import display, Image\nfrom model import run, ROOT\ndf, comparison, summary = run()'),
md('## Data\n6,000 historical account snapshots in 2025; 500 separate unlabeled scoring accounts dated June 30, 2026. This dataset is independent of the SQL example; it supplies the dated outcomes required for prediction.'),
code("display(df.head(5))\ndisplay(pd.DataFrame(summary['splits']).T)\nprint('Embargo rows excluded:', summary['excluded_embargo_rows'])\nprint('Missing income values:', df.monthly_income.isna().sum())"),
code("display(Image(filename=str(ROOT/'figures/data_exploration.png')))"),
md('Higher starting delinquency is associated with more simulated 90+ DPD events. This relationship partly reflects the generator design, not a discovery about actual customers.'),
md('## Results\n### Model comparison\nBoth models use the same fixed 0.50 threshold below. ROC-AUC and average precision assess ranking without selecting a threshold. The prior-only baseline predicts the training event rate.'),
code("display(comparison[['model','roc_auc','average_precision','precision','recall','f1','brier','threshold']].round(3))\ndisplay(Image(filename=str(ROOT/'figures/roc_comparison.png')))"),
md('Logistic Regression ranks the synthetic test outcomes better than the prior-only baseline. The small difference versus Random Forest is descriptive; no significance claim is made.'),
md('### Operational threshold\nThe selected threshold maximizes validation F2 on a fixed grid, emphasizing recall. F2 is a demonstration objective; actual review capacity and costs would determine a production threshold.'),
code("display(pd.read_csv(ROOT/'outputs/operating_point_metrics.csv').round(3))\ndisplay(Image(filename=str(ROOT/'figures/confusion_matrix.png')))"),
md('### What the model uses\nPermutation importance measures test AUC reduction when a feature is shuffled. Error bars show variability across eight repeats, not confidence intervals. This diagnostic is not used for model selection and is not causal.'),
code("display(Image(filename=str(ROOT/'figures/feature_importance.png')))"),
md('### Separate scoring accounts\nScores are produced by the evaluated fitted model, with no hidden refit. These unlabeled scores are not included in test metrics.'),
code("scores = pd.read_csv(ROOT/'outputs/risk_scores.csv')\ndisplay(scores.head(10).round(3))\nprint('Unlabeled accounts scored:', len(scores))"),
md('## Takeaways\nThe workflow demonstrates temporal separation, mature outcomes, leakage-safe preprocessing, model selection, threshold selection and account scoring. Use it to explain ranking versus decision thresholds in an interview.\n\nSynthetic results do not establish production fitness. Real use needs observed delinquency histories, customer-group handling for repeated accounts, calibration, temporal robustness, fairness review and operational cost validation. Predicted scores here are illustrative and not calibrated financial probabilities.\n\nReproduce: `python model.py`; execute notebook: `python create_notebook.py`. Outputs are overwritten only in this project folder.')]
nbformat.validate(nb)
# This environment blocks kernel sockets. Execute the same cells sequentially
# in one fresh process and capture rich display outputs without a socket kernel.
import base64, contextlib, io
import IPython.display as ipd
namespace={'__name__':'__main__'}
outputs=[]
def capture(value):
    if isinstance(value,ipd.Image):
        raw=value.data if value.data is not None else Path(value.filename).read_bytes()
        outputs.append(nbformat.v4.new_output('display_data',data={'image/png':base64.b64encode(raw).decode(),'text/plain':'<PNG figure>'},metadata={}))
    elif hasattr(value,'_repr_html_'):
        outputs.append(nbformat.v4.new_output('display_data',data={'text/html':value._repr_html_(),'text/plain':str(value)},metadata={}))
    else:
        outputs.append(nbformat.v4.new_output('display_data',data={'text/plain':str(value)},metadata={}))
ipd.display=capture
count=0
for cell in nb.cells:
    if cell.cell_type!='code': continue
    count+=1;outputs=[]
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream): exec(compile(cell.source,'<notebook-cell>','exec'),namespace)
    if stream.getvalue():outputs.insert(0,nbformat.v4.new_output('stream',name='stdout',text=stream.getvalue()))
    cell.execution_count=count;cell.outputs=outputs
nb.metadata['execution_method']='Sequential fresh-process Python execution; rich displays captured; socket kernel unavailable in authoring environment'
nbformat.validate(nb)
nbformat.write(nb,ROOT/'credit_risk_analysis.ipynb')
assert not any(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.outputs)
print('Notebook executed and validated:',ROOT/'credit_risk_analysis.ipynb')
