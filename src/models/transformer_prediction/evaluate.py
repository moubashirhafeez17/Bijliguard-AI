import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REPORT=ROOT/"reports/transformer_model/evaluation_metrics.json"
if __name__=="__main__":
    if not REPORT.exists(): raise FileNotFoundError("Train the model first.")
    print(json.dumps(json.loads(REPORT.read_text(encoding="utf-8")),indent=2))
