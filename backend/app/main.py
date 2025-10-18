from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os, pandas as pd

CSV_PATH = os.getenv("DATA_CSV", os.path.join(os.path.dirname(__file__), "../../data/products.csv"))

app = FastAPI(title="AI Recs MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# lazy load dataset once
_df = pd.read_csv(CSV_PATH).fillna("")

@app.get("/")
def health():
    return {"ok": True, "rows": len(_df)}

@app.get("/analytics/summary")
def analytics():
    # super basic summary for frontend
    cat_counts = _df["categories"].astype(str).str.split(",", expand=True)[0].value_counts().to_dict()
    return {"category_counts": cat_counts}
