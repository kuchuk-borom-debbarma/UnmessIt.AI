import re
from typing import Any


def normalize_plan_json(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    normalized = dict(data)
    for key in ("search_queries", "must_find", "constraints"):
        normalized[key] = string_list(normalized.get(key))
    return normalized


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [f"{key}: {val}" for key, val in value.items() if str(val).strip()]
    return [str(value)]


def normalize_query(query: str) -> str:
    return re.sub(r"^\s*\d+[\).\:-]?\s*", "", query).strip() or query
