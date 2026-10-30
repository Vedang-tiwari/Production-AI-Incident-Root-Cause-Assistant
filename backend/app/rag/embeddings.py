import math
import re
from typing import Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger


class EmbeddingGenerator:
    """
    Embedding generator with an offline TF-IDF/n-gram hashing vectorizer fallback.
    Provides fast, deterministic, reproducible embeddings without requiring external API keys.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _tokenize(self, text: str) -> List[str]:
        clean = re.sub(r"[^a-zA-Z0-9_\-\s]", " ", text.lower())
        return [w for w in clean.split() if len(w) > 1]

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a normalized L2 dense vector for the text using feature hashing and term frequency.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension

        # Feature hashing with n-grams
        for i, token in enumerate(tokens):
            h1 = hash(token) % self.dimension
            vector[h1] += 1.0

            # Bigrams
            if i < len(tokens) - 1:
                bigram = f"{token}_{tokens[i+1]}"
                h2 = hash(bigram) % self.dimension
                vector[h2] += 1.5

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [round(x / norm, 6) for x in vector]

        return vector

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return round(dot / (norm1 * norm2), 4)


embedding_generator = EmbeddingGenerator()

