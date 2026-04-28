"""Utilities for parsing, repairing, and validating structured LLM output."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


class StructuredOutputError(ValueError):
    """Raised when structured output cannot be repaired or validated."""


def _strip_code_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _extract_json_segment(text: str) -> str:
    start_positions = [index for index in (text.find("{"), text.find("[")) if index != -1]
    if not start_positions:
        return text.strip()

    start = min(start_positions)
    opening = text[start]
    closing = "}" if opening == "{" else "]"

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()

    return text[start:].strip()


def _normalize_json_like_text(raw_text: str) -> str:
    text = _strip_code_fences(raw_text)
    text = _extract_json_segment(text)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    return text.strip()


def _repair_json(raw_text: str) -> Any:
    normalized = _normalize_json_like_text(raw_text)

    try:
        return json.loads(normalized)
    except json.JSONDecodeError:
        pass

    try:
        python_object = ast.literal_eval(normalized)
    except (SyntaxError, ValueError) as exc:
        raise StructuredOutputError("Unable to repair malformed JSON output.") from exc

    try:
        json.dumps(python_object)
    except TypeError as exc:
        raise StructuredOutputError("Repaired output is not JSON-serializable.") from exc

    return python_object


def _validate_type(value: Any, expected_type: str) -> bool:
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    python_type = type_map.get(expected_type)
    if python_type is None:
        return True
    if expected_type == "number":
        return isinstance(value, python_type) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, python_type)


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected_type = schema.get("type")
    if expected_type and not _validate_type(value, expected_type):
        raise StructuredOutputError(
            f"Schema validation failed at {path}: expected {expected_type}, "
            f"received {type(value).__name__}."
        )

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        raise StructuredOutputError(
            f"Schema validation failed at {path}: value {value!r} not in enum."
        )

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise StructuredOutputError(
                    f"Schema validation failed at {path}: missing required key {key!r}."
                )

        properties = schema.get("properties", {})
        for key, child_schema in properties.items():
            if key in value:
                _validate_schema(value[key], child_schema, f"{path}.{key}")

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for index, item in enumerate(value):
            _validate_schema(item, item_schema, f"{path}[{index}]")


def validate_structured_output(raw_text: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Repair JSON-like text when possible and validate it against a schema."""
    repaired = _repair_json(raw_text)
    _validate_schema(repaired, schema)
    return {"validated_json": repaired}

