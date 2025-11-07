import os, numpy as np, hashlib, json
from typing import List

def _deterministic_random_vector(dim: int, seed_text: str) -> List[float]:
    # Deterministic vector for dev/testing
    seed = int(hashlib.sha256(seed_text.encode('utf-8')).hexdigest(), 16) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    v = rng.normal(0, 1, size=dim).astype('float32')
    # L2 normalize
    norm = np.linalg.norm(v) + 1e-8
    return (v / norm).tolist()

def embed_texts(texts: List[str]) -> List[List[float]]:
    dim = int(os.getenv('EMBED_DIM', '1536'))
    which = os.getenv('EMBEDDER', 'random').lower()
    if which == 'random':
        return [_deterministic_random_vector(dim, t) for t in texts]
    elif which == 'openai':
        # Lazy import to keep optional
        import requests, os
        api_key = os.getenv('OPENAI_API_KEY')
        model = os.getenv('OPENAI_EMBED_MODEL', 'text-embedding-3-large')
        if not api_key:
            raise RuntimeError('OPENAI_API_KEY not set')
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        resp = requests.post('https://api.openai.com/v1/embeddings', headers=headers, json={'model': model, 'input': texts}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return [x['embedding'] for x in data['data']]
    elif which == 'sentence-transformers':
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv('ST_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')
        model = SentenceTransformer(model_name)
        embs = model.encode(texts, normalize_embeddings=True)
        return [e.tolist() for e in embs]
    else:
        raise ValueError(f'Unknown EMBEDDER: {which}')
