"""Retrieval helpers for attachment-backed ticket context."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.rag.indexer import generate_query_embedding
from app.repositories.attachment_repo import AttachmentRecord, list_attachments_for_ticket


class RetrieverError(RuntimeError):
    """Raised when retrieval cannot be completed."""


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise RetrieverError(
            f"Embedding dimension mismatch during retrieval: {len(left)} vs {len(right)}."
        )

    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return numerator / (left_norm * right_norm)


@dataclass
class RAGRetriever:
    """Fetch relevant attachment chunks using query/document embedding similarity."""

    top_k: int = 3

    def retrieve(self, query: str, ticket_id: str, top_k: int | None = None) -> dict[str, list[str]]:
        """Return the most relevant parsed attachment chunks for a ticket."""
        effective_top_k = top_k or self.top_k
        if effective_top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        attachments = list_attachments_for_ticket(ticket_id)
        if not attachments:
            return {"chunks": []}

        query_embedding = generate_query_embedding(query)

        ranked: list[tuple[float, AttachmentRecord]] = []
        for attachment in attachments:
            parsed_text = attachment.get("parsed_text")
            embedding = attachment.get("embedding")
            if not parsed_text or not embedding:
                continue
            score = _cosine_similarity(query_embedding, embedding)
            ranked.append((score, attachment))

        ranked.sort(key=lambda item: item[0], reverse=True)
        chunks = [record["parsed_text"] for _, record in ranked[:effective_top_k]]
        return {"chunks": chunks}


_retriever: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    """Return a singleton retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def retrieve_relevant_chunks(query: str, ticket_id: str, top_k: int = 3) -> dict[str, list[str]]:
    """Compatibility helper matching the technical document wording."""
    return get_retriever().retrieve(query=query, ticket_id=ticket_id, top_k=top_k)

