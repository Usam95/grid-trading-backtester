import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";

import type {
  BinanceEurResearchCatalog,
  CanonicalAdaptivePresentation,
  FrozenProductionPanel,
  OperatorControlsPresentation,
  ProductionArchiveBacktestBody,
  ResearchPort,
  RunBacktestBody,
  SafetyPosturePresentation,
  StudioBacktestRun,
  StudioConfiguration,
  ResearchJob,
  ResearchJobRequest,
} from "./research/port";

type Workspace = "research" | "operations";
type ResearchMode = "production" | "synthetic";

type Draft = {
  symbol: string;
  regime: "range" | "trend" | "random";
  bars: number;
  seed: number;
  initialCash: number;
  lower: number;
  upper: number;
  levels: number;
  spacing: "geometric" | "arithmetic";
  quoteSize: number;
  makerFee: number;
  takerFee: number;
  stopLoss: number;
};

function number(value: number | null | undefined, fallback: number): number {
  return value ?? fallback;
}

function draftFrom(configuration: StudioConfiguration): Draft {
  const spec = configuration.default_spec;
  return {
    symbol: spec.symbol ?? "BTCUSDT",
    regime: spec.data?.regime ?? "range",
    bars: number(spec.data?.n, 300),
    seed: number(spec.data?.seed, 7),
    initialCash: number(spec.initial_cash, 10_000),
    lower: number(spec.grid?.lower, 92),
    upper: number(spec.grid?.upper, 108),
    levels: number(spec.grid?.levels, 12),
    spacing:
      spec.grid?.spacing === "geometric" ? "geometric" : "arithmetic",
    quoteSize: number(spec.sizing?.value, 80),
    makerFee: number(spec.fees?.maker, 0.001),
    takerFee: number(spec.fees?.taker, 0.001),
    stopLoss: number(spec.grid?.stop_loss_frac, 0.12),
  };
}

function requestFrom(draft: Draft): RunBacktestBody {
  return {
    spec: {
      symbol: draft.symbol,
      market_type: "spot",
      initial_cash: draft.initialCash,
      grid: {
        levels: draft.levels,
        lower: draft.lower,
        upper: draft.upper,
        spacing: draft.spacing,
        direction: "neutral",
        adaptive: false,
        stop_loss_frac: draft.stopLoss,
      },
      sizing: { mode: "fixed_quote", value: draft.quoteSize },
      fees: { maker: draft.makerFee, taker: draft.takerFee },
      data: {
        kind: "synthetic",
        n: draft.bars,
        start_price: (draft.lower + draft.upper) / 2,
        seed: draft.seed,
        regime: draft.regime,
      },
      n_trials: 1,
    },
    options: { include_trades: true, with_report: false },
  };
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat("en", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "always",
  }).format(value);
}

function formatMoney(value: number, quoteAsset = "USDT"): string {
  return `${new Intl.NumberFormat("en", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)} ${quoteAsset}`;
}

