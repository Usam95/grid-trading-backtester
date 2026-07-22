import { useEffect, useState, type FormEvent } from "react";

import type {
  BinanceDatasetPreview,
  DatasetManifest,
  ManifestedBacktestBody,
  ResearchPort,
  RunBacktestBody,
  StudioBacktestRun,
  StudioConfiguration,
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

function formatMoney(value: number): string {
  return `${new Intl.NumberFormat("en", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)} USDT`;
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
  return (
    <section className="results" aria-live="polite">
      <div className="result-heading"><div><p className="eyebrow">Completed research run</p><h2>{run.result.symbol} primary result</h2></div><span className="verdict">{result.verdict}</span></div>
      <div className="metrics">
        <article className="primary"><span>Net return</span><strong>{formatPercent(result.net_return)}</strong></article>
        <article><span>Final equity</span><strong>{formatMoney(result.final_equity)}</strong></article>
        <article><span>Max drawdown</span><strong>{formatPercent(result.max_drawdown)}</strong></article>
        <article><span>Completed trades</span><strong>{result.completed_trades}</strong></article>
        <article><span>Fees paid</span><strong>{formatMoney(result.fees_paid)}</strong></article>
      </div>
      <div className="record"><span>Authoritative local record</span><code>{run.id}</code><span>Saved by the research service · {new Date(run.created_at).toLocaleString()}</span></div>
      {run.provenance && <div className="production-provenance">
        <div><strong>PRODUCTION HISTORY</strong><span>Official Binance Spot archive</span></div>
        <div><strong>TESTNET HISTORY NOT USED</strong><span>Testnet is not profitability evidence</span></div>
        <span>Manifest identity</span><code>{run.provenance.manifest_identity}</code>
        <span>Deterministic backtest fingerprint</span><code>{run.provenance.backtest_fingerprint}</code>
      </div>}
    </section>
  );
}

function ResearchWorkspace({ research }: { research: ResearchPort }) {
  const [configuration, setConfiguration] = useState<StudioConfiguration>();
  const [draft, setDraft] = useState<Draft>();
  const [run, setRun] = useState<StudioBacktestRun>();
  const [error, setError] = useState<string>();
  const [running, setRunning] = useState(false);
  const [productionDate, setProductionDate] = useState("2025-01-01");
  const [preview, setPreview] = useState<BinanceDatasetPreview>();
  const [manifest, setManifest] = useState<DatasetManifest>();
  const [productionBusy, setProductionBusy] = useState(false);

  useEffect(() => {
    let current = true;
    research.getConfiguration().then((value) => {
      if (current) {
        setConfiguration(value);
        setDraft(draftFrom(value));
      }
    }).catch((reason: unknown) => current && setError(reason instanceof Error ? reason.message : "Configuration unavailable"));
    const runId = window.location.hash.match(/experiments\/([^/]+)$/)?.[1];
    if (runId) research.getBacktest(runId).then((value) => current && setRun(value)).catch(() => undefined);
    return () => { current = false; };
  }, [research]);

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

  async function previewProduction() {
    if (!draft) return;
    setProductionBusy(true); setError(undefined); setPreview(undefined); setManifest(undefined);
    try {
      const start = new Date(`${productionDate}T00:00:00Z`);
      const end = new Date(start.getTime() + 86_400_000);
      setPreview(await research.previewProductionDataset({
        symbol: draft.symbol,
        interval: "1m",
        start: start.toISOString(),
        end: end.toISOString(),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Production-data preview failed");
    } finally { setProductionBusy(false); }
  }

  async function importProduction() {
    if (!preview) return;
    setProductionBusy(true); setError(undefined);
    try { setManifest(await research.importProductionDataset(preview.preview_id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Production-data import failed"); }
    finally { setProductionBusy(false); }
  }

  async function runProduction() {
    if (!draft || !manifest) return;
    setProductionBusy(true); setError(undefined);
    try {
      const existing = requestFrom(draft);
      const request: ManifestedBacktestBody = {
        dataset_id: manifest.dataset_id,
        spec: {
          ...existing.spec,
          symbol: draft.symbol,
          market_type: "spot",
          initial_cash: draft.initialCash,
          n_trials: 1,
          data: { kind: "manifested_parquet", dataset_id: manifest.dataset_id },
        },
        options: existing.options,
      };
      const completed = await research.executeManifestedBacktest(request);
      setRun(completed);
      window.history.replaceState(null, "", `#/research/experiments/${completed.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Production backtest failed"); }
    finally { setProductionBusy(false); }
  }

  if (!draft || !configuration) return <main className="workspace"><p>{error ?? "Loading canonical configuration…"}</p></main>;
  const update = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft({ ...draft, [key]: value });
  return (
    <main className="workspace">
      <div className="page-title"><div><p className="eyebrow">Research · Experiments</p><h1>Static grid backtest</h1><p>Configure one deterministic local experiment. The browser submits work; the research service owns the completed record.</p></div><span className="scope">MIGRATED WORKFLOW</span></div>
      <section className="production-data" aria-labelledby="production-data-heading">
        <div className="result-heading"><div><p className="eyebrow">Manifested market evidence</p><h2 id="production-data-heading">Production history</h2><p>Preview one bounded UTC day from the official Binance Spot archive before downloading any archive bytes.</p></div><span className="scope">1m · MAX 1 DAY IN STUDIO</span></div>
        <div className="production-controls">
          <label>UTC archive day<input aria-label="UTC archive day" type="date" value={productionDate} onChange={(event) => setProductionDate(event.currentTarget.value)} /></label>
          <button disabled={productionBusy} type="button" onClick={previewProduction}>Preview official download</button>
        </div>
        {preview && <div className="download-preview">
          <strong>{preview.symbol} · {preview.interval} · {new Date(preview.start).toISOString()} to {new Date(preview.end).toISOString()}</strong>
          <span>{preview.estimated_bytes.toLocaleString("en-US")} bytes</span>
          {preview.sources.map((source) => <div key={source.url}><span>{source.url.split("/").at(-1)}</span><code>{source.expected_sha256}</code></div>)}
          <button disabled={productionBusy} type="button" onClick={importProduction}>Download, verify & normalize</button>
        </div>}
        {manifest && <div className="manifest-card">
          <div><strong>QUALITY APPROVED</strong><span>{manifest.quality.rows.toLocaleString("en-US")} ordered candles · {manifest.quality.gaps} gaps · {manifest.quality.duplicates} duplicates</span></div>
          <span>Manifest identity</span><code>{manifest.dataset_id}</code>
          <span>Normalized Parquet SHA-256</span><code>{manifest.normalization.sha256}</code>
          <p><strong>Production market history supplied this evidence.</strong> Binance Testnet history was not used and is not profitability evidence.</p>
          <button disabled={productionBusy} type="button" onClick={runProduction}>Run production-history backtest</button>
        </div>}
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

function OperationsWorkspace() {
  return <main className="workspace empty"><p className="eyebrow">Operations · Command Center</p><h1>Operations boundary established</h1><p>This workspace is reserved for an authenticated control gateway. Ticket 02 grants no Paper, Testnet, live, or venue command authority.</p><div className="boundary"><strong>GATEWAY NOT CONFIGURED</strong><span>COMMAND AUTHORITY UNAVAILABLE</span><span>No commands are cached or queued by this browser.</span></div></main>;
}

export function App({ research }: { research: ResearchPort }) {
  const [workspace, setWorkspace] = useState<Workspace>("research");
  return <div className="shell"><aside><div className="brand"><span>GRIDLAB</span><strong>Operator Studio</strong></div><div className="workspace-switch"><button aria-label="Research workspace" className={workspace === "research" ? "selected" : ""} onClick={() => setWorkspace("research")}>Research</button><button aria-label="Operations workspace" className={workspace === "operations" ? "selected" : ""} onClick={() => setWorkspace("operations")}>Operations</button></div><Navigation workspace={workspace} /></aside><div className="main"><AuthorityHeader workspace={workspace} />{workspace === "research" ? <ResearchWorkspace research={research} /> : <OperationsWorkspace />}</div></div>;
}
