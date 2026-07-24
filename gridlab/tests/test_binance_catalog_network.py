"""Explicitly bounded real-network acceptance for the public EUR catalog."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from gridlab.data.binance_catalog import (
    OfficialBinanceCatalogClient,
    discover_eur_catalog,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("GRIDLAB_REAL_BINANCE_CATALOG") != "1",
    reason="set GRIDLAB_REAL_BINANCE_CATALOG=1 for bounded official catalog acceptance",
)


def test_current_official_eur_catalog_is_reproducibly_admitted() -> None:
    catalog = discover_eur_catalog(
        OfficialBinanceCatalogClient(),
        retrieved_at=datetime.now(timezone.utc),
    )

    assert len(catalog.catalog_id) == 64
    assert len(catalog.symbols) <= 100
    assert all(entry.quote_asset == "EUR" for entry in catalog.symbols)
    assert all(entry.coverage.first_date <= entry.coverage.last_date for entry in catalog.symbols)
    assert all(entry.liquidity.observed_days == 30 for entry in catalog.symbols)
