from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


def identity_payload(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return value.identity_payload()
    if is_dataclass(value):
        return {
            field.name: identity_payload(getattr(value, field.name))
            for field in fields(value)
            if field.name not in {"presentation"}
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, timedelta):
        return int(value.total_seconds() * 1_000_000)
    if isinstance(value, Mapping):
        return {
            str(key): identity_payload(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [identity_payload(item) for item in value]
    return value


def content_identity(namespace: str, value: Any) -> str:
    encoded = json.dumps(
        {"namespace": namespace, "value": identity_payload(value)},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