function formatBytes(value: number): string {
  return `${new Intl.NumberFormat("en-US").format(value)} bytes`;
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatSignedPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function buildRungPrices(draft: Draft): number[] {
  const levels = Math.max(2, Math.floor(draft.levels));
  if (draft.spacing === "geometric" && draft.lower > 0 && draft.upper > 0) {
    const ratio = Math.pow(draft.upper / draft.lower, 1 / (levels - 1));
    return Array.from({ length: levels }, (_, index) => draft.lower * Math.pow(ratio, index));
  }
  const step = (draft.upper - draft.lower) / (levels - 1);
  return Array.from({ length: levels }, (_, index) => draft.lower + step * index);
}

function utcDay(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function inclusiveEndDay(exclusiveIso: string): string {
  const end = new Date(exclusiveIso);
  end.setUTCDate(end.getUTCDate() - 1);
  return end.toISOString().slice(0, 10);
}

function formatUtcDateTime(iso: string): string {
  const value = new Date(iso);
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(value);
  const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${lookup.day} ${lookup.month} ${lookup.year}, ${lookup.hour}:${lookup.minute} UTC`;
}

function rangeDays(startIso: string, endIso: string): number {
  return Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 86_400_000);
}

function rangeLabel(range: { start: string; end: string }): string {
  return `${formatUtcDateTime(range.start)} → ${formatUtcDateTime(range.end)}`;
}

function rangeChipLabel(range: { start: string; end: string }): string {
  return `${utcDay(range.start)} → ${inclusiveEndDay(range.end)} · ${rangeDays(range.start, range.end)} days`;
}

function anchorDraftToReplayStart(
  draft: Draft,
  replayStartPrice: number,
): Draft {
  if (!Number.isFinite(replayStartPrice) || replayStartPrice <= 0) {
    return draft;
  }
  const currentCenter = (draft.lower + draft.upper) / 2;
  const safeCenter = currentCenter > 0 ? currentCenter : replayStartPrice;
  const lowerOffset = safeCenter > 0
    ? Math.max(0, (safeCenter - draft.lower) / safeCenter)
    : 0.08;
  const upperOffset = safeCenter > 0
    ? Math.max(0, (draft.upper - safeCenter) / safeCenter)
    : 0.08;
  return {
    ...draft,
    lower: Number((replayStartPrice * (1 - lowerOffset)).toFixed(8)),
    upper: Number((replayStartPrice * (1 + upperOffset)).toFixed(8)),
  };
}

function isMidnightUtc(iso: string): boolean {
  const value = new Date(iso);
  return value.getUTCHours() === 0 && value.getUTCMinutes() === 0 && value.getUTCSeconds() === 0;
}

function friendlyRangeExplanation(range: { start: string; end: string }): string {
  if (isMidnightUtc(range.start) && isMidnightUtc(range.end)) {
    return "This range starts and ends on clean UTC day boundaries, so it behaves like a normal date window.";
  }
  return "This range begins or ends mid-day because the first or last verified candle we actually hold does not line up with midnight UTC.";
}

function NumberField({
  label,
  value,
  onChange,
  min,
  step = 1,
}: {
  label: string;
  value: number;
  onChange(value: number): void;
  min?: number;
  step?: number;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        value={value}
        min={min}
        step={step}
        onChange={(event) => onChange(event.currentTarget.valueAsNumber)}
      />
    </label>
  );
}

function ExpandableInfo({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details className="expandable-info" open={defaultOpen}>
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  );
}

function ModeSelector({
  mode,
  onChange,
}: {
  mode: ResearchMode;
  onChange(mode: ResearchMode): void;
}) {
  return (
    <section className="mode-selector" aria-label="Backtest mode">
      <button
        type="button"
        className={mode === "production" ? "mode-card selected" : "mode-card"}
        onClick={() => onChange("production")}
      >
        <div className="mode-card-top">
          <span className="mode-badge">Production replay</span>
          <span className="mode-status">{mode === "production" ? "Selected" : "Available"}</span>
        </div>
        <strong>Use locally verified EUR history</strong>
        <p>Pick a real symbol and verified range, then run the strategy on stored production candles.</p>
      </button>
      <button
        type="button"
        className={mode === "synthetic" ? "mode-card selected" : "mode-card"}
        onClick={() => onChange("synthetic")}
      >
        <div className="mode-card-top">
          <span className="mode-badge">Synthetic sandbox</span>
          <span className="mode-status">{mode === "synthetic" ? "Selected" : "Available"}</span>
        </div>
        <strong>Experiment quickly with synthetic data</strong>
        <p>Try parameter ideas fast before spending time on a reality-anchored replay.</p>
      </button>
    </section>
  );
}

function StrategyFields({
  configuration,
  draft,
  update,
}: {
  configuration: StudioConfiguration;
  draft: Draft;
  update: <K extends keyof Draft>(key: K, value: Draft[K]) => void;
}) {
  return (
    <div className="sections cleaner">
      <fieldset>
        <legend><b>01</b> Market & scenario</legend>
        <label>Symbol<input aria-label="Symbol" value={draft.symbol} onChange={(e) => update("symbol", e.currentTarget.value.toUpperCase())} /></label>
        <label>Scenario<select value={draft.regime} onChange={(e) => update("regime", e.currentTarget.value as Draft["regime"])}>{configuration.data_regimes.map((item) => <option key={item}>{item}</option>)}</select></label>
        <NumberField label="Synthetic bars" min={50} value={draft.bars} onChange={(v) => update("bars", v)} />
        <NumberField label="Deterministic seed" value={draft.seed} onChange={(v) => update("seed", v)} />
      </fieldset>
      <fieldset>
        <legend><b>02</b> Grid setup</legend>
        <NumberField label="Initial quote capital" min={1} value={draft.initialCash} onChange={(v) => update("initialCash", v)} />
        <NumberField label="Lower bound" min={0.01} step={0.01} value={draft.lower} onChange={(v) => update("lower", v)} />
        <NumberField label="Upper bound" min={0.01} step={0.01} value={draft.upper} onChange={(v) => update("upper", v)} />
        <NumberField label="Configured rung prices" min={2} value={draft.levels} onChange={(v) => update("levels", v)} />
        <label>Spacing<select value={draft.spacing} onChange={(e) => update("spacing", e.currentTarget.value as Draft["spacing"])}>{configuration.spacing.map((item) => <option key={item}>{item}</option>)}</select></label>
        <NumberField label="Fixed quote per order" min={0.01} step={0.01} value={draft.quoteSize} onChange={(v) => update("quoteSize", v)} />
      </fieldset>
      <fieldset>
        <legend><b>03</b> Costs</legend>
        <NumberField label="Maker fee fraction" min={0} step={0.0001} value={draft.makerFee} onChange={(v) => update("makerFee", v)} />
        <NumberField label="Taker fee fraction" min={0} step={0.0001} value={draft.takerFee} onChange={(v) => update("takerFee", v)} />
        <p className="note">The backend applies costs and execution semantics. This view still uses simulated candle execution, not live venue evidence.</p>
      </fieldset>
      <fieldset>
        <legend><b>04</b> Safety limits</legend>
        <NumberField label="Global stop-loss fraction" min={0} step={0.01} value={draft.stopLoss} onChange={(v) => update("stopLoss", v)} />
        <p className="note">Static neutral Spot only. No leverage, shorting, adaptive range shifts, compounding, or live activation is available here.</p>
      </fieldset>
    </div>
  );
}

function ProductionSetupGuidance({
  draft,
  selected,
  selectedCatalogSymbol,
  selectedRange,
  catalogRetrievedAt,
}: {
  draft: Draft;
  selected?: FrozenProductionPanel["datasets"][number];
  selectedCatalogSymbol?: BinanceEurResearchCatalog["symbols"][number];
  selectedRange?: FrozenProductionPanel["datasets"][number]["verified_ranges"][number];
  catalogRetrievedAt?: string;
}) {
  const centerPrice = (draft.lower + draft.upper) / 2;
  const replayStartPrice = selectedRange ? Number(selectedRange.start_open_price) : null;
  const replayEndPrice = selectedRange ? Number(selectedRange.end_close_price) : null;
  const centerVsReplayStart = replayStartPrice && replayStartPrice > 0
    ? ((centerPrice - replayStartPrice) / replayStartPrice) * 100
    : null;
  const lowerDistance = centerPrice > 0 ? ((draft.lower - centerPrice) / centerPrice) * 100 : 0;
  const upperDistance = centerPrice > 0 ? ((draft.upper - centerPrice) / centerPrice) * 100 : 0;
  const rangeWidth = centerPrice > 0 ? ((draft.upper - draft.lower) / centerPrice) * 100 : 0;
  const rungPrices = buildRungPrices(draft);
  const lowest = Math.min(...rungPrices);
  const highest = Math.max(...rungPrices);

  return (
    <section className="setup-guidance" aria-labelledby="setup-guidance-heading">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Backtest setup context</p>
          <h3 id="setup-guidance-heading">Configure the grid with market context</h3>
          <p className="section-copy">
            This panel now shows the actual replay-start price from the selected verified local range, so you can anchor the grid to the market level that the backtest will really begin from.
          </p>
        </div>
      </div>

      <div className="summary-grid setup-guidance-grid">
        <article>
          <span>Replay-start price</span>
          <strong>{replayStartPrice !== null ? `${replayStartPrice.toFixed(2)} EUR` : "Unavailable"}</strong>
        </article>
        <article>
          <span>Replay-end close</span>
          <strong>{replayEndPrice !== null ? `${replayEndPrice.toFixed(2)} EUR` : "Unavailable"}</strong>
        </article>
        <article>
          <span>Configured grid center</span>
          <strong>{centerPrice.toFixed(2)} EUR</strong>
        </article>
        <article>
          <span>Center vs replay start</span>
          <strong>{centerVsReplayStart !== null ? formatSignedPercent(centerVsReplayStart) : "Unavailable"}</strong>
        </article>
      </div>

      <div className="summary-grid setup-guidance-grid secondary">
        <article>
          <span>Configured width</span>
          <strong>{rangeWidth.toFixed(2)}%</strong>
        </article>
        <article>
          <span>Lower vs center</span>
          <strong>{formatSignedPercent(lowerDistance)}</strong>
        </article>
        <article>
          <span>Upper vs center</span>
          <strong>{formatSignedPercent(upperDistance)}</strong>
        </article>
        <article>
          <span>Starting candle</span>
          <strong>{selectedRange ? formatUtcDateTime(selectedRange.start) : "Unavailable"}</strong>
        </article>
      </div>

      <div className="ladder-preview-card">
        <div className="ladder-preview-copy">
          <span>Mini ladder preview</span>
          <strong>{draft.levels} configured rung prices · {draft.spacing} spacing</strong>
          <p>
            This is a simple visual preview of where the ladder lands between your lower and upper bounds. The highlighted marker is your configured grid center, while the replay-start price above tells you where the selected backtest window actually begins.
          </p>
        </div>
        <div className="ladder-rail" aria-label="Grid rung preview">
          <div
            className="ladder-center-marker"
            style={{ left: `${clamp(((centerPrice - lowest) / Math.max(highest - lowest, 0.000001)) * 100, 0, 100)}%` }}
          >
            <span>Center {centerPrice.toFixed(2)}</span>
          </div>
          {rungPrices.map((price, index) => {
            const position = clamp(((price - lowest) / Math.max(highest - lowest, 0.000001)) * 100, 0, 100);
            const side = price <= centerPrice ? "Buy side" : "Sell side";
            return (
              <div
                key={`${price}-${index}`}
                className={price <= centerPrice ? "rung-dot buy" : "rung-dot sell"}
                style={{ left: `${position}%` }}
                title={`Rung ${index + 1}: ${price.toFixed(2)} EUR · ${side}`}
              >
                <span>{index + 1}</span>
              </div>
            );
          })}
        </div>
        <div className="ladder-scale">
          <span>Lower {draft.lower.toFixed(2)}</span>
          <span>Upper {draft.upper.toFixed(2)}</span>
        </div>
      </div>

      <div className="rung-chip-list" aria-label="Rung price list">
        {rungPrices.map((price, index) => (
          <span key={`chip-${price}-${index}`} className={price <= centerPrice ? "rung-chip buy" : "rung-chip sell"}>
            {index + 1}: {price.toFixed(2)}
          </span>
        ))}
      </div>

      <div className="selected-range-card">
        <div>
          <span>Replay window</span>
          <strong>{selectedRange ? `${rangeDays(selectedRange.start, selectedRange.end)} days` : "Not selected"}</strong>
          <p>{selectedRange ? rangeLabel(selectedRange) : "Choose a verified range to see the exact replay window."}</p>
        </div>
        <div>
          <span>Market quality</span>
          <strong>{selectedCatalogSymbol ? `#${selectedCatalogSymbol.liquidity_rank} official liquidity rank` : "Waiting for symbol"}</strong>
          <p>
            {selectedCatalogSymbol
              ? `${formatCompactNumber(Number(selectedCatalogSymbol.liquidity.median_daily_quote_volume))} EUR median daily volume · ${selectedCatalogSymbol.liquidity.current_spread_bps} bps spread snapshot.`
              : "Select a symbol to inspect its stored production history."}
          </p>
        </div>
        <div>
          <span>Why this helps</span>
          <strong>Bounds should be intentional</strong>
          <p>Use the center and percentage offsets to see whether your lower and upper bounds are narrow, balanced, or far away before running the backtest.</p>
        </div>
      </div>

      {selected?.symbol && (
        <div className="symbol-detail-grid setup-detail-grid">
          <article>
            <span>Archive availability</span>
            <strong>{selected.coverage.first_date} → {selected.coverage.last_date}</strong>
          </article>
          <article>
            <span>Active partitions</span>
            <strong>{selected.partitions.filter((item) => item.active).length}</strong>
          </article>
          <article>
            <span>Stored locally</span>
            <strong>{formatBytes(selected.stored_bytes)}</strong>
          </article>
          <article>
            <span>Catalog snapshot</span>
            <strong>{catalogRetrievedAt ? formatUtcDateTime(catalogRetrievedAt) : "Unavailable"}</strong>
          </article>
        </div>
      )}
    </section>
  );
}

function Navigation({ workspace }: { workspace: Workspace }) {
  return (
    <nav aria-label="Studio" className="nav-groups">
      <section aria-labelledby="research-nav">
        <h2 id="research-nav">Research</h2>
        {["Overview", "Experiments", "Candidates", "Data", "Learn"].map((item) => (
          <a
            className={workspace === "research" && item === "Experiments" ? "active" : ""}
            href={`#/research/${item.toLowerCase()}`}
            key={item}
          >
            {item}
          </a>
        ))}
      </section>
      <section aria-labelledby="operations-nav">
        <h2 id="operations-nav">Operations</h2>
        {["Command Center", "Qualification", "Reconciliation", "Incidents", "Evidence & Audit"].map((item) => (
          <a
            className={workspace === "operations" && item === "Command Center" ? "active" : ""}
            href={`#/operations/${item.toLowerCase().replaceAll(" ", "-")}`}
            key={item}
          >
            {item}
          </a>
        ))}
      </section>
      <a className="legacy-link" href="/">Open legacy Studio</a>
    </nav>
  );
}

function AuthorityHeader({ workspace }: { workspace: Workspace }) {
  if (workspace === "operations") {
    return (
      <header className="authority operations">
        <div><strong>OPERATIONS</strong><span>NO ENVIRONMENT SELECTED</span><span>GATEWAY NOT CONFIGURED</span></div>
        <div><span>VIEW DISCONNECTED</span><strong>COMMAND AUTHORITY UNAVAILABLE</strong></div>
      </header>
    );
  }
  return (
    <header className="authority research">
      <div><strong>RESEARCH</strong><span>LOCAL</span><span>Typed Studio · FastAPI</span></div>
      <div><span>LOCAL SERVICE</span><strong>NO ONLINE TRADING AUTHORITY</strong></div>
    </header>
  );
}

type SubmittedSpecification = {
  initial_cash?: number;
  grid?: {
    lower?: number;
    upper?: number;
    levels?: number;
    spacing?: string;
  };
  sizing?: {
    value?: number;
  };
};

type ReplaySeries = {
  x?: number[];
  timestamps?: string[];
  price?: number[];
};

type ReplayTrade = {
  side?: string;
  entry_price?: number;
  exit_price?: number;
  opened_at?: string;
  closed_at?: string;
  entry_x?: number;
  exit_x?: number;
  pnl?: number;
};

type ReplayGrid = {
  lower?: number;
  upper?: number;
  center?: number;
  levels?: number[];
};

function formatChartPrice(value: number, quoteAsset: string): string {
  const digits = value >= 1000 ? 0 : value >= 100 ? 2 : value >= 1 ? 3 : 5;
  return `${value.toFixed(digits)} ${quoteAsset}`;
}

function ReplayVisualization({ run }: { run: StudioBacktestRun }) {
  const result = run.result as { series?: ReplaySeries; trades?: ReplayTrade[]; grid?: ReplayGrid };
  const series = result.series;
  const trades = Array.isArray(result.trades) ? result.trades : [];
  const grid = result.grid;
  const quoteAsset = run.provenance?.quote_asset ?? "USDT";
  const xValues = Array.isArray(series?.x) ? series.x.filter((value) => Number.isFinite(value)) : [];
  const timestamps = Array.isArray(series?.timestamps) ? series.timestamps : [];
  const prices = Array.isArray(series?.price) ? series.price.filter((value) => Number.isFinite(value)) : [];
  const gridLevels = Array.isArray(grid?.levels) ? grid.levels.filter((value) => Number.isFinite(value)) : [];
  if (prices.length < 2 || xValues.length !== prices.length) {
    return null;
  }

  const minVisiblePoints = Math.min(prices.length, Math.max(2, Math.min(24, Math.ceil(prices.length * 0.5))));
  const [viewport, setViewport] = useState(() => ({
    startIndex: 0,
    endIndex: prices.length - 1,
  }));
  const dragState = useRef<{ pointerX: number; startIndex: number; endIndex: number } | null>(null);

  useEffect(() => {
    setViewport({
      startIndex: 0,
      endIndex: prices.length - 1,
    });
  }, [run.id, prices.length]);

  const boundedViewport = useMemo(() => {
    const fullStartIndex = 0;
    const fullEndIndex = prices.length - 1;
    const requestedCount = Math.max(
      minVisiblePoints,
      Math.min(prices.length, viewport.endIndex - viewport.startIndex + 1),
    );
    let startIndex = clamp(
      Math.round(viewport.startIndex),
      fullStartIndex,
      Math.max(fullStartIndex, prices.length - requestedCount),
    );
    let endIndex = startIndex + requestedCount - 1;
    if (endIndex > fullEndIndex) {
      endIndex = fullEndIndex;
      startIndex = Math.max(fullStartIndex, endIndex - requestedCount + 1);
    }
    return { startIndex, endIndex, fullStartIndex, fullEndIndex, visibleCount: requestedCount };
  }, [minVisiblePoints, prices.length, viewport.endIndex, viewport.startIndex]);

  const visibleIndices = Array.from(
    { length: boundedViewport.endIndex - boundedViewport.startIndex + 1 },
    (_, offset) => boundedViewport.startIndex + offset,
  );
  const visibleX = visibleIndices.map((index) => xValues[index]);
  const visiblePrices = visibleIndices.map((index) => prices[index]);
  const visibleTimestamps = visibleIndices.map((index) => timestamps[index]);
  const visibleXMin = visibleX[0];
  const visibleXMax = visibleX[visibleX.length - 1];
  const visibleTrades = trades.filter((trade) => {
    const entry = typeof trade.entry_x === "number" ? trade.entry_x : null;
    const exit = typeof trade.exit_x === "number" ? trade.exit_x : null;
    return (entry !== null && entry >= visibleXMin && entry <= visibleXMax)
      || (exit !== null && exit >= visibleXMin && exit <= visibleXMax);
  });
  const tradePrices = visibleTrades.flatMap((trade) => [trade.entry_price, trade.exit_price]).filter(
    (value): value is number => typeof value === "number" && Number.isFinite(value),
  );

  const width = 920;
  const height = 320;
  const padding = { top: 18, right: 18, bottom: 34, left: 56 };
  const domainXMin = visibleX[0];
  const domainXMax = visibleX[visibleX.length - 1];
  const domainPrices = [...visiblePrices, ...gridLevels, ...tradePrices];
  const minPrice = Math.min(...domainPrices);
  const maxPrice = Math.max(...domainPrices);
  const paddedRange = Math.max((maxPrice - minPrice) * 0.08, maxPrice * 0.02, 0.00001);
  const domainYMin = minPrice - paddedRange;
  const domainYMax = maxPrice + paddedRange;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const xAt = (value: number) => {
    if (domainXMax === domainXMin) return padding.left + plotWidth / 2;
    return padding.left + ((value - domainXMin) / (domainXMax - domainXMin)) * plotWidth;
  };
  const yAt = (value: number) => {
    if (domainYMax === domainYMin) return padding.top + plotHeight / 2;
    return padding.top + ((domainYMax - value) / (domainYMax - domainYMin)) * plotHeight;
  };
  const pricePath = visiblePrices.map((value, index) => `${index === 0 ? "M" : "L"} ${xAt(visibleX[index]).toFixed(2)} ${yAt(value).toFixed(2)}`).join(" ");
  const firstTimestamp = visibleTimestamps[0];
  const lastTimestamp = visibleTimestamps[visibleTimestamps.length - 1];
  const canZoomIn = boundedViewport.visibleCount > minVisiblePoints;
  const canZoomOut = boundedViewport.visibleCount < prices.length;

  function setViewportByCenter(nextCount: number, centerIndex: number) {
    const visibleCount = Math.max(minVisiblePoints, Math.min(prices.length, Math.round(nextCount)));
    const halfSpan = (visibleCount - 1) / 2;
    let startIndex = Math.round(centerIndex - halfSpan);
    let endIndex = startIndex + visibleCount - 1;
    if (startIndex < 0) {
      startIndex = 0;
      endIndex = visibleCount - 1;
    }
    if (endIndex > prices.length - 1) {
      endIndex = prices.length - 1;
      startIndex = Math.max(0, endIndex - visibleCount + 1);
    }
    setViewport({ startIndex, endIndex });
  }

  function zoom(factor: number) {
    const currentCount = boundedViewport.visibleCount;
    const centerIndex = boundedViewport.startIndex + (currentCount - 1) / 2;
    const nextCount = factor < 1
      ? Math.floor(currentCount * factor)
      : Math.ceil(currentCount * factor);
    setViewportByCenter(nextCount, centerIndex);
  }

  function resetViewport() {
    setViewport({
      startIndex: 0,
      endIndex: prices.length - 1,
    });
  }

  function handleWheel(event: React.WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const relative = clamp((event.clientX - rect.left - padding.left) / plotWidth, 0, 1);
    const factor = event.deltaY > 0 ? 1.25 : 0.8;
    const anchorIndex = boundedViewport.startIndex + relative * Math.max(1, boundedViewport.visibleCount - 1);
    const nextCount = factor < 1
      ? Math.floor(boundedViewport.visibleCount * factor)
      : Math.ceil(boundedViewport.visibleCount * factor);
    setViewportByCenter(nextCount, anchorIndex);
  }

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragState.current = {
      pointerX: event.clientX,
      startIndex: boundedViewport.startIndex,
      endIndex: boundedViewport.endIndex,
    };
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    if (!dragState.current) return;
    const deltaPixels = event.clientX - dragState.current.pointerX;
    const currentCount = dragState.current.endIndex - dragState.current.startIndex + 1;
    const deltaIndex = Math.round((deltaPixels / plotWidth) * Math.max(1, currentCount - 1));
    setViewport({
      startIndex: dragState.current.startIndex - deltaIndex,
      endIndex: dragState.current.endIndex - deltaIndex,
    });
  }

  function handlePointerUp(event: React.PointerEvent<SVGSVGElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragState.current = null;
  }

  return (
    <section className="replay-visualization" aria-labelledby="replay-visualization-heading">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Replay visualization</p>
          <h3 id="replay-visualization-heading">Price path, grid, and executed trades</h3>
          <p className="section-copy">
            The yellow line shows the replayed market price, horizontal lines show the configured grid ladder, and trade markers show where the backtest actually entered and exited.
          </p>
        </div>
      </div>

      <div className="chart-legend">
        <span><i className="legend-swatch price" />Replay price path</span>
        <span><i className="legend-swatch grid" />Grid levels</span>
        <span><i className="legend-swatch buy" />Buy entries</span>
        <span><i className="legend-swatch sell" />Sell exits</span>
      </div>

      <div className="chart-toolbar">
        <div className="chart-toolbar-group">
          <button type="button" onClick={() => zoom(0.8)} disabled={!canZoomIn} aria-label="Zoom in replay chart">Zoom in</button>
          <button type="button" onClick={() => zoom(1.25)} disabled={!canZoomOut} aria-label="Zoom out replay chart">Zoom out</button>
          <button type="button" onClick={resetViewport} disabled={!canZoomOut} aria-label="Reset replay chart zoom">Reset</button>
        </div>
        <span className="chart-viewport-label">
          Visible points: {visiblePrices.length.toLocaleString("en-US")} / {prices.length.toLocaleString("en-US")} · Drag to pan · Wheel to zoom
        </span>
      </div>

      <svg
        className="replay-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Replay price path with grid levels and executed trades"
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        <defs>
          <linearGradient id="priceGlow" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#f0b90b" stopOpacity="0.65" />
            <stop offset="100%" stopColor="#fcd535" stopOpacity="1" />
          </linearGradient>
        </defs>

        <rect x="0" y="0" width={width} height={height} rx="18" className="chart-bg" />

        {[domainYMin, grid?.lower, grid?.center, grid?.upper, domainYMax]
          .filter((value): value is number => typeof value === "number" && Number.isFinite(value))
          .map((value, index) => (
            <g key={`axis-${index}`}>
              <line x1={padding.left} x2={width - padding.right} y1={yAt(value)} y2={yAt(value)} className="chart-axis-line" />
              <text x={14} y={yAt(value) + 4} className="chart-axis-label">{formatChartPrice(value, quoteAsset)}</text>
            </g>
          ))}

        {gridLevels.map((level, index) => (
          <line
            key={`grid-${index}`}
            x1={padding.left}
            x2={width - padding.right}
            y1={yAt(level)}
            y2={yAt(level)}
            className={Math.abs(level - (grid?.center ?? Number.NaN)) < 1e-9 ? "chart-grid-line center" : "chart-grid-line"}
          />
        ))}

        <path d={pricePath} className="chart-price-path" />

        {visibleTrades.flatMap((trade, index) => {
          const entryX = typeof trade.entry_x === "number" ? xAt(trade.entry_x) : null;
          const entryY = typeof trade.entry_price === "number" ? yAt(trade.entry_price) : null;
          const exitX = typeof trade.exit_x === "number" ? xAt(trade.exit_x) : null;
          const exitY = typeof trade.exit_price === "number" ? yAt(trade.exit_price) : null;
          return [
            entryX !== null && entryY !== null
              ? <g key={`entry-${index}`}>
                <circle cx={entryX} cy={entryY} r="5" className="chart-trade-entry" />
                <title>{`Buy ${trade.entry_price?.toFixed(5)} ${quoteAsset} · ${trade.opened_at ?? "unknown time"}`}</title>
              </g>
              : null,
            exitX !== null && exitY !== null
              ? <g key={`exit-${index}`}>
                <rect x={exitX - 4.5} y={exitY - 4.5} width="9" height="9" rx="2" className="chart-trade-exit" />
                <title>{`Sell ${trade.exit_price?.toFixed(5)} ${quoteAsset} · ${trade.closed_at ?? "unknown time"}`}</title>
              </g>
              : null,
          ];
        })}

        {firstTimestamp && <text x={padding.left} y={height - 10} className="chart-time-label">{formatUtcDateTime(firstTimestamp)}</text>}
        {lastTimestamp && <text x={width - padding.right} y={height - 10} textAnchor="end" className="chart-time-label">{formatUtcDateTime(lastTimestamp)}</text>}
      </svg>

      <div className="summary-grid">
        <article><span>Grid range</span><strong>{grid?.lower !== undefined && grid?.upper !== undefined ? `${formatChartPrice(grid.lower, quoteAsset)} → ${formatChartPrice(grid.upper, quoteAsset)}` : "Unavailable"}</strong></article>
        <article><span>Replay points drawn</span><strong>{prices.length.toLocaleString("en-US")}</strong></article>
        <article><span>Trades marked</span><strong>{visibleTrades.length.toLocaleString("en-US")}</strong></article>
        <article><span>Current replay verdict</span><strong>{run.primary_result.verdict}</strong></article>
      </div>
    </section>
  );
}

