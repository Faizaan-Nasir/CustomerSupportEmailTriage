"""Gemini client wrapper for backend LLM interactions."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.config import settings


class LLMClientError(RuntimeError):
    """Raised when an LLM request fails after all retry attempts."""


def _import_gemini_sdk() -> Any:
    """Import the Gemini SDK lazily so the app can boot without the package."""
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "The 'google-generativeai' package is required to use the Gemini client. "
            "Install backend dependencies in the project venv before running this module."
        ) from exc
    return genai


@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response payload."""

    text: str
    raw: Any

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "raw": self.raw}


class GeminiClient:
    """Thin wrapper around Gemini text generation with retry support."""

    DEFAULT_MODEL_CANDIDATES = (
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-flash-latest",
        "models/gemini-pro-latest",
    )

    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            genai = _import_gemini_sdk()
            genai.configure(api_key=self.api_key)
            resolved_name = self.model_name or self._resolve_model_name(genai)
            self._model = genai.GenerativeModel(resolved_name)
        return self._model

    def _resolve_model_name(self, genai: Any) -> str:
        available_models = {
            model.name
            for model in genai.list_models()
            if "generateContent" in getattr(model, "supported_generation_methods", [])
        }

        for candidate in self.DEFAULT_MODEL_CANDIDATES:
            if candidate in available_models:
                self.model_name = candidate
                return candidate

        if available_models:
            self.model_name = sorted(available_models)[0]
            return self.model_name

        raise LLMClientError("No Gemini models with generateContent support were found.")

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if text:
            return str(text).strip()

        candidates = getattr(response, "candidates", None) or []
        parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts.append(str(part_text))

        return "\n".join(parts).strip()

    def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        expect_json: bool = False,
    ) -> dict[str, Any]:
        """Generate text from Gemini and return a normalized payload."""
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        generation_config: dict[str, Any] = {
            "temperature": temperature,
        }
        if expect_json:
            generation_config["response_mime_type"] = "application/json"

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._get_model().generate_content(
                    prompt,
                    generation_config=generation_config,
                )
                text = self._extract_text(response)
                if not text:
                    raise LLMClientError("Gemini returned an empty response.")

                if expect_json:
                    json.loads(text)

                return LLMResponse(text=text, raw=response).to_dict()
            except Exception as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds)

        raise LLMClientError(
            f"Gemini request failed after {self.max_retries} attempts."
        ) from last_error


_client: GeminiClient | None = None


def get_client() -> GeminiClient:
    """Return a singleton Gemini client."""
    global _client
    if _client is None:
        _client = GeminiClient(api_key=settings.gemini_api_key)
    return _client
