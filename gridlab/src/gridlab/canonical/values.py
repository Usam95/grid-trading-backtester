from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


_DECIMAL_PATTERN = r"^-?(?:0|[0-9]+)(?:\.[0-9]+)?$"


@dataclass(frozen=True, slots=True)
class ExactDecimal:
    source: str
    kind: str
    decimal: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.source, str):
            raise TypeError("source-exact decimal input must be a string")
        if not self.kind or self.kind.strip() != self.kind:
            raise ValueError("exact decimal kind must be a non-empty canonical name")
        if not re.fullmatch(_DECIMAL_PATTERN, self.source):
            raise ValueError("source must be a canonical decimal string without exponent")
        if not self.decimal.is_finite() or Decimal(self.source) != self.decimal:
            raise ValueError("source-exact decimal source and decimal must agree")

    @classmethod
    def parse(cls, source: str, *, kind: str) -> ExactDecimal:
        decimal = Decimal(source)
        return cls(source=source, kind=kind, decimal=decimal)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExactDecimal:
        if set(payload) != {"kind", "value"}:
            raise ValueError("exact decimal payload requires only kind and value")
        return cls.parse(payload["value"], kind=payload["kind"])

    @property
    def canonical(self) -> str:
        return format(self.decimal, "f")

    def to_payload(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.source}

    def identity_payload(self) -> dict[str, str]:
        return self.to_payload()