function Results({ run }: { run: StudioBacktestRun }) {
  const result = run.primary_result;
  const quoteAsset = run.provenance?.quote_asset ?? "USDT";
  const specification = run.specification as SubmittedSpecification;
  const submittedLower = specification.grid?.lower;
  const submittedUpper = specification.grid?.upper;
  const submittedLevels = specification.grid?.levels;
  const submittedSpacing = specification.grid?.spacing;
  const submittedQuoteSize = specification.sizing?.value;
  const submittedInitialCash = specification.initial_cash;
  const submittedCenter = submittedLower !== undefined && submittedUpper !== undefined
    ? (submittedLower + submittedUpper) / 2
    : null;
  const zeroTradeRun = result.completed_trades === 0;

  return (
    <section className="results" aria-live="polite">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Completed research run</p>
          <h2>{run.result.symbol} result</h2>
          <p className="section-copy">
            {run.provenance
              ? "This run replayed locally verified production candles."
              : "This run used the synthetic research sandbox and conservative candle execution assumptions."}
          </p>
        </div>
        <span className="verdict">{result.verdict}</span>
      </div>
      <div className="metrics">
        <article className="primary"><span>Net return</span><strong>{formatPercent(result.net_return)}</strong></article>
        <article><span>Final equity</span><strong>{formatMoney(result.final_equity, quoteAsset)}</strong></article>
        <article><span>Max drawdown</span><strong>{formatPercent(result.max_drawdown)}</strong></article>
        <article><span>Completed trades</span><strong>{result.completed_trades}</strong></article>
        <article><span>Fees paid</span><strong>{formatMoney(result.fees_paid, quoteAsset)}</strong></article>
      </div>
      <div className="record">
        <span>Authoritative local record</span>
        <code>{run.id}</code>
        <span>Saved by the research service · {new Date(run.created_at).toLocaleString()}</span>
      </div>
      {(submittedLower !== undefined || submittedUpper !== undefined || submittedQuoteSize !== undefined) && (
        <div className="focus-summary">
          <div>
            <strong>Submitted bounds</strong>
            <span>{submittedLower?.toFixed(2) ?? "—"} → {submittedUpper?.toFixed(2) ?? "—"} {quoteAsset}</span>
          </div>
          <div>
            <strong>Submitted grid center</strong>
            <span>{submittedCenter !== null ? `${submittedCenter.toFixed(2)} ${quoteAsset}` : "Unavailable"}</span>
          </div>
          <div>
            <strong>Submitted ladder</strong>
            <span>{submittedLevels ?? "—"} rung prices · {submittedSpacing ?? "—"} spacing</span>
          </div>
          <div>
            <strong>Submitted order sizing</strong>
            <span>{submittedQuoteSize !== undefined ? formatMoney(submittedQuoteSize, quoteAsset) : "Unavailable"} per order · {submittedInitialCash !== undefined ? formatMoney(submittedInitialCash, quoteAsset) : "—"} starting cash</span>
          </div>
        </div>
      )}
      <ReplayVisualization run={run} />
      {zeroTradeRun && (
        <div className="production-provenance zero-trade-callout">
          <div>
            <strong>NO ORDER FILLS WERE RECORDED</strong>
            <span>This submitted grid never executed a fill during the selected replay window, so the backtest stayed fully in cash.</span>
          </div>
          <div>
            <strong>WHAT THE ZERO RESULT MEANS</strong>
            <span>0 completed trades and 0 fees means no admitted buy or sell order was executed. Final equity therefore stayed at the starting cash balance.</span>
          </div>
          <div>
            <strong>WHAT TO TRY NEXT</strong>
            <span>Move the bounds closer to the market you want to replay, narrow the range, or use fewer/wider-spaced rungs so the stored candles are more likely to touch active orders.</span>
          </div>
        </div>
      )}
      {run.provenance ? (
        <>
          <div className="summary-grid">
            <article><span>History source</span><strong>Official Binance Spot archive</strong></article>
            <article><span>Symbol</span><strong>{run.provenance.symbol}</strong></article>
            <article><span>Verified candles</span><strong>{run.provenance.candle_count.toLocaleString("en-US")}</strong></article>
            <article><span>Selected range</span><strong>{rangeDays(run.provenance.requested_start, run.provenance.requested_end)} days</strong></article>
          </div>
          <ExpandableInfo title="Show technical provenance">
            <div className="production-provenance">
              <div><strong>PRODUCTION HISTORY</strong><span>Official Binance Spot archive</span></div>
              <div><strong>TESTNET HISTORY NOT USED</strong><span>Testnet is not profitability evidence</span></div>
              <div><strong>{run.provenance.symbol}</strong><span>{rangeLabel({ start: run.provenance.requested_start, end: run.provenance.requested_end })} · {run.provenance.candle_count.toLocaleString("en-US")} candles</span></div>
              <div><strong>Coverage</strong><span>{new Date(run.provenance.coverage.first_verified_open_time).toISOString()} → {new Date(run.provenance.coverage.last_verified_open_time).toISOString()}</span></div>
              {run.provenance.catalog_identity && <><span>Catalog identity</span><code>{run.provenance.catalog_identity}</code></>}
              <span>Dataset identity</span><code>{run.provenance.dataset_id}</code>
              <span>Manifest identity</span><code>{run.provenance.manifest_identity}</code>
              <span>Partition identities</span><code>{run.provenance.partition_identities.join(", ")}</code>
              <span>Deterministic backtest fingerprint</span><code>{run.provenance.backtest_fingerprint}</code>
            </div>
          </ExpandableInfo>
        </>
      ) : (
        <ExpandableInfo title="Show simulation caveats">
          <div className="production-provenance">
            <div><strong>CANDLE SIMULATION ONLY</strong><span>{run.result.simulation?.canonical_core ? "Canonical adaptive core" : "Research candle harness"}</span></div>
            <div><strong>NOT VENUE EXECUTION PROOF</strong><span>{run.result.simulation?.limitations?.[0] ?? "Candle fills remain conservative assumptions."}</span></div>
          </div>
        </ExpandableInfo>
      )}
    </section>
  );
}

