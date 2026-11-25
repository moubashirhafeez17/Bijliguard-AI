import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone
import joblib, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score, confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from src.features.transformer_features import build_transformer_features, FEATURE_COLUMNS
DATA = ROOT / "data/processed/transformer/transformer_clean.csv"
MODEL_DIR = ROOT / "models/transformer_prediction"
REPORT_DIR = ROOT / "reports/transformer_model"
TARGET = "failure_next_7d"

def chronological_split(df):
    dates = np.array(sorted(df.date.unique()))
    if len(dates) < 40: raise ValueError("At least 40 unique dates are required.")
    cut1, cut2 = dates[int(len(dates)*.70)-1], dates[int(len(dates)*.85)-1]
    train = df[df.date <= pd.Timestamp(cut1)-pd.Timedelta(days=7)]
    val = df[(df.date > pd.Timestamp(cut1)) & (df.date <= pd.Timestamp(cut2)-pd.Timedelta(days=7))]
    test = df[df.date > pd.Timestamp(cut2)]
    if min(len(train),len(val),len(test)) == 0: raise ValueError("A chronological split is empty.")
    return train.copy(), val.copy(), test.copy(), {"train_end":str(train.date.max().date()),"validation_start":str(val.date.min().date()),"validation_end":str(val.date.max().date()),"test_start":str(test.date.min().date()),"test_end":str(test.date.max().date()),"purge_days":7}

def evaluate(y, p, threshold):
    pred = p >= threshold
    return {"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0)),"pr_auc_average_precision":float(average_precision_score(y,p)),"roc_auc":float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,"confusion_matrix":confusion_matrix(y,pred,labels=[0,1]).tolist(),"threshold":float(threshold)}

def best_threshold(y,p):
    ts=np.arange(.10,.91,.01)
    return float(max(((f1_score(y,p>=t,zero_division=0),t) for t in ts), key=lambda x:(x[0],x[1]))[1])

def train(data_path=DATA):
    raw=pd.read_csv(data_path)
    needed=["transformer_id","date",TARGET]
    missing=[c for c in needed if c not in raw]
    if missing: raise ValueError(f"Missing columns: {missing}")
    d=build_transformer_features(raw)
    d[TARGET]=pd.to_numeric(d[TARGET],errors="coerce")
    labelled=d[d[TARGET].isin([0,1])].copy(); labelled[TARGET]=labelled[TARGET].astype(int)
    tr,va,te,split=chronological_split(labelled)
    for name,part in [("train",tr),("validation",va),("test",te)]:
        if part[TARGET].nunique()!=2: raise ValueError(f"{name} split does not contain both target classes.")
    models={"RandomForest":Pipeline([("imputer",SimpleImputer(strategy="median")),("classifier",RandomForestClassifier(n_estimators=350,max_depth=12,min_samples_leaf=3,class_weight="balanced_subsample",random_state=42,n_jobs=-1))])}
    try:
        from xgboost import XGBClassifier
        neg=int((tr[TARGET]==0).sum()); pos=int((tr[TARGET]==1).sum())
        models["XGBoost"]=Pipeline([("imputer",SimpleImputer(strategy="median")),("classifier",XGBClassifier(n_estimators=300,max_depth=4,learning_rate=.04,subsample=.85,colsample_bytree=.85,reg_lambda=2,scale_pos_weight=neg/max(pos,1),eval_metric="logloss",random_state=42,n_jobs=4))])
    except ImportError: pass
    fitted={}; comparison={}
    for name,model in models.items():
        model.fit(tr[FEATURE_COLUMNS],tr[TARGET]); pv=model.predict_proba(va[FEATURE_COLUMNS])[:,1]; threshold=best_threshold(va[TARGET].to_numpy(),pv)
        comparison[name]={"validation":evaluate(va[TARGET].to_numpy(),pv,threshold),"threshold":threshold}; fitted[name]=model
    selected=max(comparison,key=lambda n:(comparison[n]["validation"]["pr_auc_average_precision"],comparison[n]["validation"]["f1"]))
    model=fitted[selected]; threshold=comparison[selected]["threshold"]
    pt=model.predict_proba(te[FEATURE_COLUMNS])[:,1]; test_metrics=evaluate(te[TARGET].to_numpy(),pt,threshold)
    MODEL_DIR.mkdir(parents=True,exist_ok=True); REPORT_DIR.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,MODEL_DIR/"transformer_model.joblib")
    clf=model.named_steps["classifier"]
    if hasattr(clf,"feature_importances_"):
        ix=np.argsort(clf.feature_importances_); plt.figure(figsize=(9,5)); plt.barh(np.array(FEATURE_COLUMNS)[ix],np.array(clf.feature_importances_)[ix]); plt.tight_layout(); plt.savefig(REPORT_DIR/"feature_importance.png",dpi=150); plt.close()
    cm=np.array(test_metrics["confusion_matrix"]); plt.figure(figsize=(5,4)); plt.imshow(cm); plt.title("Transformer test confusion matrix"); plt.xlabel("Predicted"); plt.ylabel("Actual"); plt.xticks([0,1],["No failure","Failure"]); plt.yticks([0,1],["No failure","Failure"])
    for (i,j),v in np.ndenumerate(cm): plt.text(j,i,str(v),ha="center",va="center")
    plt.tight_layout(); plt.savefig(REPORT_DIR/"confusion_matrix.png",dpi=150); plt.close()
    metrics={"dataset":str(data_path),"dataset_is_simulated":True,"rows_total":len(raw),"rows_labelled":len(labelled),"rows_unknown_target_excluded":int(d[TARGET].isna().sum()),"positive_count":int((labelled[TARGET]==1).sum()),"negative_count":int((labelled[TARGET]==0).sum()),"target":TARGET,"split":split,"validation_comparison":comparison,"selected_model":selected,"test_metrics":test_metrics}
    (REPORT_DIR/"evaluation_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    metadata={"model_name":selected,"created_at_utc":datetime.now(timezone.utc).isoformat(),"target":TARGET,"feature_columns":FEATURE_COLUMNS,"threshold":threshold,"risk_thresholds":{"medium":.15,"high":.30},"dataset":str(data_path),"dataset_is_simulated":True,"split":split,"test_metrics":test_metrics}
    (MODEL_DIR/"model_metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print("Selected model:",selected); print(json.dumps(test_metrics,indent=2)); print("Saved model:",MODEL_DIR/"transformer_model.joblib")
    return metrics

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--data",type=Path,default=DATA); args=parser.parse_args(); train(args.data)
