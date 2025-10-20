import os
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import numpy as np
import pandas as pd,math
from .models_runtime import Runtime
from .vector_store import load_or_build_faiss

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  
)
@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.get("/")
def home():
    return {"message": "AI-Recos backend is live!"}

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

def _to_py_scalar(x):
    # unwrap numpy scalars
    if isinstance(x, np.generic):
        x = x.item()
    # replace NaN/inf with None for JSON
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x

def _sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return _to_py_scalar(obj)

# ---------- Routes ----------
@app.get("/")
def health():
    return {"ok": True, "rows": int(len(_df)), "csv": os.path.relpath(CSV_PATH, REPO_ROOT)}

# Analytics summary for frontend charts
@app.get("/analytics/summary")
def analytics():
    try:
        # ---- categories ----
        if "category_main" in _df.columns:
            cat_series = _df["category_main"].fillna("").astype(str)
        else:
            cat_series = _df.get("categories", pd.Series([], dtype=str)).fillna("").astype(str)
            cat_series = cat_series.apply(lambda s: s.split(",")[0].strip() if s else "")

        category_counts = {str(k): int(v) for k, v in cat_series.value_counts().items()}

        # ---- prices ----
        price_series = pd.to_numeric(_df.get("price", pd.Series([], dtype="float64")), errors="coerce")
        price_series = price_series.dropna()

        if price_series.empty:
            # explicit schema with nulls if no numeric prices
            price_stats = {"count": 0, "mean": None, "std": None,
                           "min": None, "25%": None, "50%": None, "75%": None, "max": None}
        else:
            stats = price_series.describe().to_dict()
            price_stats = {k: _to_py_scalar(v) for k, v in stats.items()}

        return _sanitize({"category_counts": category_counts, "price_stats": price_stats})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analytics failed: {e}")

@app.get("/debug/columns")
def debug_columns():
    return {
        "rows": int(len(_df)),
        "columns": list(map(str, _df.columns)),
        "sample": _df.head(3).to_dict(orient="records"),
    }


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
