"""
Dense Semantic Retriever — Embedding-based Recall Expansion

Loads sentence-transformers/all-MiniLM-L6-v2 ONCE at startup.
Encodes the full catalog into a normalized embedding matrix.
Returns top-k semantically similar catalog items for a given query.

CPU-only. No external APIs. No ranking. No filtering.
"""
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer


class DenseRetriever:
    def __init__(self, catalog: List[Dict[str, Any]]):
        self.model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2', device='cpu'
        )
        self.catalog = catalog
        self.embeddings_matrix = None
        self._index_catalog()

    def _index_catalog(self):
        """Encode every catalog item into a single text field and build the embedding matrix."""
        texts = []
        for item in self.catalog:
            title = item.get("title", item.get("name", ""))
            description = item.get("description", "")

            competencies = item.get("competencies", [])
            if isinstance(competencies, list):
                comp_str = " ".join([str(c) for c in competencies])
            else:
                comp_str = str(competencies)

            tags = item.get("tags", item.get("keys", []))
            if isinstance(tags, list):
                tags_str = " ".join([str(t) for t in tags])
            else:
                tags_str = str(tags)

            text = f"{title} {description} {comp_str} {tags_str}"
            texts.append(text)

        self.embeddings_matrix = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )

    def search(self, query: str, k: int = 50) -> List[dict]:
        """Return top-k catalog items by cosine similarity. No ranking. No filtering."""
        if not query or not query.strip():
            return []

        query_embedding = self.model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )
        # Normalized vectors → dot product == cosine similarity
        similarities = self.embeddings_matrix @ query_embedding[0]

        top_indices = np.argsort(similarities)[::-1][:k]

        return [self.catalog[int(i)] for i in top_indices]
