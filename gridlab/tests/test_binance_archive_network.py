"""Opt-in, one-object acceptance against the official Binance public archive."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gridlab.data.binance_archive import (
    ArchiveRequest,
    OfficialBinanceArchiveClient,
    acquire_binance_archive,
    preview_binance_archive,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("GRIDLAB_REAL_BINANCE_ACCEPTANCE") != "1",
    reason="set GRIDLAB_REAL_BINANCE_ACCEPTANCE=1 for one fixed official daily object",
)


def test_one_fixed_official_spot_day_is_manifested(tmp_path: Path) -> None:
    """Download exactly BTCUSDT 1m for 2025-01-01; never expands the range."""
    client = OfficialBinanceArchiveClient()
    preview = preview_binance_archive(
        ArchiveRequest(
            "BTCUSDT",
            "1m",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 1, 2, tzinfo=timezone.utc),
        ),
        client,
    )

    assert len(preview.sources) == 1
    assert preview.estimated_bytes <= client.max_archive_bytes
    manifest = acquire_binance_archive(
        preview,
        client,
        tmp_path,
        retrieved_at=datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert manifest["quality"]["rows"] == 1440
    assert manifest["quality"]["gaps"] == 0
    assert manifest["timestamp"]["source_units"] == ["microseconds"]
    assert manifest["sources"][0]["observed_sha256"] == (preview.sources[0].expected_sha256)
