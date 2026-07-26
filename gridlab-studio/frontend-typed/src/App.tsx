import { useEffect, useState, type FormEvent } from "react";

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

function utcDay(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function inclusiveEndDay(exclusiveIso: string): string {
  const end = new Date(exclusiveIso);
  end.setUTCDate(end.getUTCDate() - 1);
  return end.toISOString().slice(0, 10);
}

function Navigation({ workspace }: { workspace: Workspace }) {
  return (
    <nav aria-label="Studio" className="nav-groups">
      <section aria-labelledby="research-nav">
        <h2 id="research-nav">Research</h2>
        {['Overview', 'Experiments', 'Candidates', 'Data', 'Learn'].map((item) => (
          <a className={workspace === "research" && item === "Experiments" ? "active" : ""} href={`#/research/${item.toLowerCase()}`} key={item}>{item}</a>
        ))}
      </section>
      <section aria-labelledby="operations-nav">
        <h2 id="operations-nav">Operations</h2>
        {['Command Center', 'Qualification', 'Reconciliation', 'Incidents', 'Evidence & Audit'].map((item) => (
          <a className={workspace === "operations" && item === "Command Center" ? "active" : ""} href={`#/operations/${item.toLowerCase().replaceAll(' ', '-')}`} key={item}>{item}</a>
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

function NumberField({ label, value, onChange, min, step = 1 }: { label: string; value: number; onChange(value: number): void; min?: number; step?: number }) {
  return <label>{label}<input type="number" value={value} min={min} step={step} onChange={(event) => onChange(event.currentTarget.valueAsNumber)} /></label>;
}

function Results({ run }: { run: StudioBacktestRun }) {
  const result = run.primary_result;
  const quoteAsset = run.provenance?.quote_asset ?? "USDT";
  return (
    <section className="results" aria-live="polite">
      <div className="result-heading"><div><p className="eyebrow">Completed research run</p><h2>{run.result.symbol} primary result</h2></div><span className="verdict">{result.verdict}</span></div>
      <div className="metrics">
        <article className="primary"><span>Net return</span><strong>{formatPercent(result.net_return)}</strong></article>
        <article><span>Final equity</span><strong>{formatMoney(result.final_equity, quoteAsset)}</strong></article>
        <article><span>Max drawdown</span><strong>{formatPercent(result.max_drawdown)}</strong></article>
        <article><span>Completed trades</span><strong>{result.completed_trades}</strong></article>
        <article><span>Fees paid</span><strong>{formatMoney(result.fees_paid, quoteAsset)}</strong></article>
      </div>
      <div className="record"><span>Authoritative local record</span><code>{run.id}</code><span>Saved by the research service · {new Date(run.created_at).toLocaleString()}</span></div>
      <div className="production-provenance">
        <div><strong>CANDLE SIMULATION ONLY</strong><span>{run.result.simulation?.canonical_core ? "Canonical adaptive core" : "Research candle harness"}</span></div>
        <div><strong>NOT VENUE EXECUTION PROOF</strong><span>{run.result.simulation?.limitations?.[0] ?? "Candle fills remain conservative assumptions."}</span></div>
      </div>
      {run.provenance && <div className="production-provenance">
        <div><strong>PRODUCTION HISTORY</strong><span>Official Binance Spot archive</span></div>
        <div><strong>TESTNET HISTORY NOT USED</strong><span>Testnet is not profitability evidence</span></div>
        <div><strong>{run.provenance.symbol}</strong><span>{new Date(run.provenance.requested_start).toISOString()} → {new Date(run.provenance.requested_end).toISOString()} · {run.provenance.candle_count.toLocaleString("en-US")} candles</span></div>
        <div><strong>Coverage</strong><span>{new Date(run.provenance.coverage.first_verified_open_time).toISOString()} → {new Date(run.provenance.coverage.last_verified_open_time).toISOString()}</span></div>
        {run.provenance.catalog_identity && <><span>Catalog identity</span><code>{run.provenance.catalog_identity}</code></>}
        <span>Dataset identity</span><code>{run.provenance.dataset_id}</code>
        <span>Manifest identity</span><code>{run.provenance.manifest_identity}</code>
        <span>Partition identities</span><code>{run.provenance.partition_identities.join(", ")}</code>
        <span>Deterministic backtest fingerprint</span><code>{run.provenance.backtest_fingerprint}</code>
      </div>}
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
    {!["COMPLETED", "CANCELLED"].includes(job.status) && <button type="button" onClick={onCancel}>Cancel and preserve checkpoint</button>}
  </section>;
}

function CanonicalAdaptiveCard({
  presentation,
}: {
  presentation: CanonicalAdaptivePresentation;
}) {
  const plan = presentation.derived_plan;
  return (
    <section className="production-data" aria-labelledby="adaptive-seam-heading">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Canonical exact seam</p>
          <h2 id="adaptive-seam-heading">Adaptive policy characterization</h2>
          <p>Quality-approved past-only evidence drives one immutable initial epoch, explicit activation gates, and a fully quantified bootstrap obligation.</p>
        </div>
        <span className="scope">{presentation.activation.lifecycle}</span>
      </div>
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
          <strong>{presentation.decision.adaptation_state}</strong>
          <span>{presentation.decision.intent} · {presentation.decision.reason}</span>
        </div>
        <div>
          <strong>OPERATOR INPUTS</strong>
          <span>{presentation.configuration.operator_inputs.fixed_quote_principal.value} {presentation.configuration.quote_asset} fixed quote principal · {presentation.configuration.operator_inputs.maximum_quote_capital.value} {presentation.configuration.quote_asset} capital envelope · {presentation.configuration.rung_count} rungs</span>
        </div>
        <div>
          <strong>{presentation.activation.lifecycle}</strong>
          <span>{presentation.activation.ladder_placement_allowed ? "Ladder placement allowed" : "Ladder placement blocked"} · no pending or automatically armed activation</span>
        </div>
        <div className="activation-gates" aria-label="Initial activation gates">
          {presentation.activation.gates.map((gate) => (
            <div key={gate.name}>
              <strong>{gate.outcome}</strong>
              <span>{gate.name} · {gate.reason}</span>
            </div>
          ))}
        </div>
        {plan && <>
          <div>
            <strong>IMMUTABLE INITIAL EPOCH</strong>
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
          <div>
            <strong>BOOTSTRAP OBLIGATION</strong>
            <span>{plan.bootstrap_obligation?.gross_base_required.value ?? "0"} {presentation.configuration.base_asset} gross · {plan.bootstrap_obligation?.fee_base_coverage.value ?? "0"} conservative base-fee coverage · {plan.maximum_planned_inventory?.value ?? "0"} maximum planned inventory</span>
          </div>
        </>}
        {!plan && <div><strong>NO EPOCH DERIVED</strong><span>Activation was rejected before acquisition; a fresh explicit attempt is required.</span></div>}
        <div>
          <strong>LEGACY COMPARISON</strong>
          <span>{presentation.legacy_comparison.bounded_bars} bars · adaptive {presentation.legacy_comparison.legacy_spacing} legacy grid · effective ATR multiplier {presentation.legacy_comparison.effective_atr_multiplier} · {presentation.legacy_comparison.cancelled_orders} cancellation events</span>
        </div>
        <ul>
          {presentation.legacy_comparison.semantic_differences.map((difference) => (
            <li key={difference}>{difference}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ResearchWorkspace({ research }: { research: ResearchPort }) {
  const [configuration, setConfiguration] = useState<StudioConfiguration>();
  const [draft, setDraft] = useState<Draft>();
  const [run, setRun] = useState<StudioBacktestRun>();
  const [error, setError] = useState<string>();
  const [running, setRunning] = useState(false);
  const [catalog, setCatalog] = useState<BinanceEurResearchCatalog>();
  const [panel, setPanel] = useState<FrozenProductionPanel>();
  const [catalogBusy, setCatalogBusy] = useState(false);
  const [panelBusy, setPanelBusy] = useState(false);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedVerifiedRangeIndex, setSelectedVerifiedRangeIndex] = useState(0);
  const [productionStart, setProductionStart] = useState("2025-01-01");
  const [productionEnd, setProductionEnd] = useState("2025-01-01");
  const [productionBusy, setProductionBusy] = useState(false);
  const [canonicalAdaptive, setCanonicalAdaptive] =
    useState<CanonicalAdaptivePresentation>();
  const [researchJobs, setResearchJobs] = useState<ResearchJob[]>([]);
  const [researchJobBusy, setResearchJobBusy] = useState(false);

  function applyVerifiedRange(
    dataset: FrozenProductionPanel["datasets"][number],
    rangeIndex = 0,
  ) {
    const range = dataset.verified_ranges[rangeIndex];
    setSelectedVerifiedRangeIndex(rangeIndex);
    if (!range) return;
    setProductionStart(utcDay(range.start));
    setProductionEnd(inclusiveEndDay(range.end));
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
      const selected = [...value.symbols].sort(
        (left, right) => left.liquidity_rank - right.liquidity_rank,
      )[0];
      if (selected) {
        setSelectedSymbol(selected.symbol);
        setProductionStart(selected.coverage.last_date);
        setProductionEnd(selected.coverage.last_date);
      }
    }).catch((reason: unknown) => current && setError(reason instanceof Error ? reason.message : "EUR catalog unavailable"));
    research.getProductionArchive().then((value) => {
      if (!current) return;
      setPanel(value);
      const selectedDataset = [...value.datasets].sort(
        (left, right) => left.display_order - right.display_order,
      )[0];
      if (selectedDataset?.verified_ranges[0]) {
        setSelectedSymbol(selectedDataset.symbol);
        applyVerifiedRange(selectedDataset);
      }
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
    if (runId) research.getBacktest(runId).then((value) => current && setRun(value)).catch(() => undefined);
    research.getResearchJobs?.().then((value) => current && setResearchJobs(value)).catch(() => undefined);
    return () => { current = false; };
  }, [research]);

  async function refreshCatalog() {
    setCatalogBusy(true); setError(undefined);
    try {
      const value = await research.getEurCatalog(true);
      setCatalog(value);
      if (!value.symbols.some((item) => item.symbol === selectedSymbol)) {
        const selected = value.symbols[0];
        setSelectedSymbol(selected?.symbol ?? "");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "EUR catalog refresh failed");
    } finally { setCatalogBusy(false); }
  }

  function selectProductionSymbol(symbol: string) {
    setSelectedSymbol(symbol);
    const selected = panel?.datasets.find((item) => item.symbol === symbol);
    if (selected) {
      applyVerifiedRange(selected);
    } else {
      setSelectedVerifiedRangeIndex(0);
    }
    setDraft((current) => current ? { ...current, symbol } : current);
  }

  function selectVerifiedRange(rangeIndex: number) {
    setSelectedVerifiedRangeIndex(rangeIndex);
    const selected = panel?.datasets.find((item) => item.symbol === selectedSymbol);
    if (!selected) return;
    applyVerifiedRange(selected, rangeIndex);
  }

  async function refreshPanel() {
    setPanelBusy(true); setError(undefined);
    try { setPanel(await research.getProductionArchive(true)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Production archive refresh failed"); }
    finally { setPanelBusy(false); }
  }

  async function synchronizePanel() {
    setProductionBusy(true); setError(undefined);
    try { setPanel(await research.synchronizeProductionArchive()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Production archive synchronization failed"); }
    finally { setProductionBusy(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setRunning(true); setError(undefined);
    try {
      const completed = await research.executeBacktest(requestFrom(draft));
      setRun(completed);
      window.history.replaceState(null, "", `#/research/experiments/${completed.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Backtest failed");
    } finally { setRunning(false); }
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
    if (!selectedDataset) return;
    setProductionBusy(true); setError(undefined);
    try {
      const existing = requestFrom(draft);
      const start = new Date(`${productionStart}T00:00:00Z`).toISOString();
      const endInclusive = new Date(`${productionEnd}T00:00:00Z`);
      const end = new Date(endInclusive.getTime() + 86_400_000).toISOString();
      const request: ProductionArchiveBacktestBody = {
        dataset_id: selectedDataset.dataset_id,
        start,
        end,
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
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Production backtest failed"); }
    finally { setProductionBusy(false); }
  }

  if (!draft || !configuration) return <main className="workspace"><p>{error ?? "Loading canonical configuration…"}</p></main>;
  const update = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft({ ...draft, [key]: value });
  const selected = panel?.datasets.find((item) => item.symbol === selectedSymbol);
  const rankedPanelMembers = panel?.datasets
    .slice()
    .sort((left, right) => left.display_order - right.display_order) ?? [];
  const visibleSymbols = panel?.datasets
    .filter((item) => item.symbol.includes(symbolFilter.trim().toUpperCase()))
    .sort((left, right) => left.display_order - right.display_order) ?? [];
  const selectedRange = selected?.verified_ranges[selectedVerifiedRangeIndex]
    ?? selected?.verified_ranges[0];
  const selectedRangeStart = selectedRange ? utcDay(selectedRange.start) : undefined;
  const selectedRangeEnd = selectedRange ? inclusiveEndDay(selectedRange.end) : undefined;
  return (
    <main className="workspace">
      <div className="page-title"><div><p className="eyebrow">Research · Experiments</p><h1>Static grid backtest</h1><p>Configure one deterministic local experiment. The browser submits work; the research service owns the completed record.</p></div><span className="scope">MIGRATED WORKFLOW</span></div>
      {canonicalAdaptive && <CanonicalAdaptiveCard presentation={canonicalAdaptive} />}
      <section className="production-panel" aria-labelledby="production-panel-heading">
        <div className="result-heading"><div><p className="eyebrow">Synchronized production evidence</p><h2 id="production-panel-heading">Ten-symbol EUR production archive</h2><p>The fixed EUR panel is synchronized from official Binance Spot archives, preserving each symbol’s first available date, immutable monthly partitions, and exact snapshot manifests for local backtests.</p></div><span className="scope">{panel?.status?.toUpperCase() ?? "PENDING"}</span></div>
        {panel && <div className="catalog-identity">
          <div><strong>{panel.datasets.length} fixed EUR datasets</strong><span>{panel.preview.pending_partitions} pending partitions · {panel.preview.source_objects} source objects in preview</span></div>
          <span>Archive identity</span><code>{panel.archive_id}</code>
          <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={refreshPanel}>{panelBusy ? "Refreshing…" : "Refresh archive preview"}</button>
          <button disabled={panelBusy || productionBusy || catalogBusy} type="button" onClick={synchronizePanel}>{productionBusy ? "Synchronizing…" : "Synchronize archive"}</button>
        </div>}
        {panel && <div className="history-availability" aria-live="polite">
          <div><span>Acquisition preview</span><strong>{formatBytes(panel.preview.estimated_download_bytes)}</strong></div>
          <span>{panel.preview.pending_partitions} partitions · {formatBytes(panel.preview.estimated_storage_bytes)} estimated local storage · {panel.sources[0]?.identity}</span>
        </div>}
        {rankedPanelMembers.length > 0 && <div className="symbol-evidence">
          <div><strong>Fixed order panel</strong><span>Exact EUR symbols are frozen by specification, not live ranking.</span></div>
          {rankedPanelMembers.map((member) => <div key={member.symbol}>
            <strong>#{member.display_order} · {member.symbol}</strong>
            <span>{member.coverage.first_date} → {member.coverage.last_date} · {member.partitions.filter((item) => item.active).length} active partitions · {formatBytes(member.stored_bytes)}</span>
            <span>{member.verified_ranges.length === 0 ? "No verified local range yet" : member.verified_ranges.map((range) => `${new Date(range.start).toISOString()} → ${new Date(range.end).toISOString()}`).join(" · ")}</span>
            <span>{member.pending_partition_months.length === 0 ? "Immutable monthly archive admitted" : `Pending months: ${member.pending_partition_months.join(", ")}`}</span>
          </div>)}
        </div>}
        {panel && panel.blocking_reasons.length > 0 && <div className="manifest-card">
          <div><strong>Blocked admissions</strong><span>Missing or invalid local partitions fail closed.</span></div>
          {panel.blocking_reasons.map((entry) => <span key={entry}>{entry}</span>)}
        </div>}
      </section>
      <section className="production-data" aria-labelledby="production-data-heading">
        <div className="result-heading"><div><p className="eyebrow">Local backtest snapshot</p><h2 id="production-data-heading">Run over synchronized EUR history</h2><p>Select a verified local EUR dataset window. The backend creates an immutable snapshot manifest, prunes to only required partitions and rows, and refuses incomplete ranges instead of truncating them.</p></div><span className="scope">LOCAL VERIFIED RANGE</span></div>
        {catalog && <div className="catalog-identity">
          <div><strong>{catalog.symbols.length} eligible EUR symbols</strong><span>Public compatibility snapshot · {new Date(catalog.retrieved_at).toLocaleString()}</span></div>
          <span>Catalog identity</span><code>{catalog.catalog_id}</code>
          <button disabled={catalogBusy || productionBusy} type="button" onClick={refreshCatalog}>{catalogBusy ? "Refreshing…" : "Refresh official catalog"}</button>
        </div>}
        <div className="production-controls">
          <label>Filter symbols<input aria-label="Filter EUR symbols" value={symbolFilter} onChange={(event) => setSymbolFilter(event.currentTarget.value)} placeholder="BTC, ETH…" /></label>
          <label>EUR production symbol<select aria-label="EUR production symbol" value={selectedSymbol} onChange={(event) => selectProductionSymbol(event.currentTarget.value)}>{visibleSymbols.map((item) => <option key={item.symbol} value={item.symbol}>#{item.display_order} · {item.symbol}</option>)}</select></label>
          <label>Verified local range<select aria-label="Verified local range" disabled={!selected || selected.verified_ranges.length === 0} value={String(selectedVerifiedRangeIndex)} onChange={(event) => selectVerifiedRange(Number(event.currentTarget.value))}>{selected?.verified_ranges.map((range, index) => <option key={`${range.start}-${range.end}`} value={String(index)}>{utcDay(range.start)} → {inclusiveEndDay(range.end)}</option>) ?? <option value="0">No verified local range</option>}</select></label>
          <label>UTC start day<input aria-label="UTC start day" type="date" min={selectedRangeStart} max={selectedRangeEnd} value={productionStart} onChange={(event) => setProductionStart(event.currentTarget.value)} /></label>
          <label>UTC end day<input aria-label="UTC end day" type="date" min={productionStart || selectedRangeStart} max={selectedRangeEnd} value={productionEnd} onChange={(event) => setProductionEnd(event.currentTarget.value)} /></label>
          <button disabled={productionBusy || !selected || selected.verified_ranges.length === 0} type="button" onClick={runProduction}>Run production-history backtest</button>
        </div>
        {selected && <div className="history-availability" aria-live="polite">
          <div>
            <span>Official archive availability</span>
            <strong>{selected.coverage.first_date} → {selected.coverage.last_date}</strong>
          </div>
          <div>
            <span>Selected verified local range</span>
            <strong>{selectedRange ? `${selectedRangeStart} → ${selectedRangeEnd}` : "No verified local range yet."}</strong>
          </div>
          <span>{selected.verified_ranges.length === 0 ? "No verified local range yet." : selected.verified_ranges.map((range) => `${new Date(range.start).toISOString()} → ${new Date(range.end).toISOString()}`).join(" · ")}</span>
        </div>}
        {selected && <div className="symbol-evidence">
          <div><strong>{selected.symbol}</strong><span>Stable dataset identity · EUR quote asset · Spot production history only</span></div>
          <span>{selected.partitions.filter((item) => item.active).length.toLocaleString("en-US")} active monthly partitions</span>
          <span>{selected.total_rows.toLocaleString("en-US")} verified 1m candles</span>
          <span>{formatBytes(selected.stored_bytes)} stored locally</span>
          <span>Pending months: {selected.pending_partition_months.length === 0 ? "none" : selected.pending_partition_months.join(", ")}</span>
          <span>Latest partition identities</span>
          {selected.partitions.filter((item) => item.active).slice(-3).map((partition) => <code key={partition.partition_id}>{partition.partition_id}</code>)}
        </div>}
        <p className="eligibility-note"><strong>Production history and synthetic scenarios remain separate.</strong> These EUR backtests read only verified local production partitions; they never silently fall back to synthetic or Testnet history.</p>
        {selected && selected.verified_ranges.length > 0 && <div className="manifest-card">
          <div><strong>READY FOR SNAPSHOT MANIFESTS</strong><span>{selected.dataset_id}</span></div>
          <span>Dataset identity</span><code>{selected.dataset_id}</code>
          <span>Verified partition identities</span><code>{selected.partitions.filter((item) => item.active).map((item) => item.partition_id).join(", ")}</code>
          {(panel?.blocking_reasons.length ?? 0) > 0 && <p><strong>Blocked:</strong> {panel?.blocking_reasons.join("; ")}</p>}
        </div>}
      </section>
      <section className="production-data" aria-labelledby="adaptive-research-heading">
        <div className="result-heading"><div><p className="eyebrow">Ticket 15 · resumable execution</p><h2 id="adaptive-research-heading">Run adaptive research outside the browser</h2><p>The local service owns execution and SQLite checkpoints. Close this browser, reopen Studio, and reconnect to the same job identity and sealed evidence.</p></div><span className="scope">NO TRADING AUTHORITY</span></div>
        <p className="job-note">This inventory grid is net-long base exposure. The 250 USDT Azure MVP is a validation/learning vehicle, not infrastructure-net-profitable operation.</p>
        <button type="button" disabled={researchJobBusy} onClick={startAdaptiveResearch}>{researchJobBusy ? "Research running…" : "Start adaptive research job"}</button>
        {researchJobs.map((job) => <ResearchJobCard key={job.id} job={job} onCancel={() => cancelAdaptiveResearch(job.id)} />)}
      </section>
      <form onSubmit={submit}>
        <div className="sections">
          <fieldset><legend><b>01</b> Market & Data</legend><label>Symbol<input aria-label="Symbol" value={draft.symbol} onChange={(e) => update("symbol", e.currentTarget.value.toUpperCase())} /></label><label>Market regime<select value={draft.regime} onChange={(e) => update("regime", e.currentTarget.value as Draft["regime"])}>{configuration.data_regimes.map((item) => <option key={item}>{item}</option>)}</select></label><NumberField label="Synthetic bars" min={50} value={draft.bars} onChange={(v) => update("bars", v)} /><NumberField label="Deterministic seed" value={draft.seed} onChange={(v) => update("seed", v)} /></fieldset>
          <fieldset><legend><b>02</b> Grid & Capital</legend><NumberField label="Initial quote capital" min={1} value={draft.initialCash} onChange={(v) => update("initialCash", v)} /><NumberField label="Lower bound" min={0.01} step={0.01} value={draft.lower} onChange={(v) => update("lower", v)} /><NumberField label="Upper bound" min={0.01} step={0.01} value={draft.upper} onChange={(v) => update("upper", v)} /><NumberField label="Configured rung prices" min={2} value={draft.levels} onChange={(v) => update("levels", v)} /><label>Spacing<select value={draft.spacing} onChange={(e) => update("spacing", e.currentTarget.value as Draft["spacing"])}>{configuration.spacing.map((item) => <option key={item}>{item}</option>)}</select></label><NumberField label="Fixed quote per order" min={0.01} step={0.01} value={draft.quoteSize} onChange={(v) => update("quoteSize", v)} /></fieldset>
          <fieldset><legend><b>03</b> Costs & Execution</legend><NumberField label="Maker fee fraction" min={0} step={0.0001} value={draft.makerFee} onChange={(v) => update("makerFee", v)} /><NumberField label="Taker fee fraction" min={0} step={0.0001} value={draft.takerFee} onChange={(v) => update("takerFee", v)} /><p className="note">The backend applies costs and execution semantics. This view does not calculate permission or profitability.</p></fieldset>
          <fieldset><legend><b>04</b> Risk & Evaluation</legend><NumberField label="Global stop-loss fraction" min={0} step={0.01} value={draft.stopLoss} onChange={(v) => update("stopLoss", v)} /><p className="note">Static neutral Spot only. No leverage, shorting, adaptive range, compounding, take-profit, promotion, or online activation is available here.</p></fieldset>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="review"><div><strong>Canonical submission</strong><span>{draft.symbol} · {draft.levels} rung prices · {draft.spacing} · seed {draft.seed}</span></div><button disabled={running} type="submit">{running ? "Running…" : "Run backtest"}</button></div>
      </form>
      {run && <Results run={run} />}
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
