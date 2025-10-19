import os
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings

# ----- LangChain-compatible embedding wrapper -----
class SBERTEmbeddings(Embeddings):
    def __init__(self, sbert):
        self.sbert = sbert

    def embed_documents(self, texts):
        return self.sbert.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text):
        return self.sbert.encode([text], normalize_embeddings=True)[0].tolist()

# ----- Paths & ENV knobs -----
# repo_root/backend/app/vector_store.py  -> go up to repo root then models/faiss
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODELS_FAISS_DIR = os.path.join(REPO_ROOT, "models", "faiss")
DEFAULT_FAISS_SUBDIR = os.getenv("FAISS_SUBDIR", "sbert_faiss")
FORCE_REBUILD = os.getenv("FAISS_FORCE_REBUILD", "0") == "1"

def _faiss_path():
    return os.path.join(MODELS_FAISS_DIR, DEFAULT_FAISS_SUBDIR)

# ----- Load or build FAISS -----
def load_or_build_faiss(runtime):
    """
    Try loading FAISS index from models/faiss/<subdir>.
    If not found (or FORCE_REBUILD=1), build from runtime.df and save.
    """
    target = _faiss_path()
    emb = SBERTEmbeddings(runtime.embedder)

    if not FORCE_REBUILD and os.path.exists(os.path.join(target, "index.faiss")):
        # allow_dangerous_deserialization is needed to load pickled metadatas
        store = FAISS.load_local(target, embeddings=emb, allow_dangerous_deserialization=True)
        return store

    # Build from scratch
    texts = runtime.df["doc"].tolist()
    metas = runtime.df.to_dict(orient="records")
    store = FAISS.from_texts(texts, embedding=emb, metadatas=metas)

    # Save for next boots (optional but handy)
    os.makedirs(target, exist_ok=True)
    store.save_local(target)
    return store
