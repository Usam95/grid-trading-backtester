from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping

from gridlab.canonical._identity import content_identity, identity_payload


@dataclass(frozen=True, slots=True)
class DomainTime:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None or self.value.utcoffset() is None:
            raise ValueError("domain time must be timezone-aware")
        object.__setattr__(self, "value", self.value.astimezone(timezone.utc))

    def identity_payload(self) -> str:
        return self.value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class EventSource:
    system: str
    stream: str

    def __post_init__(self) -> None:
        if not self.system or not self.stream:
            raise ValueError("event source system and stream are required")


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    schema: str
    source: EventSource
    source_event_key: str
    source_sequence: int
    event_time: DomainTime
    received_time: DomainTime
    correlation_id: str
    causation_id: str | None
    payload_items: tuple[tuple[str, Any], ...]

    def __post_init__(self) -> None:
        if not self.schema or not self.source_event_key or not self.correlation_id:
            raise ValueError("schema, source event key, and correlation identity are required")
        if self.source_sequence < 0:
            raise ValueError("source sequence must be non-negative")
        if not re.fullmatch(r"^[a-z0-9-]+/v[1-9][0-9]*$", self.schema):
            raise ValueError("canonical event schema identity is invalid")
        keys = tuple(key for key, _ in self.payload_items)
        if any(not isinstance(key, str) for key in keys):
            raise TypeError("canonical event payload keys must be strings")
        if len(set(keys)) != len(keys):
            raise ValueError("canonical event payload keys must be unique")
        frozen = tuple(
            (key, _freeze_payload(value))
            for key, value in sorted(self.payload_items, key=lambda item: item[0])
        )
        object.__setattr__(self, "payload_items", frozen)

    @classmethod
    def create(
        cls,
        *,
        schema: str,
        source: EventSource,
        source_event_key: str,
        source_sequence: int,
        event_time: DomainTime,
        received_time: DomainTime,
        correlation_id: str,
        causation_id: str | None,
        payload: Mapping[str, Any],
    ) -> CanonicalEvent:
        if any(not isinstance(key, str) for key in payload):
            raise TypeError("canonical event payload keys must be strings")
        payload_items = tuple(
            (str(key), _freeze_payload(value))
            for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
        )
        return cls(
            schema=schema,
            source=source,
            source_event_key=source_event_key,
            source_sequence=source_sequence,
            event_time=event_time,
            received_time=received_time,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload_items=payload_items,
        )

    @property
    def payload(self) -> dict[str, Any]:
        return {key: _thaw_payload(value) for key, value in self.payload_items}

    @property
    def event_id(self) -> str:
        return content_identity("canonical-event/v1", self.identity_payload())

    @property
    def admission_fingerprint(self) -> str:
        return content_identity(
            "canonical-admitted-event/v1",
            {
                "event": self.identity_payload(),
                "received_time": identity_payload(self.received_time),
            },
        )

    @property
    def ordering_key(self) -> tuple[datetime, str, str, int, str]:
        return (
            self.event_time.value,
            self.source.system,
            self.source.stream,
            self.source_sequence,
            self.event_id,
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source": identity_payload(self.source),
            "source_event_key": self.source_event_key,
            "source_sequence": self.source_sequence,
            "event_time": identity_payload(self.event_time),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": identity_payload(self.payload),
        }


def _freeze_payload(value: Any) -> Any:
    _validate_payload_keys(value)
    material = identity_payload(value)
    if isinstance(material, Mapping):
        return tuple(
            (str(key), _freeze_payload(item))
            for key, item in sorted(material.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(material, (tuple, list)):
        return tuple(_freeze_payload(item) for item in material)
    if isinstance(material, float):
        raise TypeError("canonical event payload floats are not source-exact")
    if material is None or isinstance(material, (bool, int, str)):
        return material
    raise TypeError(f"canonical event payload contains unsupported {type(value).__name__}")


def _validate_payload_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical event payload keys must be strings")
        for item in value.values():
            _validate_payload_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _validate_payload_keys(item)


def _thaw_payload(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {key: _thaw_payload(item) for key, item in value}
        return [_thaw_payload(item) for item in value]
    return value
