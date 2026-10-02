"""Leakage-controlled temporal validation and genuinely unlabeled scoring."""
import json, platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import roc_auc_score,average_precision_score,precision_score,recall_score,f1_score,brier_score_loss,confusion_matrix,roc_curve
from sklearn.inspection import permutation_importance
from generate_data import ROOT,FEATURES,generate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TARGET='future_90dpd'
COLORS={'Logistic Regression':'#235789','Random Forest':'#b87521','Baseline':'#666666'}
def make_pipeline(model):
    num=Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())])
    prep=ColumnTransformer([('numeric',num,FEATURES[:-1]),('category',OneHotEncoder(handle_unknown='ignore'),['portfolio'])])
    return Pipeline([('prepare',prep),('model',model)])
def metrics(y,p,threshold=.5):
    pred=p>=threshold
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'roc_auc':roc_auc_score(y,p),'average_precision':average_precision_score(y,p),'precision':precision_score(y,pred,zero_division=0),'recall':recall_score(y,pred,zero_division=0),'f1':f1_score(y,pred,zero_division=0),'brier':brier_score_loss(y,p),'threshold':threshold,'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}
def run():
    data=ROOT/'data';out=ROOT/'outputs';fig=ROOT/'figures'
    for d in [data,out,fig]:d.mkdir(exist_ok=True)
    generate().to_csv(data/'historical_snapshots.csv',index=False)
    generate(500,84,True).to_csv(data/'scoring_accounts.csv',index=False)
    df=pd.read_csv(data/'historical_snapshots.csv',parse_dates=['snapshot_date','outcome_end_date'])
    # Embargo ensures all training outcomes mature before validation, and validation before test.
    train=df[df.snapshot_date<'2025-04-01'].copy()
    val=df[(df.snapshot_date>='2025-07-01')&(df.snapshot_date<'2025-08-01')].copy()
    test=df[df.snapshot_date>='2025-11-01'].copy()
    assert train.outcome_end_date.max()<val.snapshot_date.min()
    assert val.outcome_end_date.max()<test.snapshot_date.min()
    assert not set(train.customer_id)&set(val.customer_id)
    assert not set(train.customer_id)&set(test.customer_id)
    assert not set(val.customer_id)&set(test.customer_id)
    assert df.account_id.is_unique and df.customer_id.is_unique
    assert df.days_past_due.between(0,89).all() and df[TARGET].isin([0,1]).all()
    assert all(d[TARGET].nunique()==2 for d in [train,val,test])
    candidates={'Baseline':DummyClassifier(strategy='prior'),'Logistic Regression':LogisticRegression(max_iter=1000,random_state=42),'Random Forest':RandomForestClassifier(n_estimators=250,max_depth=6,min_samples_leaf=20,random_state=42,n_jobs=1)}
    fitted={};val_rows=[];test_rows=[];probs={}
    for name,estimator in candidates.items():
        pipe=make_pipeline(estimator).fit(train[FEATURES],train[TARGET]);fitted[name]=pipe
        vp=pipe.predict_proba(val[FEATURES])[:,1]
        val_rows.append({'model':name,**metrics(val[TARGET],vp)})
    validation=pd.DataFrame(val_rows)
    winner=validation[validation.model!='Baseline'].sort_values('roc_auc',ascending=False).iloc[0]['model']
    # Threshold chosen only from validation: F2 prioritizes recall, illustrative objective.
    from sklearn.metrics import fbeta_score
    vprob=fitted[winner].predict_proba(val[FEATURES])[:,1]
    grid=np.arange(.1,.81,.02)
    threshold=float(max(grid,key=lambda t:fbeta_score(val[TARGET],vprob>=t,beta=2,zero_division=0)))
    pd.DataFrame({'threshold':grid,'validation_f2':[fbeta_score(val[TARGET],vprob>=t,beta=2,zero_division=0) for t in grid]}).to_csv(out/'threshold_selection.csv',index=False)
    for name,pipe in fitted.items():
        p=pipe.predict_proba(test[FEATURES])[:,1];probs[name]=p
        test_rows.append({'model':name,**metrics(test[TARGET],p,.5)})
    pd.DataFrame([{'model':winner,**metrics(test[TARGET],probs[winner],threshold)}]).to_csv(out/'operating_point_metrics.csv',index=False)
    report=pd.DataFrame(test_rows);report.to_csv(out/'test_metrics.csv',index=False);validation.to_csv(out/'validation_metrics.csv',index=False)
    held=test[['account_id','customer_id','snapshot_date',TARGET]].copy()
    for name,p in probs.items():held[name.lower().replace(' ','_')+'_probability']=p
    held.to_csv(out/'holdout_predictions.csv',index=False)
    live=pd.read_csv(data/'scoring_accounts.csv')
    assert TARGET not in live and not set(live.customer_id)&set(df.customer_id)
    # Preserve evaluated fitted model for scoring; no unreported refit.
    scores=live[['account_id','snapshot_date','balance']].copy();scores['risk_probability']=fitted[winner].predict_proba(live[FEATURES])[:,1]
    scores['review_flag']=scores.risk_probability>=threshold
    scores.sort_values('risk_probability',ascending=False).to_csv(out/'risk_scores.csv',index=False)
    imp=permutation_importance(fitted[winner],test[FEATURES],test[TARGET],scoring='roc_auc',n_repeats=8,random_state=42)
    importance=pd.DataFrame({'feature':FEATURES,'mean_auc_drop':imp.importances_mean,'std_auc_drop':imp.importances_std}).sort_values('mean_auc_drop')
    importance.to_csv(out/'permutation_importance.csv',index=False)
    split={'train':train,'validation':val,'test':test}
    info={'dataset':'100% synthetic; independent from SQL dataset','target':'Simulated transition to 90+ DPD within 90 days; not legal default','selection_metric':'validation ROC-AUC','selected_model':winner,'threshold':threshold,'threshold_objective':'validation F2 on fixed 0.10-0.80 grid','splits':{k:{'rows':len(d),'start':str(d.snapshot_date.min().date()),'end':str(d.snapshot_date.max().date()),'outcome_end':str(d.outcome_end_date.max().date()),'prevalence':float(d[TARGET].mean())} for k,d in split.items()},'excluded_embargo_rows':len(df)-sum(len(d) for d in split.values()),'scored_unlabeled_accounts':len(live),'checks':['unique account/customer grain','mature outcomes before next split','no customer overlap','target excluded from features','both classes in each split','live set unlabeled and disjoint'],'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__}}
    (out/'run_summary.json').write_text(json.dumps(info,indent=2)+'\n')
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    f,ax=plt.subplots(figsize=(8,5))
    for name,p in probs.items():
        x,y,_=roc_curve(test[TARGET],p);auc=roc_auc_score(test[TARGET],p)
        ax.plot(x,y,label=f'{name} (AUC {auc:.3f})',color=COLORS[name],linestyle='--' if name=='Baseline' else '-')
    ax.set(xlabel='False positive rate',ylabel='True positive rate',title=f'ROC comparison | untouched test accounts (n={len(test)})',xlim=(0,1),ylim=(0,1));ax.legend(loc='lower right');f.tight_layout();f.savefig(fig/'roc_comparison.png',dpi=130);plt.close(f)
    f,ax=plt.subplots(figsize=(8,4.5));ax.barh(importance.feature,importance.mean_auc_drop,xerr=importance.std_auc_drop,color='#235789');ax.axvline(0,color='#333333',linewidth=.8);ax.set(xlabel='Mean test ROC-AUC decrease (8 permutations; error bars = SD)',title=f'Permutation importance | {winner}');f.tight_layout();f.savefig(fig/'feature_importance.png',dpi=130);plt.close(f)
    f,axes=plt.subplots(1,2,figsize=(9,4));axes[0].hist(df.credit_score,bins=20,color='#235789');axes[0].set(title='Synthetic credit score distribution',xlabel='Credit score',ylabel='Accounts')
    rates=df.assign(band=pd.cut(df.days_past_due,[-1,29,59,89],labels=['0–29','30–59','60–89'])).groupby('band',observed=True)[TARGET].agg(['mean','count'])
    axes[1].bar(rates.index.astype(str),rates['mean']*100,color='#b87521');axes[1].set(title='Simulated 90-day outcome by starting DPD',xlabel='Days past due at snapshot',ylabel='90+ DPD outcome (%)',ylim=(0,100));f.tight_layout();f.savefig(fig/'data_exploration.png',dpi=130);plt.close(f)
    f,ax=plt.subplots(figsize=(6,4.5));cm=confusion_matrix(test[TARGET],probs[winner]>=threshold);ax.imshow(cm,cmap='Blues')
    for (i,j),v in np.ndenumerate(cm):ax.text(j,i,str(v),ha='center',va='center',color='white' if v>cm.max()/2 else '#222222',fontsize=17)
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['No event','90+ DPD'],yticklabels=['No event','90+ DPD'],xlabel='Predicted outcome',ylabel='Observed synthetic outcome',title=f'{winner} | test confusion matrix\nValidation-selected threshold {threshold:.2f}');f.tight_layout();f.savefig(fig/'confusion_matrix.png',dpi=130);plt.close(f)
    print(report[['model','roc_auc','average_precision','precision','recall','threshold']].to_string(index=False))
    return df,report,info
if __name__=='__main__':run()
