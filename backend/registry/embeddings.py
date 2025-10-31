"""
Embeddings Service for Registry
---------------------------------
Handles semantic embedding generation using sentence-transformers.
"""

from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating semantic embeddings"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding service with specified model.

        Args:
            model_name: HuggingFace model name for embeddings
        """
        self.model_name = model_name
        self.model = None
        self.dimension = 384  # Default dimension for all-MiniLM-L6-v2

        logger.info(f"Initializing embedding service with model: {model_name}")

    def _load_model(self):
        """Lazy load the model on first use"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        self._load_model()

        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)

        # Convert to list and ensure it's the right dimension
        vector = embedding.tolist()

        if len(vector) != self.dimension:
            logger.warning(
                f"Embedding dimension mismatch: expected {self.dimension}, got {len(vector)}"
            )

        return vector

    def embed_agent_description(self, agent_name: str, agent_description: str, capabilities: List[dict]) -> List[float]:
        """
        Generate embedding for an agent based on its description and capabilities.

        This creates a rich text representation of the agent that can be used for
        semantic search and discovery.

        Args:
            agent_name: Name of the agent
            agent_description: Agent description
            capabilities: List of capability dictionaries

        Returns:
            List of floats representing the embedding vector
        """
        # Create a comprehensive text representation
        text_parts = [
            f"Agent: {agent_name}",
            f"Description: {agent_description}",
        ]

        # Add capability descriptions
        for cap in capabilities:
            cap_desc = cap.get("description", "")
            if cap_desc:
                text_parts.append(f"Capability: {cap_desc}")

        # Combine all parts
        full_text = " | ".join(text_parts)

        logger.debug(f"Generating embedding for agent text: {full_text[:100]}...")

        return self.embed_text(full_text)

    def compute_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vector1: First embedding vector
            vector2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        # Convert to numpy arrays
        v1 = np.array(vector1)
        v2 = np.array(vector2)

        # Compute cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure it's in [0, 1] range (cosine similarity is in [-1, 1])
        # We convert to [0, 1] by: (sim + 1) / 2
        # But typically for semantic search, we just use the raw value clipped to [0, 1]
        return float(max(0.0, min(1.0, similarity)))


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
