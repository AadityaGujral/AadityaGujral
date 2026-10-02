import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report

df=pd.read_csv("data/credit_risk_accounts.csv")
features=["days_past_due","contact_attempts","rpc_count","monthly_income","credit_score","original_balance"]
X,y=df[features],df["default_flag"]
X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.25,random_state=42,stratify=y)
scaler=StandardScaler()
X_train_scaled=scaler.fit_transform(X_train)
X_test_scaled=scaler.transform(X_test)
logit=LogisticRegression(max_iter=1000).fit(X_train_scaled,y_train)
rf=RandomForestClassifier(n_estimators=250,max_depth=7,min_samples_leaf=8,random_state=42).fit(X_train,y_train)
for name,model,xt in [("Logistic Regression",logit,X_test_scaled),("Random Forest",rf,X_test)]:
    p=model.predict_proba(xt)[:,1]
    print(name,"ROC-AUC:",round(roc_auc_score(y_test,p),3))
    print(classification_report(y_test,(p>=.5).astype(int)))