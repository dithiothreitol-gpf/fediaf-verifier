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
    def _null_to_empty(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        field_types = cls.model_fields
        for key, val in list(data.items()):
            if val is None and key in field_types:
                annotation = field_types[key].annotation
                origin = typing.get_origin(annotation)
                if annotation is str:
                    data[key] = ""
                elif annotation is bool:
                    data[key] = False
                elif annotation is int:
                    data[key] = 0
                elif origin is list:
                    data[key] = []
        return data
