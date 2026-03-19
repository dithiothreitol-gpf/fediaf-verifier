"""Shared base model with null-safe validation for AI responses."""

from __future__ import annotations

import typing
from typing import Any

from pydantic import BaseModel, model_validator


class NullSafeBase(BaseModel):
    """BaseModel that converts None to safe defaults before validation.

    AI models frequently return null for optional string/list fields even
    when the prompt asks for empty strings or arrays. This avoids Pydantic
    validation errors without loosening the type system.
    """

    @model_validator(mode="before")
    @classmethod
    def _coerce_ai_types(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        field_types = cls.model_fields
        for key, val in list(data.items()):
            if key not in field_types:
                continue
            annotation = field_types[key].annotation
            origin = typing.get_origin(annotation)

            if val is None:
                # None → safe default
                if annotation is str:
                    data[key] = ""
                elif annotation is bool:
                    data[key] = False
                elif annotation is int:
                    data[key] = 0
                elif origin is list:
                    data[key] = []
            elif annotation is str and not isinstance(val, str):
                # AI returned dict/list/number instead of string — coerce
                import json as _json

                if isinstance(val, dict):
                    # Flatten dict to readable text
                    parts = []
                    for k, v in val.items():
                        parts.append(f"{k}: {v}")
                    data[key] = "\n".join(parts)
                elif isinstance(val, list):
                    data[key] = "\n".join(str(item) for item in val)
                else:
                    data[key] = str(val)
        return data
