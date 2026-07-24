"""Durable local snapshots of the public Binance EUR research catalog."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from backend import service


DEFAULT_CATALOGS = Path(__file__).resolve().parent.parent / ".studio" / "catalogs"


class StudioCatalogRepository:
    """Persist immutable catalog snapshots and validate operator selections."""

    def __init__(
        self,
        root: Path,
        client: service.BinanceCatalogClient,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = root
        self.client = client
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.snapshots = root / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.latest_path = root / "latest.json"

    @staticmethod
    def _catalog(payload: dict[str, Any]) -> service.EurResearchCatalog:
        sources = tuple(
            service.CatalogSource(
                environment=source["environment"],
                url=source["url"],
                server_time=datetime.fromisoformat(source["server_time"]),
            )
            for source in payload["sources"]
        )
        symbols: list[service.EurCatalogSymbol] = []
        for raw in payload["symbols"]:
            coverage = raw["coverage"]
            liquidity = raw["liquidity"]
            symbols.append(
                service.EurCatalogSymbol(
                    symbol=raw["symbol"],
                    base_asset=raw["base_asset"],
                    quote_asset=raw["quote_asset"],
                    status=raw["status"],
                    exchange_filters=raw["exchange_filters"],
                    coverage=service.ArchiveCoverage(
                        first_date=date.fromisoformat(coverage["first_date"]),
                        last_date=date.fromisoformat(coverage["last_date"]),
                        intervals=tuple(coverage["intervals"]),
                        known_gap_dates=tuple(
                            date.fromisoformat(value)
                            for value in coverage["known_gap_dates"]
                        ),
                        evidence_urls=tuple(coverage["evidence_urls"]),
                    ),
                    liquidity=service.LiquidityEvidence(
                        observed_days=liquidity["observed_days"],
                        observed_start_date=date.fromisoformat(
                            liquidity["observed_start_date"]
                        ),
                        observed_end_date=date.fromisoformat(
                            liquidity["observed_end_date"]
                        ),
                        observed_at=datetime.fromisoformat(liquidity["observed_at"]),
                        kline_source_url=liquidity["kline_source_url"],
                        kline_payload_sha256=liquidity["kline_payload_sha256"],
                        ticker_source_url=liquidity["ticker_source_url"],
                        ticker_payload_sha256=liquidity["ticker_payload_sha256"],
                        median_daily_quote_volume=Decimal(
                            liquidity["median_daily_quote_volume"]
                        ),
                        median_daily_trade_count=Decimal(
                            liquidity["median_daily_trade_count"]
                        ),
                        annualized_realized_volatility=Decimal(
                            liquidity["annualized_realized_volatility"]
                        ),
                        current_spread_bps=Decimal(liquidity["current_spread_bps"]),
                        current_trade_count=liquidity["current_trade_count"],
                    ),
                    liquidity_rank=raw["liquidity_rank"],
                )
            )
        return service.EurResearchCatalog(
            catalog_id=payload["catalog_id"],
            retrieved_at=datetime.fromisoformat(payload["retrieved_at"]),
            quote_asset=payload["quote_asset"],
            filters=tuple(payload["filters"]),
            sources=sources,
            symbols=tuple(symbols),
        )

    @staticmethod
    def _payload(catalog: service.EurResearchCatalog) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            json.loads(json.dumps(asdict(catalog), sort_keys=True, default=str)),
        )

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _validate_identity(catalog_id: str) -> None:
        if len(catalog_id) != 64 or any(
            char not in "0123456789abcdef" for char in catalog_id
        ):
            raise service.CatalogAdmissionError("invalid catalog identity")

    def refresh(self) -> service.EurResearchCatalog:
        catalog = service.discover_eur_catalog(self.client, retrieved_at=self.clock())
        payload = self._payload(catalog)
        snapshot_path = self.snapshots / f"{catalog.catalog_id}.json"
        if snapshot_path.exists():
            existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if existing != payload:
                raise service.CatalogAdmissionError(
                    "catalog snapshot conflicts with its content identity"
                )
        else:
            self._write_json(snapshot_path, payload)
        self._write_json(self.latest_path, {"catalog_id": catalog.catalog_id})
        return catalog

    def get(
        self,
        catalog_id: str | None = None,
        *,
        refresh: bool = False,
    ) -> service.EurResearchCatalog:
        if refresh:
            return self.refresh()
        latest_requested = catalog_id is None
        if catalog_id is None:
            if not self.latest_path.is_file():
                return self.refresh()
            latest = json.loads(self.latest_path.read_text(encoding="utf-8"))
            catalog_id = latest.get("catalog_id")
        if not isinstance(catalog_id, str):
            raise service.CatalogAdmissionError("latest catalog identity is malformed")
        self._validate_identity(catalog_id)
        path = self.snapshots / f"{catalog_id}.json"
        if not path.is_file():
            raise service.CatalogAdmissionError(
                f"catalog snapshot not found: {catalog_id}"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("catalog_id") != catalog_id:
            raise service.CatalogAdmissionError("catalog snapshot identity mismatch")
        try:
            catalog = self._catalog(payload)
        except (KeyError, TypeError, ValueError) as exc:
            if latest_requested:
                return self.refresh()
            raise service.CatalogAdmissionError(
                "catalog snapshot schema is incompatible"
            ) from exc
        if service.catalog_identity(catalog) != catalog_id:
            raise service.CatalogAdmissionError("catalog snapshot identity mismatch")
        return catalog

    def selection(
        self,
        catalog_id: str,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> tuple[service.EurResearchCatalog, service.EurCatalogSymbol]:
        catalog = self.get(catalog_id)
        selected = next(
            (entry for entry in catalog.symbols if entry.symbol == symbol), None
        )
        if selected is None:
            raise service.CatalogAdmissionError(
                f"{symbol} is not admitted by catalog {catalog.catalog_id}"
            )
        last_requested_date = (end - timedelta(microseconds=1)).date()
        if start.date() < selected.coverage.first_date:
            raise service.CatalogAdmissionError(
                f"{symbol} production history begins {selected.coverage.first_date}"
            )
        if last_requested_date > selected.coverage.last_date:
            raise service.CatalogAdmissionError(
                f"{symbol} production history ends {selected.coverage.last_date}"
            )
        requested_dates = {
            start.date() + timedelta(days=offset)
            for offset in range((end.date() - start.date()).days)
        }
        gaps = requested_dates & set(selected.coverage.known_gap_dates)
        if gaps:
            raise service.CatalogAdmissionError(
                f"known archive gap {min(gaps)} for {symbol}"
            )
        return catalog, selected


def studio_catalog_repository() -> StudioCatalogRepository:
    configured = os.environ.get("GRIDLAB_STUDIO_CATALOGS")
    root = Path(configured) if configured else DEFAULT_CATALOGS
    return StudioCatalogRepository(root, service.OfficialBinanceCatalogClient())