function ResearchJobCard({ job, onCancel }: { job: ResearchJob; onCancel(): void }) {
  const [selected, setSelected] = useState<string>();
  const result = job.result;
  const event = result?.visualization.overlays.find((item) => item.event_id === selected);
  return <section className="research-job" aria-labelledby="research-job-heading">
    <div className="result-heading"><div><p className="eyebrow">Durable adaptive research job</p><h2 id="research-job-heading">{job.status} · {job.phase}</h2></div><span className="scope">{job.progress}%</span></div>
    <div className="job-progress"><div style={{ width: `${job.progress}%` }} /></div>
    <div className="production-provenance"><span>Job identity</span><code>{job.identity.job}</code><span>Dataset</span><code>{job.identity.dataset}</code><span>Code · schema · seed</span><code>{job.identity.code} · {job.identity.schema} · {job.identity.seed}</code></div>
    {job.error && <p className="error" role="alert">{job.error} · prior checkpoints remain available for resume.</p>}
    {result && <>
      <div className="metrics"><article className="primary"><span>Net return</span><strong>{formatPercent(result.net_return)}</strong></article><article><span>Completed cycles</span><strong>{result.completed_cycles}</strong></article><article><span>Max drawdown</span><strong>{formatPercent(result.max_drawdown)}</strong></article><article><span>Fees</span><strong>{formatMoney(result.fees_paid)}</strong></article></div>
      <p className="job-note"><strong>Inventory meaning:</strong> {result.inventory_basis}. <strong>Capital boundary:</strong> {result.capital_note}</p>
      <div className="job-gates" aria-label="Non-compensating research gates">{result.gates.map((gate) => <div key={gate.name} className={gate.outcome === "PASSED" ? "gate-pass" : "gate-fail"}><strong>{gate.outcome}</strong><span>{gate.name} · {gate.reason}</span></div>)}</div>
      <div className="job-visualization"><div><strong>Price and causal overlays</strong><span>Past-only adaptation, epoch, transition, fill, cycle, and safety evidence</span></div><div className="job-events">{result.visualization.overlays.map((item) => <button type="button" key={item.event_id} className={item.event_id === selected ? "selected" : ""} onClick={() => setSelected(item.event_id)}><strong>{item.kind}</strong><span>{item.label}</span></button>)}</div>{event && <div className="causal-detail"><strong>Selected evidence · {event.kind}</strong><span>{event.label}</span><code>{event.event_id}</code><span>Causal inputs: {(event.causal_event_ids ?? []).join(", ") || "none"}</span></div>}</div>
    </>}
    {!['COMPLETED', 'CANCELLED'].includes(job.status) && <button type="button" onClick={onCancel}>Cancel and preserve checkpoint</button>}
  </section>;
}

