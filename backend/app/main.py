"""
AI Recos Backend — FastAPI + FAISS + Pandas + LangChain Community
Optimized for Render deployment.
"""

import os
import math
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# -------- Lazy imports for large modules (avoid Render timeouts) --------
try:
    from .models_runtime import Runtime
    from .vector_store import load_or_build_faiss
except Exception as e:
    Runtime = None
    load_or_build_faiss = None
    print(f"[WARN] Optional imports failed (will be loaded lazily): {e}")

# ------------------------------------------------------------
# ✅ FastAPI app configuration
# ------------------------------------------------------------
app = FastAPI(
    title="AI Recos Backend",
    description="AI-powered recommendation & analytics service.",
    version="1.0.0"
)

# ------------------------------------------------------------
# ✅ CORS (allow frontend + dev)
# ------------------------------------------------------------
origins = [
    "*",  # Allow all origins for testing
    "http://localhost:5173",           # Vite local dev
    "https://*.vercel.app",            # Vercel deployments
    "https://ai-recos-frontend.vercel.app",  # production frontend (optional)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# ✅ Basic routes (health + home)
# ------------------------------------------------------------
@app.get("/healthz")
def health_check():
    """Render uses this endpoint for health checks."""
    return {"status": "ok", "message": "Backend is healthy."}

@app.get("/")
def home():
    return {"message": "AI-Recos backend is live 🚀"}

# ------------------------------------------------------------
# ✅ Lazy data and runtime initialization
# ------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CSV = os.path.join(REPO_ROOT, "data", "products.csv")
CSV_PATH = os.getenv("DATA_CSV", DEFAULT_CSV)

runtime = None
store = None
_df = None

@app.on_event("startup")
def load_runtime():
    """Lazy-load Runtime & FAISS only once when server starts."""
    global runtime, store, _df
    try:
        if Runtime is None or load_or_build_faiss is None:
            from .models_runtime import Runtime
            from .vector_store import load_or_build_faiss

        runtime = Runtime(CSV_PATH)
        store = load_or_build_faiss(runtime)
        _df = runtime.df
        print(f"[INFO] Runtime initialized with {len(_df)} rows.")
    except Exception as e:
        print(f"[ERROR] Runtime initialization failed: {e}")
        runtime, store, _df = None, None, pd.DataFrame()

# ------------------------------------------------------------
# ✅ Utility functions for safe JSON serialization
# ------------------------------------------------------------
def _to_py_scalar(x):
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x

def _sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return _to_py_scalar(obj)

# ------------------------------------------------------------
# ✅ API: dataset summary
# ------------------------------------------------------------
@app.get("/summary")
def summary():
    if _df is None or _df.empty:
        raise HTTPException(status_code=500, detail="Runtime not initialized or dataset empty.")

    try:
        return {"ok": True, "rows": len(_df), "csv": os.path.relpath(CSV_PATH, REPO_ROOT)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {e}")

# ------------------------------------------------------------
# ✅ API: analytics summary (categories + price stats)
# ------------------------------------------------------------
@app.get("/analytics/summary")
def analytics_summary():
    if _df is None or _df.empty:
        raise HTTPException(status_code=500, detail="Dataset not loaded.")

    try:
        # Category counts
        if "category_main" in _df.columns:
            cat_series = _df["category_main"].fillna("").astype(str)
        else:
            cat_series = _df.get("categories", pd.Series([], dtype=str)).fillna("").astype(str)
            cat_series = cat_series.apply(lambda s: s.split(",")[0].strip() if s else "")

        category_counts = {str(k): int(v) for k, v in cat_series.value_counts().items()}

        # Price stats
        price_series = pd.to_numeric(_df.get("price", pd.Series([], dtype="float64")), errors="coerce").dropna()
        stats = price_series.describe().to_dict() if not price_series.empty else {}
        price_stats = {k: _to_py_scalar(v) for k, v in stats.items()}

        return _sanitize({"category_counts": category_counts, "price_stats": price_stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {e}")

# ------------------------------------------------------------
# ✅ API: debug columns
# ------------------------------------------------------------
@app.get("/debug/columns")
def debug_columns():
    if _df is None:
        raise HTTPException(status_code=500, detail="Dataset not loaded.")
    return {
        "rows": int(len(_df)),
        "columns": list(map(str, _df.columns)),
        "sample": _df.head(3).to_dict(orient="records"),
    }

# ------------------------------------------------------------
# ✅ API: semantic search
# ------------------------------------------------------------
@app.get("/search")
def search(q: str = Query(..., min_length=2), k: int = 6):
    if store is None:
        raise HTTPException(status_code=500, detail="FAISS store not initialized.")
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

# ------------------------------------------------------------
# ✅ API: recommendations by uniq_id
# ------------------------------------------------------------
@app.get("/recommend/{uniq_id}")
def recommend(uniq_id: str, k: int = 5):
    if _df is None or store is None:
        raise HTTPException(status_code=500, detail="Runtime or store not ready.")
    try:
        rows = _df[_df["uniq_id"] == uniq_id]
        if rows.empty:
            return {"recommended": []}
        qdoc = rows.iloc[0]["doc"]
        res = store.similarity_search(qdoc, k=k + 1)
        out = []
        for r in res:
            md = r.metadata
            if md.get("uniq_id") == uniq_id:
                continue
            out.append({
                "uniq_id": md.get("uniq_id"),
                "title": md.get("title"),
                "brand": md.get("brand"),
                "price": md.get("price"),
                "categories": md.get("categories"),
                "images": md.get("images"),
            })
            if len(out) == k:
                break
        return {"recommended": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {e}")

# ------------------------------------------------------------
# ✅ API: generate creative description
# ------------------------------------------------------------
@app.get("/generate/{uniq_id}")
def generate(uniq_id: str):
    if runtime is None:
        raise HTTPException(status_code=500, detail="Runtime not initialized.")
    try:
        row = _df[_df["uniq_id"] == uniq_id]
        if row.empty:
            return {"uniq_id": uniq_id, "generated_description": ""}
        text = runtime.generate_description(row.iloc[0].to_dict())
        return {"uniq_id": uniq_id, "generated_description": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

# ------------------------------------------------------------
# ✅ API: classify image
# ------------------------------------------------------------
@app.get("/classify")
def classify(image_url: str):
    if runtime is None:
        raise HTTPException(status_code=500, detail="Runtime not initialized.")
    try:
        pred = runtime.classify_url(image_url)
        return {"predicted_category": pred}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")
