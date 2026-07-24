"""Durable local repository for manifested production research datasets."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from backend import service


DEFAULT_DATASETS = Path(__file__).resolve().parent.parent / ".studio" / "datasets"


class StudioDatasetRepository:
    """Persist server-owned previews and admitted immutable dataset manifests."""

    def __init__(
        self,
        root: Path,
        client: service.ArchiveClient,
        *,
        limits: service.AcquisitionLimits = service.AcquisitionLimits(),
    ) -> None:
        self.root = root
        self.client = client
        self.limits = limits
        self.previews = root / "previews"
        self.admitted = root / "admitted"
        self.previews.mkdir(parents=True, exist_ok=True)
        self.admitted.mkdir(parents=True, exist_ok=True)

    def preview(
        self,
        request: service.ArchiveRequest,
        *,
        catalog_identity: str | None = None,
        symbol_metadata: dict[str, object] | None = None,
        limits: service.AcquisitionLimits | None = None,
    ) -> service.ArchivePreview:
        preview = service.preview_binance_archive(
            request,
            self.client,
            catalog_identity=catalog_identity,
            symbol_metadata=symbol_metadata,
            limits=limits or self.limits,
        )
        path = self.previews / f"{preview.preview_id}.json"
        path.write_text(
            json.dumps(asdict(preview), indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return preview

    def get_preview(self, preview_id: str) -> service.ArchivePreview:
        path = self.previews / f"{preview_id}.json"
        if not path.is_file():
            raise service.DataAdmissionError(
                f"download preview not found: {preview_id}"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["preview_id"] != preview_id:
            raise service.DataAdmissionError("download preview identity mismatch")
        return service.ArchivePreview(
            preview_id=payload["preview_id"],
            venue=payload["venue"],
            market=payload["market"],
            symbol=payload["symbol"],
            interval=payload["interval"],
            start=datetime.fromisoformat(payload["start"]),
            end=datetime.fromisoformat(payload["end"]),
            estimated_bytes=payload["estimated_bytes"],
            sources=tuple(
                service.ArchiveSource(**source) for source in payload["sources"]
            ),
            limits=service.AcquisitionLimits(
                **payload.get("limits", asdict(service.AcquisitionLimits()))
            ),
            catalog_identity=payload.get("catalog_identity"),
            symbol_metadata=payload.get("symbol_metadata"),
        )

    def acquire(
        self, preview_id: str, *, retrieved_at: datetime | None = None
    ) -> dict[str, object]:
        preview = self.get_preview(preview_id)
        return service.acquire_binance_archive(
            preview,
            self.client,
            self.admitted,
            retrieved_at=retrieved_at or datetime.now(timezone.utc),
        )

    def manifest_path(self, dataset_id: str) -> Path:
        if len(dataset_id) != 64 or any(
            char not in "0123456789abcdef" for char in dataset_id
        ):
            raise service.DataAdmissionError("invalid dataset identity")
        path = self.admitted / dataset_id / "manifest.json"
        if not path.is_file():
            raise service.DataAdmissionError(
                f"dataset manifest not found: {dataset_id}"
            )
        return path

    def manifest(self, dataset_id: str) -> dict[str, object]:
        return json.loads(self.manifest_path(dataset_id).read_text(encoding="utf-8"))


def studio_dataset_repository() -> StudioDatasetRepository:
    configured = os.environ.get("GRIDLAB_STUDIO_DATASETS")
    root = Path(configured) if configured else DEFAULT_DATASETS
    limits = service.AcquisitionLimits(
        max_days=int(os.environ.get("GRIDLAB_DATA_MAX_DAYS", "7")),
        max_objects=int(os.environ.get("GRIDLAB_DATA_MAX_OBJECTS", "7")),
        max_bytes=int(os.environ.get("GRIDLAB_DATA_MAX_BYTES", str(256 * 1024 * 1024))),
    )
    return StudioDatasetRepository(
        root,
        service.OfficialBinanceArchiveClient(),
        limits=limits,
    )
