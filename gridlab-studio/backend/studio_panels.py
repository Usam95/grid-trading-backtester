"""Durable synchronized ten-symbol EUR production-archive repository."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from backend import service

DEFAULT_ARCHIVE = (
    Path(__file__).resolve().parent.parent / ".studio" / "production-archive"
)


class StudioProductionPanelRepository:
    """Preview, synchronize, and snapshot the fixed EUR production archive."""

    def __init__(
        self,
        root: Path,
        catalog_client: service.BinanceCatalogClient,
        archive_client: service.ArchiveClient,
    ) -> None:
        self.root = root
        self.catalog_client = catalog_client
        self.archive_client = archive_client
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, *, refresh: bool = False) -> dict[str, object]:
        existing = self.root / "index.json"
        if existing.is_file() and not refresh:
            return service.read_synchronized_production_archive(self.root)
        return service.preview_synchronized_production_archive(
            self.catalog_client,
            self.archive_client,
            self.root,
            retrieved_at=datetime.now(timezone.utc),
        )

    def synchronize(self) -> dict[str, object]:
        return service.synchronize_synchronized_production_archive(
            self.catalog_client,
            self.archive_client,
            self.root,
            retrieved_at=datetime.now(timezone.utc),
        )

    def create_snapshot(
        self,
        dataset_id: str,
        start: datetime,
        end: datetime,
    ) -> dict[str, object]:
        return service.create_production_snapshot_manifest(
            self.root,
            dataset_id,
            start,
            end,
            retrieved_at=datetime.now(timezone.utc),
        )


def studio_production_panel_repository() -> StudioProductionPanelRepository:
    configured = os.environ.get("GRIDLAB_STUDIO_PRODUCTION_ARCHIVE")
    root = Path(configured) if configured else DEFAULT_ARCHIVE
    return StudioProductionPanelRepository(
        root,
        service.OfficialBinanceCatalogClient(),
        service.OfficialBinanceArchiveClient(),
    )
