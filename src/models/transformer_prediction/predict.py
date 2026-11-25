import json
from pathlib import Path
import joblib, pandas as pd
ROOT=Path(__file__).resolve().parents[3]
MODEL_DIR=ROOT/"models/transformer_prediction"

def _load():
    mp=MODEL_DIR/"transformer_model.joblib"; meta=MODEL_DIR/"model_metadata.json"
    if not mp.exists() or not meta.exists(): raise FileNotFoundError("Trained transformer model missing. Run: python -m src.models.transformer_prediction.train")
    return joblib.load(mp),json.loads(meta.read_text(encoding="utf-8"))

def predict_transformer_batch(df):
    from src.features.transformer_features import build_transformer_features, FEATURE_COLUMNS
    if df.empty: return pd.DataFrame(columns=["transformer_id","date","risk_level","failure_prob_7d","recommendation","source"])
    featured=build_transformer_features(df); model,meta=_load(); cols=meta.get("feature_columns",FEATURE_COLUMNS)
    probs=model.predict_proba(featured[cols])[:,1].clip(0,1)
    high=float(meta.get("risk_thresholds",{}).get("high",.30)); med=float(meta.get("risk_thresholds",{}).get("medium",.15))
    out=featured[["transformer_id","date"]].copy(); out["failure_prob_7d"]=probs
    out["risk_level"]=out.failure_prob_7d.map(lambda p:"High" if p>=high else ("Medium" if p>=med else "Low"))
    out["recommendation"]=out.risk_level.map({"Low":"Continue routine monitoring.","Medium":"Schedule a maintenance inspection and monitor readings.","High":"Prioritize inspection; investigate possible overheating or overload."})
    out["source"]=f"trained model ({meta.get('model_name','unknown')})"
    return out[["transformer_id","date","risk_level","failure_prob_7d","recommendation","source"]]

def predict_single_transformer(df):
    result=predict_transformer_batch(df)
    if result.empty: raise ValueError("At least one transformer reading is required.")
    return result.iloc[-1].to_dict()
