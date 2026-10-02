"""Export the original training-only pipelines to portable browser inference data."""
import sys,json,pathlib,argparse
import pandas as pd,numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_curve
ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);args=ap.parse_args()
source=pathlib.Path(args.source).resolve();sys.path.insert(0,str(source))
from model import make_pipeline,TARGET
from generate_data import FEATURES
root=pathlib.Path(__file__).resolve().parent;dest=root/'dist';dest.mkdir(exist_ok=True)
df=pd.read_csv(source/'data/historical_snapshots.csv');train=df[df.snapshot_date<'2025-04-01'];test=df[df.snapshot_date>='2025-11-01'];live=pd.read_csv(source/'data/scoring_accounts.csv')
models={};expected={};roc={}
for key,est in [('logistic',LogisticRegression(max_iter=1000,random_state=42)),('forest',RandomForestClassifier(n_estimators=250,max_depth=6,min_samples_leaf=20,random_state=42,n_jobs=1))]:
 pipe=make_pipeline(est).fit(train[FEATURES],train[TARGET]);prep=pipe['prepare'];num=prep.named_transformers_['numeric'];model=pipe['model']
 m={'features':FEATURES,'medians':num['impute'].statistics_.tolist(),'means':num['scale'].mean_.tolist(),'scales':num['scale'].scale_.tolist(),'categories':prep.named_transformers_['category'].categories_[0].tolist()}
 if key=='logistic':m.update({'intercept':float(model.intercept_[0]),'coefficients':model.coef_[0].tolist()})
 else:
  m['trees']=[]
  for tree in model.estimators_:
   t=tree.tree_;m['trees'].append({'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'probability':(t.value[:,0,1]/t.value[:,0,:].sum(axis=1)).tolist()})
 models[key]=m
 allrows=pd.concat([test,live],ignore_index=True);expected[key]=pipe.predict_proba(allrows[FEATURES])[:,1].tolist();p=expected[key][:len(test)]
 fpr,tpr,_=roc_curve(test[TARGET],p);roc[key]=list(zip(fpr.tolist(),tpr.tolist()))
 existing=pd.read_csv(source/'outputs/holdout_predictions.csv');col='logistic_regression_probability' if key=='logistic' else 'random_forest_probability'
 assert np.max(np.abs(np.array(p)-existing[col].values))<1e-12
# Individual test and live records support independent JS inference parity tests.
def records(d):return json.loads(d.to_json(orient='records'))
summary=json.loads((source/'outputs/run_summary.json').read_text())
bundle={'trainingRanges':{k:[float(train[k].min()),float(train[k].max())] for k in FEATURES[:-1]},'models':models,'summary':summary,'testMetrics':records(pd.read_csv(source/'outputs/test_metrics.csv')),'validationMetrics':records(pd.read_csv(source/'outputs/validation_metrics.csv')),'importance':records(pd.read_csv(source/'outputs/permutation_importance.csv')),'roc':roc,'holdout':[{'y':int(y),'logistic':l,'forest':f} for y,l,f in zip(test[TARGET],expected['logistic'][:len(test)],expected['forest'][:len(test)])],'accounts':records(live),'baseline':float(train[TARGET].mean())}
(dest/'data.json').write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False))
(root/'parity-fixtures.json').write_text(json.dumps({'rows':records(allrows[FEATURES]),'expected':expected},allow_nan=False))
print(f'Exported {len(train)} training rows; {len(test)} test and {len(live)} unlabeled scoring rows. Original predictions reproduced.')
