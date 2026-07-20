from typing import Any

from fastapi.encoders import jsonable_encoder

from app.core.logging import request_id_ctx


def envelope(data: Any) -> dict:
    """The standard success envelope every endpoint returns (API Spec §0.2):
    `{"data": ..., "meta": {"request_id": ...}}`. Pydantic models are encoded the same way
    FastAPI would encode them as a bare response, so callers can pass a model instance,
    a dict, or a primitive interchangeably."""
    return {"data": jsonable_encoder(data), "meta": {"request_id": request_id_ctx.get()}}