function CanonicalAdaptiveCard({
  presentation,
}: {
  presentation: CanonicalAdaptivePresentation;
}) {
  const plan = presentation.derived_plan;
  const blockedGates = presentation.activation.gates.filter((gate) => gate.outcome !== "PASSED");

  return (
    <section className="insight-card" aria-labelledby="adaptive-seam-heading">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Decision insight</p>
          <h2 id="adaptive-seam-heading">Why this starting grid was suggested</h2>
          <p className="section-copy">
            This card explains the current adaptive read in plain language. It does not place orders; it only explains the configuration the canonical seam would accept.
          </p>
        </div>
        <span className="scope">{presentation.activation.lifecycle}</span>
      </div>
      <div className="summary-grid">
        <article><span>Current mode</span><strong>{presentation.decision.adaptation_state}</strong></article>
        <article><span>Intent</span><strong>{presentation.decision.intent}</strong></article>
        <article><span>Reason</span><strong>{presentation.decision.reason}</strong></article>
        <article><span>Bootstrap</span><strong>{presentation.activation.ladder_placement_allowed ? "Ready" : "Needs confirmation"}</strong></article>
      </div>
      {plan && (
        <div className="focus-summary">
          <div>
            <strong>Suggested initial range</strong>
            <span>{plan.lower.value} → {plan.upper.value} {presentation.configuration.quote_asset} around activation {plan.activation_price.value}</span>
          </div>
          <div>
            <strong>Operator sizing</strong>
            <span>{presentation.configuration.operator_inputs.fixed_quote_principal.value} {presentation.configuration.quote_asset} per order · {presentation.configuration.rung_count} rungs</span>
          </div>
          <div>
            <strong>Bootstrap obligation</strong>
            <span>{plan.bootstrap_obligation?.gross_base_required.value ?? "0"} {presentation.configuration.base_asset} gross backing inventory</span>
          </div>
        </div>
      )}
      <div className="gate-strip">
        {presentation.activation.gates.map((gate) => (
          <article key={gate.name} className={gate.outcome === "PASSED" ? "gate gate-pass" : "gate gate-warn"}>
            <strong>{gate.outcome}</strong>
            <span>{gate.name}</span>
            <p>{gate.reason}</p>
          </article>
        ))}
      </div>
      <ExpandableInfo title="Show detailed decision evidence">
        <div className="production-provenance">
          <span>Configuration identity</span>
          <code>{presentation.configuration.configuration_id}</code>
          <span>Observation identity</span>
          <code>{presentation.observation.observation_id}</code>
          <span>Canonical event identity</span>
          <code>{presentation.observation.event_id}</code>
          <span>Activation replay fingerprint</span>
          <code>{presentation.activation.replay_fingerprint}</code>
          {plan && <>
            <span>Grid plan epoch identity</span>
            <code>{plan.epoch_id}</code>
            <span>Plan derivation causation</span>
            <code>{plan.derivation_causation_id}</code>
          </>}
          <div>
            <strong>Operator inputs</strong>
            <span>{presentation.configuration.operator_inputs.fixed_quote_principal.value} {presentation.configuration.quote_asset} fixed quote principal · {presentation.configuration.operator_inputs.maximum_quote_capital.value} {presentation.configuration.quote_asset} capital envelope · {presentation.configuration.rung_count} rungs</span>
          </div>
          {plan && <>
            <div>
              <strong>Immutable initial epoch</strong>
              <span>{plan.derivation_semantics} · bounds {plan.lower.value}–{plan.upper.value} {presentation.configuration.quote_asset} · activation {plan.activation_price.value} · {plan.quantized_rungs.length} rungs</span>
            </div>
            <div className="initial-ladder" aria-label="Initial rung ladder">
              {plan.quantized_rungs.map((rung) => (
                <div key={rung.index}>
                  <strong>{rung.role}</strong>
                  <span>Rung {rung.index + 1} · {rung.price.value}</span>
                </div>
              ))}
            </div>
          </>}
          {blockedGates.length > 0 && <div>
            <strong>Why placement is blocked</strong>
            <span>{blockedGates.map((gate) => `${gate.name}: ${gate.reason}`).join(" · ")}</span>
          </div>}
          <div>
            <strong>Legacy comparison</strong>
            <span>{presentation.legacy_comparison.bounded_bars} bars · adaptive {presentation.legacy_comparison.legacy_spacing} legacy grid · effective ATR multiplier {presentation.legacy_comparison.effective_atr_multiplier} · {presentation.legacy_comparison.cancelled_orders} cancellation events</span>
          </div>
          <ul>
            {presentation.legacy_comparison.semantic_differences.map((difference) => (
              <li key={difference}>{difference}</li>
            ))}
          </ul>
        </div>
      </ExpandableInfo>
    </section>
  );
}

