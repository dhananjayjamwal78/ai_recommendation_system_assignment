import os
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .models_runtime import Runtime
from .vector_store import load_or_build_faiss

# ---------- Config ----------
# Default CSV at repo_root/data/products.csv (relative to this file)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "products.csv")
CSV_PATH = os.getenv("DATA_CSV", DEFAULT_CSV)

app = FastAPI(title="AI Recs MVP", version="1.0")

# CORS (dev-friendly; restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Startup ----------
runtime = Runtime(CSV_PATH)
store = load_or_build_faiss(runtime)
_df = runtime.df  # convenience alias

# ---------- Routes ----------
@app.get("/")
def health():
    return {"ok": True, "rows": int(len(_df)), "csv": os.path.relpath(CSV_PATH, REPO_ROOT)}

# Analytics summary for frontend charts
@app.get("/analytics/summary")
def analytics():
    cat_counts = (
        _df["category_main"]
        .astype(str)
        .value_counts()
        .to_dict()
    )
    # price stats (coerce to numeric safely)
    price = pd.to_numeric(_df.get("price", ""), errors="coerce")
    price_stats = price.dropna().describe().to_dict()
    return {"category_counts": cat_counts, "price_stats": price_stats}

# NLP: semantic search by prompt
@app.get("/search")
def search(q: str = Query(..., min_length=2), k: int = 6):
    res = store.similarity_search(q, k=k)
    return {
        "results": [
            {
                "uniq_id": r.metadata.get("uniq_id"),
                "title": r.metadata.get("title"),
                "brand": r.metadata.get("brand"),
                "price": r.metadata.get("price"),
                "categories": r.metadata.get("categories"),
                "images": r.metadata.get("images"),
            }
            for r in res
        ]
    }

# ML Recs: similar items for a chosen product (by uniq_id)
@app.get("/recommend/{uniq_id}")
def recommend(uniq_id: str, k: int = 5):
    rows = _df[_df["uniq_id"] == uniq_id]
    if rows.empty:
        return {"recommended": []}
    qdoc = rows.iloc[0]["doc"]
    res = store.similarity_search(qdoc, k=k + 1)  # +1 to skip itself
    out = []
    for r in res:
        md = r.metadata
        if md.get("uniq_id") == uniq_id:
            continue
        out.append(
            {
                "uniq_id": md.get("uniq_id"),
                "title": md.get("title"),
                "brand": md.get("brand"),
                "price": md.get("price"),
                "categories": md.get("categories"),
                "images": md.get("images"),
            }
        )
        if len(out) == k:
            break
    return {"recommended": out}

# GenAI: creative description for a product
@app.get("/generate/{uniq_id}")
def generate(uniq_id: str):
    row = _df[_df["uniq_id"] == uniq_id]
    if row.empty:
        return {"uniq_id": uniq_id, "generated_description": ""}
    text = runtime.generate_description(row.iloc[0].to_dict())
    return {"uniq_id": uniq_id, "generated_description": text}

# CV: zero-shot category prediction from image URL
@app.get("/classify")
def classify(image_url: str):
    try:
        pred = runtime.classify_url(image_url)
        return {"predicted_category": pred}
    except Exception as e:
        return {"predicted_category": "", "error": str(e)}
