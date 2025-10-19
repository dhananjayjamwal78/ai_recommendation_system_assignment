import os, io, re, torch, requests
import pandas as pd
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, CLIPModel, CLIPProcessor

class Runtime:
    """
    Holds dataset and lightweight models used at runtime:
    - SBERT text embedder
    - DistilGPT-2 for short creative descriptions
    - CLIP for zero-shot image classification
    """
    def __init__(self, csv_path: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found at {csv_path}")

        # ------- Data -------
        self.df = pd.read_csv(csv_path).fillna("")
        # main category (first of comma-separated list)
        self.df["category_main"] = self.df.get("categories", "").astype(str).apply(self._first_cat)
        # one "doc" text used for embeddings
        self.df["doc"] = self.df.apply(
            lambda r: self._coalesce(r.get("title"), r.get("brand"), r.get("description"),
                                     r.get("material"), r.get("color")),
            axis=1
        )

        # ------- Models -------
        # 1) Text embeddings (fast, 384-dim, good quality)
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # 2) GenAI: small GPT-2
        self.gen_tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
        self.gen_model = AutoModelForCausalLM.from_pretrained("distilgpt2")

        # 3) Zero-shot CLIP for CV
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        # label list for CLIP prompts
        labels = sorted(list({c for c in self.df["category_main"].tolist() if c}))
        self.category_labels = labels

    # ---------- Helpers ----------
    @staticmethod
    def _coalesce(*vals):
        return " ".join([str(v) for v in vals if pd.notna(v) and str(v).strip()])

    @staticmethod
    def _first_cat(s):
        parts = [p.strip() for p in str(s).split(",") if p.strip()]
        return parts[0] if parts else ""

    @staticmethod
    def _first_img(s):
        s = str(s)
        return s.split(",")[0].strip() if s else ""

    # ---------- GenAI ----------
    def generate_description(self, row: dict) -> str:
        prompt = (
            f"Write a catchy 2-sentence product description.\n"
            f"Title: {row.get('title','')}\n"
            f"Brand: {row.get('brand','')}\n"
            f"Material: {row.get('material','')}\n"
            f"Color: {row.get('color','')}\n"
            f"Description:"
        )
        ids = self.gen_tokenizer.encode(prompt, return_tensors="pt")
        with torch.no_grad():
            out = self.gen_model.generate(
                ids,
                max_length=ids.shape[1] + 60,
                do_sample=True,
                top_p=0.92,
                top_k=40,
                temperature=0.8,
                pad_token_id=self.gen_tokenizer.eos_token_id,
            )
        text = self.gen_tokenizer.decode(out[0], skip_special_tokens=True)
        return text.split("Description:")[-1].strip()

    # ---------- CV ----------
    def classify_url(self, image_url: str) -> str:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")

        texts = [f"a photo of {c}" for c in self.category_labels] or ["a product"]
        inputs = self.clip_proc(text=texts, images=img, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = self.clip_model(**inputs).logits_per_image[0]
            idx = int(torch.argmax(logits))
        return self.category_labels[idx] if self.category_labels else "unknown"