function ResearchWorkspace({ research }: { research: ResearchPort }) {
  const [configuration, setConfiguration] = useState<StudioConfiguration>();
  const [draft, setDraft] = useState<Draft>();
  const [run, setRun] = useState<StudioBacktestRun>();
  const [mode, setMode] = useState<ResearchMode>("production");
  const [error, setError] = useState<string>();
  const [running, setRunning] = useState(false);
  const [catalog, setCatalog] = useState<BinanceEurResearchCatalog>();
  const [panel, setPanel] = useState<FrozenProductionPanel>();
  const [catalogBusy, setCatalogBusy] = useState(false);
  const [panelBusy, setPanelBusy] = useState(false);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedVerifiedRangeIndex, setSelectedVerifiedRangeIndex] = useState(0);
  const [productionBusy, setProductionBusy] = useState(false);
  const [canonicalAdaptive, setCanonicalAdaptive] =
    useState<CanonicalAdaptivePresentation>();
  const [researchJobs, setResearchJobs] = useState<ResearchJob[]>([]);
  const [researchJobBusy, setResearchJobBusy] = useState(false);

  function syncSelectedDataset(
    nextPanel: FrozenProductionPanel,
    requestedSymbol?: string,
    requestedRangeIndex?: number,
  ) {
    const ordered = nextPanel.datasets
      .slice()
      .sort((left, right) => left.display_order - right.display_order);
    const preferred = ordered.find((dataset) => dataset.symbol === requestedSymbol) ?? ordered[0];
    if (!preferred) return;
    const nextRangeIndex = Math.min(
      requestedRangeIndex ?? 0,
      Math.max(preferred.verified_ranges.length - 1, 0),
    );
    setSelectedSymbol(preferred.symbol);
    setSelectedVerifiedRangeIndex(nextRangeIndex);
    setDraft((current) => current ? { ...current, symbol: preferred.symbol } : current);
  }

  useEffect(() => {
    let current = true;
    research.getConfiguration().then((value) => {
      if (current) {
        setConfiguration(value);
        setDraft(draftFrom(value));
      }
    }).catch((reason: unknown) => current && setError(reason instanceof Error ? reason.message : "Configuration unavailable"));
    research.getEurCatalog().then((value) => {
      if (!current) return;
      setCatalog(value);
    }).catch((reason: unknown) => current && setError(reason instanceof Error ? reason.message : "EUR catalog unavailable"));
    research.getProductionArchive().then((value) => {
      if (!current) return;
      setPanel(value);
      syncSelectedDataset(value);
    }).catch((reason: unknown) => current && setError(reason instanceof Error ? reason.message : "Production archive unavailable"));
    research.characterizeCanonicalAdaptive({
      symbol: "BTCEUR",
      decision_time: "2025-01-02T00:00:00Z",
      trend: "0.0000",
      volatility: "0.0100",
      reference_price: "100.00",
      activation_price: "100.00",
      event_time: null,
      observed_count: 24,
      sequence_end: 24,
      spacing: "GEOMETRIC",
      venue_environment: "production",
      tick_size: "0.01",
      step_size: "0.00001",
      minimum_price: "0.01",
      maximum_price: null,
      minimum_quantity: "0.00010",
      maximum_quantity: null,
      minimum_notional: "5.00",
      maximum_notional: null,
      max_open_orders: null,
      foreign_open_orders: 0,
      symbol_status: "TRADING",
      spot_trading_allowed: true,
      limit_maker_supported: true,
      contradictory_rules: false,
      bootstrap_complete: false,
      bootstrap_confirmed_base: "0",
      bootstrap_evidence_id: null,
      complete: true,
      evidence_quality: "ADMITTED",
    }).then((value) => current && setCanonicalAdaptive(value))
      .catch((reason: unknown) => current && setError(
        reason instanceof Error ? reason.message : "Canonical adaptive seam unavailable",
      ));
    const runId = window.location.hash.match(/experiments\/([^/]+)$/)?.[1];
    if (runId) {
      research.getBacktest(runId)
        .then((value) => current && setRun(value))
        .catch(() => undefined);
    }
    research.getResearchJobs?.().then((value) => current && setResearchJobs(value)).catch(() => undefined);
    return () => { current = false; };
  }, [research]);

  async function refreshCatalog() {
    setCatalogBusy(true);
    setError(undefined);
    try {
      setCatalog(await research.getEurCatalog(true));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "EUR catalog refresh failed");
    } finally {
      setCatalogBusy(false);
    }
  }

  function selectProductionSymbol(symbol: string) {
    if (!panel || panel.datasets.length === 0) {
      setSelectedSymbol(symbol);
      setDraft((current) => current ? { ...current, symbol } : current);
      return;
    }
    syncSelectedDataset(panel, symbol, 0);
  }

  function selectVerifiedRange(rangeIndex: number) {
    setSelectedVerifiedRangeIndex(rangeIndex);
  }

  async function refreshPanel() {
    setPanelBusy(true);
    setError(undefined);
    try {
      const refreshed = await research.getProductionArchive(true);
      setPanel(refreshed);
      syncSelectedDataset(refreshed, selectedSymbol, selectedVerifiedRangeIndex);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Production archive refresh failed");
    } finally {
      setPanelBusy(false);
    }
  }

  async function synchronizePanel() {
    setProductionBusy(true);
    setError(undefined);
    try {
      const synchronized = await research.synchronizeProductionArchive();
      setPanel(synchronized);
      syncSelectedDataset(synchronized, selectedSymbol, selectedVerifiedRangeIndex);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Production archive synchronization failed");
    } finally {
      setProductionBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setRunning(true);
    setError(undefined);
    try {
      const completed = await research.executeBacktest(requestFrom(draft));
      setRun(completed);
      window.history.replaceState(null, "", `#/research/experiments/${completed.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Backtest failed");
    } finally {
      setRunning(false);
    }
  }

  async function startAdaptiveResearch() {
    if (!draft || !research.createResearchJob || !research.getResearchJob) return;
    setResearchJobBusy(true); setError(undefined);
    try {
      const baseRequest = requestFrom(draft);
      const baseSpec = (baseRequest.spec ?? {}) as ResearchJobRequest["spec"];
      const request: ResearchJobRequest = {
        spec: { ...baseSpec, initial_cash: draft.initialCash, grid: { ...(baseSpec.grid ?? {}), adaptive: true } } as ResearchJobRequest["spec"],
        dataset_identity: selected?.dataset_id ?? `admitted-production:${draft.symbol}`,
        venue_rules_identity: "binance-spot-rules/v1",
        fee_identity: `maker:${draft.makerFee};taker:${draft.takerFee}`,
        execution_model_identity: "candle-conservative/v1",
        schema_identity: "studio-research-job/v1",
        seed: draft.seed,
      };
      const created = await research.createResearchJob(request);
      setResearchJobs((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      let latest = created;
      while (!["COMPLETED", "CANCELLED", "FAILED", "RESUMABLE"].includes(latest.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 50));
        latest = await research.getResearchJob(created.id);
        setResearchJobs((current) => current.map((item) => item.id === latest.id ? latest : item));
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Adaptive research job failed"); }
    finally { setResearchJobBusy(false); }
  }

  async function cancelAdaptiveResearch(jobId: string) {
    if (!research.cancelResearchJob) return;
    const cancelled = await research.cancelResearchJob(jobId);
    setResearchJobs((current) => current.map((item) => item.id === cancelled.id ? cancelled : item));
  }

  async function runProduction() {
    if (!draft || !panel) return;
    const selectedDataset = panel.datasets.find((item) => item.symbol === selectedSymbol);
    const selectedRange = selectedDataset?.verified_ranges[selectedVerifiedRangeIndex]
      ?? selectedDataset?.verified_ranges[0];
    if (!selectedDataset || !selectedRange) return;
    setProductionBusy(true);
    setError(undefined);
    try {
      const existing = requestFrom(draft);
      const request: ProductionArchiveBacktestBody = {
        dataset_id: selectedDataset.dataset_id,
        start: selectedRange.start,
        end: selectedRange.end,
        spec: {
          ...existing.spec,
          symbol: selectedDataset.symbol,
          market_type: "spot",
          initial_cash: draft.initialCash,
          n_trials: 1,
          data: { kind: "manifested_parquet", dataset_id: selectedDataset.dataset_id },
        },
        options: existing.options,
      };
      const completed = await research.executeProductionArchiveBacktest(request);
      setRun(completed);
      window.history.replaceState(null, "", `#/research/experiments/${completed.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Production backtest failed");
    } finally {
      setProductionBusy(false);
    }
  }

  const selected = panel?.datasets.find((item) => item.symbol === selectedSymbol);
  const selectedCatalogSymbol = catalog?.symbols.find((item) => item.symbol === selectedSymbol);
  const catalogOptions = catalog?.symbols
    .filter((item) => item.symbol.includes(symbolFilter.trim().toUpperCase()))
    .sort((left, right) => left.liquidity_rank - right.liquidity_rank)
    .map((item) => ({ symbol: item.symbol, display_order: item.liquidity_rank })) ?? [];
  const visibleSymbols = panel?.datasets
    .filter((item) => item.symbol.includes(symbolFilter.trim().toUpperCase()))
    .sort((left, right) => left.display_order - right.display_order) ?? [];
  const symbolOptions = visibleSymbols.length > 0 ? visibleSymbols : catalogOptions;
  const selectedRange = selected?.verified_ranges[selectedVerifiedRangeIndex]
    ?? selected?.verified_ranges[0];
  const selectedRangeDays = selectedRange ? rangeDays(selectedRange.start, selectedRange.end) : 0;
  const totalLocalDatasets = panel?.datasets.length ?? 0;
  const verifiedRangeCount = selected?.verified_ranges.length ?? 0;

  useEffect(() => {
    if (!selectedRange) return;
    const replayStartPrice = Number(selectedRange.start_open_price);
    if (!Number.isFinite(replayStartPrice) || replayStartPrice <= 0) return;
    setDraft((current) => {
      if (!current) return current;
      const anchored = anchorDraftToReplayStart(
        { ...current, symbol: selected?.symbol ?? current.symbol },
        replayStartPrice,
      );
      if (anchored.symbol === current.symbol
        && anchored.lower === current.lower
        && anchored.upper === current.upper) {
        return current;
      }
      return anchored;
    });
  }, [selected?.symbol, selectedRange?.start, selectedRange?.end, selectedRange?.start_open_price]);

  if (!draft || !configuration) {
    return <main className="workspace"><p>{error ?? "Loading canonical configuration…"}</p></main>;
  }

  const update = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft({ ...draft, [key]: value });

  return (
    <main className="workspace">
      <div className="page-title">
        <div>
          <p className="eyebrow">Research · Experiments</p>
          <h1>Choose how you want to test the strategy</h1>
          <p>
            Start with one path at a time. Use verified EUR market history for reality-anchored replay, or switch to synthetic data when you want fast parameter experiments.
          </p>
        </div>
        <span className="scope">{mode === "production" ? "Production replay" : "Synthetic sandbox"}</span>
      </div>

      <ModeSelector mode={mode} onChange={setMode} />

      {error && <p className="error" role="alert">{error}</p>}

      {mode === "production" ? (
        <>
        <section className="focus-card" aria-labelledby="production-history-heading">
          <div className="result-heading">
            <div>
              <p className="eyebrow">Verified production replay</p>
              <h2 id="production-history-heading">Run over local EUR market history</h2>
              <p className="section-copy">
                Choose a verified local EUR dataset, keep the grid settings visible in the same section, then run an exact replay over stored production candles.
              </p>
            </div>
            <span className="scope">{panel?.status?.toUpperCase() ?? "PENDING"}</span>
          </div>

          <div className="summary-grid">
            <article><span>Eligible EUR symbols</span><strong>{catalog?.symbols.length ?? "—"}</strong></article>
            <article><span>Local datasets ready</span><strong>{totalLocalDatasets}</strong></article>
            <article><span>Selected verified windows</span><strong>{verifiedRangeCount}</strong></article>
            <article><span>Estimated local storage</span><strong>{panel ? formatBytes(panel.preview.estimated_storage_bytes) : "—"}</strong></article>
          </div>

          <div className="production-controls friendly">
            <label>
              Find a symbol
              <input
                aria-label="Filter EUR symbols"
                value={symbolFilter}
                onChange={(event) => setSymbolFilter(event.currentTarget.value)}
                placeholder="BTC, ETH…"
              />
            </label>
            <label>
              EUR production symbol
              <select
                aria-label="EUR production symbol"
                value={selectedSymbol}
                onChange={(event) => selectProductionSymbol(event.currentTarget.value)}
              >
                {symbolOptions.map((item) => (
                  <option key={item.symbol} value={item.symbol}>
                    #{item.display_order} · {item.symbol}{visibleSymbols.length === 0 ? " · local archive pending" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Verified local range
              <select
                aria-label="Verified local range"
                disabled={!selected || selected.verified_ranges.length === 0}
                value={String(selectedVerifiedRangeIndex)}
                onChange={(event) => selectVerifiedRange(Number(event.currentTarget.value))}
              >
                {selected?.verified_ranges.map((range, index) => (
                  <option key={`${range.start}-${range.end}`} value={String(index)}>
                    {rangeChipLabel(range)}
                  </option>
                )) ?? <option value="0">No verified local range</option>}
              </select>
            </label>
          </div>

          {selected && selectedRange && (
            <>
              <div className="selected-range-card">
                <div>
                  <span>Selected market</span>
                  <strong>{selected.symbol}</strong>
                  <p>Stable local dataset · EUR quote asset · verified Spot production replay only.</p>
                </div>
                <div>
                  <span>What will run</span>
                  <strong>{selectedRangeDays} day replay</strong>
                  <p>{rangeLabel(selectedRange)}</p>
                </div>
                <div>
                  <span>Available locally</span>
                  <strong>{selected.total_rows.toLocaleString("en-US")} verified 1m candles</strong>
                  <p>{selected.partitions.filter((item) => item.active).length.toLocaleString("en-US")} active monthly partitions · {formatBytes(selected.stored_bytes)} stored locally</p>
                </div>
              </div>

              <ExpandableInfo title="Why this verified range is selectable" defaultOpen>
                <div className="insight-list">
                  <p><strong>Official archive availability:</strong> {selected.coverage.first_date} → {selected.coverage.last_date}</p>
                  <p><strong>Verified local range:</strong> {rangeLabel(selectedRange)}</p>
                  <p>{friendlyRangeExplanation(selectedRange)}</p>
                  <p><strong>Safety note:</strong> production-history and synthetic scenarios remain separate. These EUR backtests read only verified local production partitions.</p>
                </div>
              </ExpandableInfo>
            </>
          )}

          <section className="nested-panel" aria-labelledby="production-grid-settings-heading">
            <div className="result-heading">
              <div>
                <p className="eyebrow">Strategy settings</p>
                <h3 id="production-grid-settings-heading">Tune the grid for this replay</h3>
                <p className="section-copy">
                  These settings drive the backtest that will run over the selected verified production range.
                </p>
              </div>
            </div>
            <ProductionSetupGuidance
              draft={draft}
              selected={selected}
              selectedCatalogSymbol={selectedCatalogSymbol}
              selectedRange={selectedRange}
              catalogRetrievedAt={catalog?.retrieved_at}
            />
            <StrategyFields configuration={configuration} draft={draft} update={update} />
            <div className="review">
              <div>
                <strong>Production replay summary</strong>
                <span>{selected?.symbol ?? draft.symbol} · {draft.levels} rung prices · {draft.spacing} spacing · {selectedRangeDays || "—"} day replay</span>
              </div>
              <button
                className="primary-cta"
                disabled={productionBusy || !selectedRange}
                type="button"
                onClick={runProduction}
              >
                {productionBusy ? "Running…" : "Run production-history backtest"}
              </button>
            </div>
          </section>

          {run && <Results run={run} />}

          {canonicalAdaptive && (
            <ExpandableInfo title="See why the system suggests a certain starting grid">
              <CanonicalAdaptiveCard presentation={canonicalAdaptive} />
            </ExpandableInfo>
          )}

          {!selected && catalog && (
            <div className="archive-empty-state">
              <p><strong>Official catalog loaded:</strong> {catalog.symbols.length} EUR symbols are available, but no verified local dataset is synchronized yet.</p>
              <div className="action-row">
                <button disabled={catalogBusy || productionBusy} type="button" onClick={refreshCatalog}>
                  {catalogBusy ? "Refreshing…" : "Refresh official market list"}
                </button>
                <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={refreshPanel}>
                  {panelBusy ? "Refreshing…" : "Refresh local archive status"}
                </button>
                <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={synchronizePanel}>
                  {productionBusy ? "Synchronizing…" : "Synchronize local archive"}
                </button>
              </div>
              <p>No verified local range is available until the archive is synchronized.</p>
            </div>
          )}

          {selected && (
            <>
              <ExpandableInfo title="Show selected symbol details">
                <div className="symbol-detail-grid">
                  <article><span>Liquidity rank</span><strong>#{selected.display_order}</strong></article>
                  <article><span>Coverage</span><strong>{selected.coverage.first_date} → {selected.coverage.last_date}</strong></article>
                  <article><span>Pending months</span><strong>{selected.pending_partition_months.length === 0 ? "None" : selected.pending_partition_months.length}</strong></article>
                  <article><span>Verified windows</span><strong>{selected.verified_ranges.length}</strong></article>
                </div>
              </ExpandableInfo>

              <ExpandableInfo title="Show archive maintenance and technical evidence">
                <div className="action-row">
                  <button disabled={catalogBusy || productionBusy} type="button" onClick={refreshCatalog}>
                    {catalogBusy ? "Refreshing…" : "Refresh official market list"}
                  </button>
                  <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={refreshPanel}>
                    {panelBusy ? "Refreshing…" : "Refresh local archive status"}
                  </button>
                  <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={synchronizePanel}>
                    {productionBusy ? "Synchronizing…" : "Synchronize local archive"}
                  </button>
                </div>
                <div className="production-provenance">
                  {catalog && <>
                    <span>Catalog identity</span>
                    <code>{catalog.catalog_id}</code>
                  </>}
                  <span>Archive identity</span>
                  <code>{panel?.archive_id}</code>
                  <span>Dataset identity</span>
                  <code>{selected.dataset_id}</code>
                  <span>Latest partition identities</span>
                  <code>{selected.partitions.filter((item) => item.active).slice(-3).map((partition) => partition.partition_id).join(", ")}</code>
                  <div><strong>Acquisition preview</strong><span>{panel?.preview.pending_partitions ?? 0} pending partitions · {panel ? formatBytes(panel.preview.estimated_download_bytes) : "—"} estimated download</span></div>
                  {(panel?.blocking_reasons.length ?? 0) > 0 && <div><strong>Blocked admissions</strong><span>{panel?.blocking_reasons.join("; ")}</span></div>}
                  <div><strong>Symbol panel</strong><span>{panel?.datasets.map((dataset) => `#${dataset.display_order} ${dataset.symbol}`).join(" · ")}</span></div>
                </div>
              </ExpandableInfo>
            </>
          )}
        </section>
        <section className="production-data" aria-labelledby="adaptive-research-heading">
          <div className="result-heading"><div><p className="eyebrow">Ticket 15 · resumable execution</p><h2 id="adaptive-research-heading">Run adaptive research outside the browser</h2><p>The local service owns execution and SQLite checkpoints. Close this browser, reopen Studio, and reconnect to the same job identity and sealed evidence.</p></div><span className="scope">NO TRADING AUTHORITY</span></div>
          <p className="job-note">This inventory grid is net-long base exposure. The 250 USDT Azure MVP is a validation/learning vehicle, not infrastructure-net-profitable operation.</p>
          <button type="button" disabled={researchJobBusy} onClick={startAdaptiveResearch}>{researchJobBusy ? "Research running…" : "Start adaptive research job"}</button>
          {researchJobs.map((job) => <ResearchJobCard key={job.id} job={job} onCancel={() => cancelAdaptiveResearch(job.id)} />)}
        </section>
        </>
      ) : (
        <form onSubmit={submit} className="focus-card" aria-labelledby="synthetic-heading">
          <div className="result-heading">
            <div>
              <p className="eyebrow">Quick synthetic sandbox</p>
              <h2 id="synthetic-heading">Try the strategy with fast synthetic data</h2>
              <p className="section-copy">
                This is the fastest way to experiment with ranges, spacing, and fees before you spend time on verified production history.
              </p>
            </div>
            <span className="scope">Fast iteration</span>
          </div>

          <ExpandableInfo title="When should I use the synthetic sandbox?" defaultOpen>
            <div className="insight-list">
              <p>Use it to compare parameter ideas quickly.</p>
              <p>Do not treat it as venue proof or profitability proof.</p>
              <p>When you want a reality-anchored replay, switch back to production replay above.</p>
            </div>
          </ExpandableInfo>

          <StrategyFields configuration={configuration} draft={draft} update={update} />

          {canonicalAdaptive && (
            <ExpandableInfo title="See why the system suggests a certain starting grid">
              <CanonicalAdaptiveCard presentation={canonicalAdaptive} />
            </ExpandableInfo>
          )}

          <div className="review">
            <div>
              <strong>Synthetic submission summary</strong>
              <span>{draft.symbol} · {draft.levels} rung prices · {draft.spacing} spacing · seed {draft.seed}</span>
            </div>
            <button disabled={running} type="submit">{running ? "Running…" : "Run synthetic backtest"}</button>
          </div>

          {run && <Results run={run} />}
        </form>
      )}
    </main>
  );
}

function OperationsWorkspace({ research }: { research: ResearchPort }) {
  const [presentation, setPresentation] = useState<SafetyPosturePresentation>();
  const [controls, setControls] = useState<OperatorControlsPresentation>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let current = true;
    research.getSafetyPosture()
      .then((value) => current && setPresentation(value))
      .catch((reason: unknown) => current && setError(
        reason instanceof Error ? reason.message : "Safety posture unavailable",
      ));
    research.getOperatorControls()
      .then((value) => current && setControls(value))
      .catch((reason: unknown) => current && setError(
        reason instanceof Error ? reason.message : "Operator controls unavailable",
      ));
    return () => { current = false; };
  }, [research]);

  return <main className="workspace empty">
    <p className="eyebrow">Operations · Command Center</p>
    <h1>Deterministic safety posture</h1>
    <p>Canonical facts are presented separately. This view does not dispatch, queue, cancel, or place commands.</p>
    <div className="boundary"><strong>GATEWAY NOT CONFIGURED</strong><span>COMMAND AUTHORITY UNAVAILABLE</span><span>No commands are cached or queued by this browser.</span></div>
    {error && <p className="error" role="alert">{error}</p>}
    {presentation && <section className="production-data" aria-labelledby="safety-posture-heading">
      <div className="result-heading">
        <div><p className="eyebrow">Canonical overlay</p><h2 id="safety-posture-heading">Safety and venue evidence</h2></div>
        <span className="scope">{presentation.safety.posture}</span>
      </div>
      <div className="production-provenance">
        <span>Deterministic safety fingerprint</span><code>{presentation.fingerprint}</code>
        <div><strong>Grid lifecycle</strong><span>{presentation.lifecycle.grid_lifecycle}</span></div>
        <div><strong>Adaptation state</strong><span>{presentation.lifecycle.adaptation_state}</span></div>
        <div><strong>Epoch transition</strong><span>{presentation.lifecycle.epoch_transition_state}</span></div>
        <div><strong>Runtime lifecycle</strong><span>{presentation.lifecycle.runtime_lifecycle}</span></div>
        <div><strong>Safety posture</strong><span>{presentation.safety.posture}</span></div>
        <div><strong>Freshness</strong><span>{presentation.freshness.map((item) => `${item.evidence_class}: ${item.condition}`).join(" · ")}</span></div>
        <div><strong>Reconciliation</strong><span>{presentation.lifecycle.reconciliation_state}</span></div>
        <div><strong>Venue condition</strong><span>{presentation.venue.condition} · evidence preserved as {presentation.venue.evidence_id}</span></div>
        {presentation.venue.wind_down_deadline && <div><strong>Wind-down deadline</strong><span>{new Date(presentation.venue.wind_down_deadline).toISOString()}</span></div>}
        <div><strong>Allowed command classes</strong><span>{presentation.safety.allowed_command_classes.join(" · ")}</span></div>
        <div><strong>Clock evidence</strong><span>{presentation.safety.clock_offset.value}s offset · {presentation.safety.scheduling_delay.value}s scheduling delay · {presentation.safety.round_trip_latency.value}s observation round trip</span></div>
        <div><strong>Capital evidence</strong><span>{presentation.capital.committed_principal.value} / {presentation.capital.capital_envelope.value} quote committed · {presentation.capital.fee_reserve.value} fee reserve</span></div>
      </div>
    </section>}
    {controls && <section className="production-data" aria-labelledby="operator-controls-heading">
      <div className="result-heading">
        <div><p className="eyebrow">Canonical operator lifecycle</p><h2 id="operator-controls-heading">Operate controls and terminal disposal</h2></div>
        <span className="scope">{controls.projection.transition_state}</span>
      </div>
      <div className="production-provenance">
        <span>Deterministic control fingerprint</span><code>{controls.fingerprint}</code>
        <div><strong>Active epoch</strong><span>{controls.projection.active_epoch_id}</span></div>
        <div><strong>Proposed epoch</strong><span>{controls.projection.proposed_epoch_id ?? "none"}</span></div>
        <div><strong>Posture</strong><span>{controls.projection.posture}</span></div>
        <div><strong>Inventory basis</strong><span>{controls.inventory_basis.quantity.value} {controls.inventory_basis.base_asset} · {controls.inventory_basis.source}</span></div>
        <div><strong>Pause</strong><span>{controls.pause.availability} · cancel {controls.pause.cancel_obligation_ids.length} obligations · retain {controls.pause.retained_obligation_ids.length}</span></div>
        <div><strong>Resume</strong><span>{controls.resume.availability} · {controls.resume.gates.filter((gate) => gate.outcome === "FAILED").map((gate) => gate.name).join(" · ")}</span></div>
        <div><strong>Operator Stop</strong><span>{controls.operator_stop.availability} · {controls.operator_stop.selected_disposition ?? "DISPOSITION REQUIRED"} · {controls.operator_stop.late_fill_ids.length} late fills admitted</span></div>
        <div><strong>Emergency Stop</strong><span>{controls.emergency_stop.availability} · {controls.emergency_stop.idempotent ? "IDEMPOTENT" : "NON-IDEMPOTENT"} · {controls.emergency_stop.environment_bound ? "ENVIRONMENT-BOUND" : "UNSCOPED"}</span></div>
        <div><strong>Terminal trigger</strong><span>{controls.terminal.trigger} · {controls.terminal.state}</span></div>
        <div><strong>Terminal disposal waves</strong><span>{controls.terminal.waves.map((wave) => `W${wave.wave} ${wave.order_type} ${wave.outcome}`).join(" · ")}</span></div>
        <div><strong>Golden replay cases</strong><span>{controls.terminal.golden_replay_cases.map((item) => item.case_name).join(" · ")}</span></div>
      </div>
    </section>}
  </main>;
}

export function App({ research }: { research: ResearchPort }) {
  const [workspace, setWorkspace] = useState<Workspace>("research");
  return <div className="shell"><aside><div className="brand"><span>GRIDLAB</span><strong>Operator Studio</strong></div><div className="workspace-switch"><button aria-label="Research workspace" className={workspace === "research" ? "selected" : ""} onClick={() => setWorkspace("research")}>Research</button><button aria-label="Operations workspace" className={workspace === "operations" ? "selected" : ""} onClick={() => setWorkspace("operations")}>Operations</button></div><Navigation workspace={workspace} /></aside><div className="main"><AuthorityHeader workspace={workspace} />{workspace === "research" ? <ResearchWorkspace research={research} /> : <OperationsWorkspace research={research} />}</div></div>;
}
