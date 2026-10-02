export function validateAccount(a){
 const limits={days_past_due:[0,89,true],credit_score:[420,820,true],monthly_income:[1,1000000,false],balance:[0,1000000,false],utilization:[0,1,false],missed_payments_6m:[0,50,true]};
 for(const [k,[lo,hi,int]] of Object.entries(limits)){if(k==='monthly_income'&&a[k]===null)continue;if(typeof a[k]!=='number'||!Number.isFinite(a[k])||a[k]<lo||a[k]>hi||(int&&!Number.isInteger(a[k])))throw new Error(`Check ${k.replaceAll('_',' ')}: expected ${int?'a whole number':'a number'} from ${lo} to ${hi}.`);}
 if(!['Auto','Credit Card','Medical','Personal Loan'].includes(a.portfolio))throw new Error('Choose a supported portfolio.');return a;
}
export function transform(model,a){return [...model.features.slice(0,6).map((k,i)=>((a[k]??model.medians[i])-model.means[i])/model.scales[i]),...model.categories.map(c=>a.portfolio===c?1:0)];}
export function score(model,a){const x=transform(model,a);if(model.coefficients){let z=model.intercept+x.reduce((s,v,i)=>s+v*model.coefficients[i],0);return z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));}
 const tx=x.map(Math.fround);let sum=0;for(const t of model.trees){let n=0;while(t.left[n]!==-1)n=tx[t.feature[n]]<=t.threshold[n]?t.left[n]:t.right[n];sum+=t.probability[n];}return sum/model.trees.length;
}
export function contributions(model,a){const x=transform(model,a);const rows=model.features.slice(0,6).map((k,i)=>({feature:k,value:x[i]*model.coefficients[i]}));rows.push({feature:'portfolio',value:model.categories.reduce((s,c,i)=>s+x[i+6]*model.coefficients[i+6],0)});return rows.sort((a,b)=>Math.abs(b.value)-Math.abs(a.value));}
export function evaluate(rows,key,t){let tp=0,tn=0,fp=0,fn=0;for(const r of rows){const p=r[key]>=t;if(p&&r.y)tp++;else if(p)fp++;else if(r.y)fn++;else tn++;}return{tp,tn,fp,fn,precision:tp+fp?tp/(tp+fp):0,recall:tp+fn?tp/(tp+fn):0,flagged:tp+fp,n:rows.length};}
export function queue(accounts,models,key,threshold,filter='all'){return accounts.map(a=>({...a,probability:score(models[key],a)})).filter(a=>filter==='all'||(filter==='flagged'?a.probability>=threshold:a.probability<threshold)).sort((a,b)=>b.probability-a.probability||a.account_id-b.account_id);}
export function csv(rows,threshold,key){const head=['account_id','snapshot_date','portfolio','balance','risk_probability','review_flag','model','threshold'];return [head.join(','),...rows.map(r=>[r.account_id,r.snapshot_date,r.portfolio,r.balance,r.probability.toFixed(8),r.probability>=threshold,key,threshold].join(','))].join('\n');}
