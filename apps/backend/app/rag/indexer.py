"""Embedding and indexing helpers for attachment-backed RAG data."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.repositories.attachment_repo import create_attachment


class IndexerError(RuntimeError):
    """Raised when attachment text cannot be embedded or stored."""


def _import_gemini_sdk() -> Any:
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "The 'google-generativeai' package is required to generate embeddings."
        ) from exc
    return genai


def _normalize_text(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        raise IndexerError("Cannot index empty text.")
    return normalized


@dataclass
class RAGIndexer:
    """Generate embeddings and persist them into the attachments table."""

    DEFAULT_MODEL_CANDIDATES = (
        "models/gemini-embedding-001",
        "models/gemini-embedding-2",
        "models/gemini-embedding-2-preview",
    )

    model_name: str | None = settings.embedding_model
    embedding_dimension: int = settings.embedding_dimension

    def _resolve_model_name(self, genai: Any) -> str:
        available_models = {
            model.name
            for model in genai.list_models()
            if "embedContent" in getattr(model, "supported_generation_methods", [])
        }

        configured = self.model_name
        if configured and configured in available_models:
            return configured

        normalized_configured = (
            f"models/{configured}" if configured and not configured.startswith("models/") else configured
        )
        if normalized_configured and normalized_configured in available_models:
            self.model_name = normalized_configured
            return normalized_configured

        for candidate in self.DEFAULT_MODEL_CANDIDATES:
            if candidate in available_models:
                self.model_name = candidate
                return candidate

        if available_models:
            self.model_name = sorted(available_models)[0]
            return self.model_name

        raise IndexerError("No Gemini models with embedContent support were found.")

    def _embed_text(self, text: str, *, task_type: str) -> list[float]:
        """Generate an embedding using the configured Gemini model."""
        normalized_text = _normalize_text(text)

        genai = _import_gemini_sdk()
        genai.configure(api_key=settings.gemini_api_key)
        resolved_model = self._resolve_model_name(genai)

        # The Gemini SDK surface varies across versions. `google-generativeai==0.4.0`
        # does not support `output_dimensionality`, while newer builds may.
        embed_params = set(inspect.signature(genai.embed_content).parameters)
        supports_output_dim = "output_dimensionality" in embed_params

        embed_kwargs: dict[str, Any] = {
            "model": resolved_model,
            "content": normalized_text,
            "task_type": task_type,
        }
        if supports_output_dim and self.embedding_dimension > 0:
            embed_kwargs["output_dimensionality"] = int(self.embedding_dimension)

        response = genai.embed_content(**embed_kwargs)

        embedding = response.get("embedding")
        if embedding is None:
            raise IndexerError("Embedding response did not include an embedding vector.")

        vector = [float(value) for value in embedding]
        
        # Truncate or pad to match the configured embedding_dimension (1536).
        # The Supabase attachments table has a vector(1536) column.
        if len(vector) > self.embedding_dimension:
            vector = vector[:self.embedding_dimension]
        elif len(vector) < self.embedding_dimension:
            vector.extend([0.0] * (self.embedding_dimension - len(vector)))
        
        return vector

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a document embedding using the configured Gemini model."""
        return self._embed_text(text, task_type="retrieval_document")

    def generate_query_embedding(self, text: str) -> list[float]:
        """Generate a query embedding for retrieval-time similarity search."""
        return self._embed_text(text, task_type="retrieval_query")

    def index_attachment(self, ticket_id: str, file_url: str, parsed_text: str) -> dict[str, str]:
        """Generate an embedding for parsed text and store it in Supabase."""
        embedding = self.generate_embedding(parsed_text)
        return create_attachment(
            {
                "ticket_id": ticket_id,
                "file_url": file_url,
                "parsed_text": parsed_text,
                "embedding": embedding,
            }
        )


_indexer: RAGIndexer | None = None


def get_indexer() -> RAGIndexer:
    """Return a singleton indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = RAGIndexer()
    return _indexer


def generate_embedding(text: str) -> list[float]:
    """Compatibility helper for direct embedding generation."""
    return get_indexer().generate_embedding(text)


def generate_query_embedding(text: str) -> list[float]:
    """Compatibility helper for query-time embedding generation."""
    return get_indexer().generate_query_embedding(text)


def index_attachment(ticket_id: str, file_url: str, parsed_text: str) -> dict[str, str]:
    """Compatibility helper for end-to-end attachment indexing."""
    return get_indexer().index_attachment(ticket_id, file_url, parsed_text)
