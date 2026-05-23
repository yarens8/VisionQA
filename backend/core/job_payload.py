from collections.abc import Mapping
from typing import Any


def to_json_payload(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, Mapping):
        return dict(result)
    if isinstance(result, list):
        return [to_json_payload(item) for item in result]
    if isinstance(result, tuple):
        return [to_json_payload(item) for item in result]
    return result
