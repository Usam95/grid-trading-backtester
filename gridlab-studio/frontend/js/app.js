// gridlab studio — main controller.
import { api } from "./api.js";
import { el, clear, fmt, getPath, setPath, debounce, deepClone } from "./format.js";
import {
  toast, kpi, badge, verdictBanner, insightList, section, card, cardWithActions,
  dataTable, metricGrid, emptyState, runButton, infoTip,
  tabbed, trustGauge, meterRow, dataRibbon, numberedStep,
} from "./ui.js";
import { SECTIONS, renderFields, gridLadder, setVenues } from "./schema.js";
import * as charts from "./charts.js";
import { history } from "./history.js";

const state = {
  meta: null,
  spec: null,
  result: null,
  route: "lab",
  research: { tab: "grid-search", lastGS: null, lastWF: null, lastMC: null, wizard: null },
};

const view = document.getElementById("view");

// ---------------------------------------------------------------- bootstrap
async function init() {
  charts.applyChartTheme();
  initTheme();
  try {
    state.meta = await api.meta();
  } catch (e) {
    view.appendChild(emptyState("⚠", "Backend unavailable", "Start it with `python run.py`. " + e.message));
    return;
  }
  state.spec = deepClone(state.meta.default_spec);
  if (state.meta.venues) setVenues(state.meta.venues);
  renderNav();
  go(history.count() > 0 ? "dashboard" : "lab");
}

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: icon("grid"), title: "Performance Overview", sub: "Your portfolio of backtests — aggregated results across every run" },
  { id: "lab", label: "Strategy Lab", icon: icon("flask"), title: "Strategy Lab", sub: "Configure, simulate, and dissect a grid strategy" },
  { id: "research", label: "Research", icon: icon("search"), title: "Research Lab", sub: "Parameter sweeps, walk-forward & Monte-Carlo robustness" },
  { id: "learn", label: "Learn", icon: icon("book"), title: "Grid Trading 101", sub: "When grids work, when they fail, and how to make them robust" },
];

function renderNav() {
  const nav = document.getElementById("nav");
  clear(nav);
  for (const n of NAV) {
    const item = el("button", { class: "nav-item" + (state.route === n.id ? " active" : ""), html: n.icon + `<span>${n.label}</span>` });
    item.addEventListener("click", () => go(n.id));
    nav.appendChild(item);
  }
}

function go(route) {
  state.route = route;
  const n = NAV.find((x) => x.id === route);
  document.getElementById("page-title").textContent = n.title;
  document.getElementById("page-sub").textContent = n.sub;
  clear(document.getElementById("topbar-actions"));
  renderNav();
  charts.destroyAll();
  clear(view);
  if (route === "dashboard") renderDashboard();
  else if (route === "lab") renderLab();
  else if (route === "research") renderResearch();
  else renderLearn();
}

// ============================================================ DASHBOARD VIEW
// Portfolio "Performance Overview": aggregates every saved backtest (localStorage)
// into a single portfolio snapshot, equity curve, leaderboard and history list.
function topbarBtn(label, kind, onClick) {
  const b = el("button", { class: `btn ${kind} btn-sm` }, label);
  b.addEventListener("click", onClick);
  return b;
}

function aggregate(runs) {
  const n = runs.length;
  const sum = (f) => runs.reduce((a, r) => a + (f(r) || 0), 0);
  const mean = (f) => {
    const vals = runs.map(f).filter((v) => v != null && isFinite(v));
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };
  const totalInitial = sum((r) => r.initial_cash);
  const totalFinal = sum((r) => r.final_equity);
  const totalPnL = totalFinal - totalInitial;
  const byRet = runs.filter((r) => r.total_return != null).slice().sort((a, b) => b.total_return - a.total_return);
  const profitable = runs.filter((r) => (r.net_pnl || 0) > 0).length;
  return {
    n,
    totalInitial, totalFinal, totalPnL,
    portfolioReturn: totalInitial ? totalPnL / totalInitial : null,
    avgReturn: mean((r) => r.total_return),
    avgMaxDD: mean((r) => r.max_drawdown),
    avgSharpe: mean((r) => r.sharpe),
    profitableRate: n ? profitable / n : null,
    profitable,
    best: byRet[0] || null,
    worst: byRet[byRet.length - 1] || null,
    totalFees: sum((r) => r.fees_paid),
    totalTrades: sum((r) => r.n_trades),
  };
}

function dashStat(label, value, tone = "", sub) {
  return el("div", { class: "dash-stat" },
    el("div", { class: "ds-label" }, label),
    el("div", { class: "ds-value " + tone }, value),
    sub ? el("div", { class: "ds-sub" }, sub) : null);
}

function renderDashboard() {
  const runs = history.list(); // newest first

  const actions = document.getElementById("topbar-actions");
  actions.appendChild(topbarBtn("+ New backtest", "btn-primary", () => go("lab")));
  if (runs.length) {
    actions.appendChild(topbarBtn("Clear history", "btn-ghost", () => {
      if (confirm(`Delete all ${runs.length} saved backtests? This cannot be undone.`)) {
        history.clear();
        go("dashboard");
        toast("Backtest history cleared", "info");
      }
    }));
  }

  if (!runs.length) {
    const cta = el("button", { class: "btn btn-primary", style: { marginTop: "18px" } }, "Open the Strategy Lab");
    cta.addEventListener("click", () => go("lab"));
    view.appendChild(el("div", { class: "fade-in" },
      el("div", { class: "empty dash-empty" },
        el("div", { class: "big" }, "📊"),
        el("h3", {}, "No backtests yet"),
        el("div", {}, "Run a strategy in the Strategy Lab and it will be saved here automatically — building a portfolio view across every experiment you run."),
        cta)));
    return;
  }

  const chrono = runs.slice().reverse(); // oldest -> newest for the equity curve
  const agg = aggregate(runs);
  const wrap = el("div", { class: "stack fade-in" });

  // --- Row 1: portfolio snapshot + aggregate equity curve ---
  const pnlTone = agg.totalPnL >= 0 ? "pos" : "neg";
  const snapshot = el("div", { class: "card dash-snapshot" },
    el("div", { class: "card-head" }, el("div", {}, el("div", { class: "card-title" }, "Portfolio snapshot"),
      el("div", { class: "card-sub" }, `${agg.n} backtest${agg.n === 1 ? "" : "s"} aggregated`))),
    el("div", { class: "dash-pnl" },
      el("div", { class: "dp-main " + pnlTone }, (agg.totalPnL >= 0 ? "+" : "−") + fmt.money(Math.abs(agg.totalPnL))),
      el("div", { class: "dp-side" },
        el("span", { class: "hero-pill " + pnlTone }, fmt.pctSigned(agg.portfolioReturn)),
        el("div", { class: "dp-cap" }, fmt.money(agg.totalInitial, 0) + " deployed → " + fmt.money(agg.totalFinal, 0)))),
    el("div", { class: "dash-stat-grid" },
      dashStat("Avg return / run", fmt.pctSigned(agg.avgReturn), agg.avgReturn >= 0 ? "pos" : "neg"),
      dashStat("Profitable runs", fmt.pct(agg.profitableRate, 0), agg.profitableRate >= 0.5 ? "pos" : "warnc", `${agg.profitable} of ${agg.n}`),
      dashStat("Avg max drawdown", fmt.pct(agg.avgMaxDD), "neg"),
      dashStat("Avg Sharpe", fmt.ratio(agg.avgSharpe), agg.avgSharpe == null ? "" : agg.avgSharpe >= 1 ? "pos" : ""),
      dashStat("Best run", fmt.pctSigned(agg.best ? agg.best.total_return : null), "pos", agg.best ? agg.best.symbol : ""),
      dashStat("Worst run", fmt.pctSigned(agg.worst ? agg.worst.total_return : null), "neg", agg.worst ? agg.worst.symbol : "")));

  const eqCanvas = el("canvas");
  const eqCard = el("div", { class: "card dash-eq" },
    el("div", { class: "card-head" }, el("div", {}, el("div", { class: "card-title" }, "Aggregate equity curve"),
      el("div", { class: "card-sub" }, "Cumulative capital deployed vs ending portfolio value, in run order"))),
    el("div", { class: "chart-box h-md" }, eqCanvas));

  const row1 = el("div", { class: "dash-row1" }, snapshot, eqCard);
  wrap.appendChild(row1);

  // --- Row 2: leaderboard + latest/best performer ---
  const top = runs.filter((r) => r.total_return != null).slice().sort((a, b) => b.total_return - a.total_return).slice(0, 8);
  const lbCanvas = el("canvas");
  const leaderboard = el("div", { class: "card" },
    el("div", { class: "card-head" }, el("div", {}, el("div", { class: "card-title" }, "Return leaderboard"),
      el("div", { class: "card-sub" }, "Top backtests by total return"))),
    el("div", { class: "chart-box h-md" }, lbCanvas));

  const performers = el("div", { class: "stack" },
    performerCard("Latest backtest", runs[0], "info"),
    agg.best ? performerCard("Best performer", agg.best, "good") : null);

  wrap.appendChild(el("div", { class: "dash-row2" }, leaderboard, performers));

  // --- Row 3: full history ---
  wrap.appendChild(historyCard(runs));

  view.appendChild(wrap);

  // charts mount after the nodes are in the DOM
  requestAnimationFrame(() => {
    charts.aggregateEquityChart(eqCanvas, chrono);
    charts.returnLeaderboardChart(lbCanvas,
      top.map((r) => `${r.symbol} ${fmt.pctSigned(r.total_return)}`),
      top.map((r) => r.total_return));
  });
}

function performerCard(title, r, tone) {
  if (!r) return null;
  const net = r.net_pnl || 0;
  const np = net >= 0 ? "pos" : "neg";
  return el("div", { class: "card performer-card" },
    el("div", { class: "perf-head" },
      el("span", { class: "perf-title" }, title),
      badge(r.strategy, tone)),
    el("div", { class: "perf-symline" },
      el("span", { class: "perf-sym" }, r.symbol),
      el("span", { class: "perf-tf" }, r.interval),
      r.is_real ? badge("real", "good") : badge("synthetic", "warn")),
    el("div", { class: "perf-ret " + (r.total_return >= 0 ? "pos" : "neg") }, fmt.pctSigned(r.total_return)),
    el("div", { class: "perf-rows" },
      perfRow("Net P&L", (net >= 0 ? "+" : "−") + fmt.money(Math.abs(net)), np),
      perfRow("Final value", fmt.money(r.final_equity)),
      perfRow("Max drawdown", fmt.pct(r.max_drawdown), "neg"),
      perfRow("Closed trades", fmt.int(r.n_trades)),
      perfRow("Window", windowLabel(r))),
    openBtn(r));
}

function perfRow(k, v, tone = "") {
  return el("div", { class: "perf-row" }, el("span", { class: "pr-k" }, k), el("span", { class: "pr-v " + tone }, v));
}

function windowLabel(r) {
  if (!r.start || !r.end) return r.bars ? `${fmt.int(r.bars)} bars` : "—";
  return `${fmt.date(r.start)} → ${fmt.date(r.end)}`;
}

function openBtn(r) {
  const b = el("button", { class: "btn btn-ghost btn-sm", style: { marginTop: "12px", width: "100%" } }, "Reload config in Lab");
  b.addEventListener("click", () => reloadRunInLab(r));
  return b;
}

function historyCard(runs) {
  const list = el("div", { class: "dash-history" });
  for (const r of runs) {
    const net = r.net_pnl || 0;
    const row = el("div", { class: "dh-row" },
      el("div", { class: "dh-spark" }, charts.sparklineSVG(r.spark)),
      el("div", { class: "dh-id" },
        el("div", { class: "dh-sym" }, r.symbol, el("span", { class: "dh-tf" }, r.interval)),
        el("div", { class: "dh-strat" }, r.strategy, r.is_real ? "" : " · synthetic")),
      el("div", { class: "dh-win" }, windowLabel(r)),
      el("div", { class: "dh-metric" },
        el("div", { class: "dh-m-v " + (r.total_return >= 0 ? "pos" : "neg") }, fmt.pctSigned(r.total_return)),
        el("div", { class: "dh-m-k" }, "return")),
      el("div", { class: "dh-metric" },
        el("div", { class: "dh-m-v neg" }, fmt.pct(r.max_drawdown)),
        el("div", { class: "dh-m-k" }, "max DD")),
      el("div", { class: "dh-metric" },
        el("div", { class: "dh-m-v" }, fmt.int(r.n_trades)),
        el("div", { class: "dh-m-k" }, "trades")),
      el("div", { class: "dh-metric" },
        el("div", { class: "dh-m-v " + (net >= 0 ? "pos" : "neg") }, (net >= 0 ? "+" : "−") + fmt.money(Math.abs(net), 0)),
        el("div", { class: "dh-m-k" }, "net P&L")),
      verdictPill(r),
      el("div", { class: "dh-actions" },
        iconBtn("Reload config in Lab", "↻", () => reloadRunInLab(r)),
        iconBtn("Delete", "✕", () => {
          history.remove(r.id);
          go("dashboard");
        })));
    list.appendChild(row);
  }
  return cardWithActions("Backtest history", `${runs.length} run${runs.length === 1 ? "" : "s"} saved locally (most recent first)`, [], list);
}

function verdictPill(r) {
  if (r.verdict_score == null) return el("div", { class: "dh-verdict" });
  const toneMap = { good: "pos", info: "warnc", warn: "warnc", bad: "neg" };
  return el("div", { class: "dh-verdict" },
    el("span", { class: "vp " + (toneMap[r.verdict_tone] || "") },
      `${r.verdict_score}/${r.verdict_max || 7}`),
    el("span", { class: "vp-label" }, r.verdict_label || ""));
}

function iconBtn(title, glyph, onClick) {
  const b = el("button", { class: "icon-btn", title }, glyph);
  b.addEventListener("click", onClick);
  return b;
}

// Re-hydrate a saved run's configuration into the Lab (best-effort from summary).
function reloadRunInLab(r) {
  const s = state.spec;
  s.symbol = r.symbol;
  s.data = s.data || {};
  if (r.data_kind) s.data.kind = r.data_kind;
  if (r.interval && r.interval !== "—") s.data.interval = r.interval;
  if (r.symbol) s.data.symbol = r.symbol;
  if (r.venue) s.venue = r.venue;
  s.grid = s.grid || {};
  if (r.direction) s.grid.direction = r.direction;
  if (r.spacing) s.grid.spacing = r.spacing;
  if (r.levels != null) s.grid.levels = r.levels;
  s.grid.adaptive = !!r.adaptive;
  if (r.sizing_mode) { s.sizing = s.sizing || {}; s.sizing.mode = r.sizing_mode; if (r.sizing_value != null) s.sizing.value = r.sizing_value; }
  state.result = null;
  go("lab");
  toast(`Loaded ${r.symbol} ${r.strategy} into the Lab — press Run to re-test`, "info");
}


// ================================================================ LAB VIEW
function renderLab() {
  const layout = el("div", { class: "lab-layout fade-in" });
  const left = el("div", { class: "stack" });
  const right = el("div", { class: "stack", id: "results" });

  left.appendChild(presetCard());
  left.appendChild(configCard());

  if (state.result) right.appendChild(dashboard(state.result));
  else right.appendChild(previewPanel());

  layout.appendChild(left);
  layout.appendChild(right);
  view.appendChild(layout);
  refreshPreview();
}

function previewPanel() {
  // Right-column live preview shown before the first run: the grid ladder, a
  // cost-edge check, and the run context. Sticky so it stays visible while the
  // config form scrolls.
  return el("div", { class: "preview-sticky" },
    card("Grid Preview",
      "Live ladder & cost check for the current configuration — before you spend a run.",
      el("div", { id: "ladder" }, el("div", { class: "skel", style: { height: "150px" } })),
      el("div", { id: "preview-stats", class: "preview-stats" }),
      el("div", { class: "preview-context-head" }, "Run context"),
      el("dl", { id: "preview-context", class: "preview-context" })));
}

function presetCard() {
  const grid = el("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "9px" } });
  for (const p of state.meta.presets) {
    const c = el("button", { class: "preset-card" },
      el("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: "6px" } },
        el("div", { class: "preset-name" }, p.name),
        badge(p.badge, "info")),
      el("div", { class: "preset-tag" }, p.tagline));
    c.addEventListener("click", () => {
      state.spec = deepClone(p.spec);
      // ensure all spec branches exist
      go("lab");
      toast(`Loaded preset: ${p.name}`, "info");
    });
    grid.appendChild(c);
  }
  return card("Presets", "Curated starting points — click to load", grid);
}

// Four guided steps (saas-style numbered wizard) grouping the engine sections.
const STEPS = [
  { title: "Market & Data", sub: "What you trade and the price history to test on", sections: ["asset", "data"] },
  { title: "Venue & Costs", sub: "Real exchange fees, spread and market impact", sections: ["venue"] },
  { title: "Grid Configuration", sub: "Ladder geometry and how each rung is sized", sections: ["grid", "sizing"] },
  { title: "Risk & Execution", sub: "Entry filters, stops, inventory caps and fill model", sections: ["filters", "advanced"] },
];

function configCard() {
  const body = el("div", { class: "config-steps" });
  const onChange = debounce(() => refreshPreview(), 280);
  STEPS.forEach((step, idx) => {
    const stepBody = el("div");
    step.sections.forEach((secId) => {
      const sec = SECTIONS.find((s) => s.id === secId);
      if (!sec) return;
      if (step.sections.length > 1) stepBody.appendChild(el("div", { class: "step-subhead" }, `${sec.icon}  ${sec.title}`));
      const fieldsWrap = el("div", { dataset: { sec: sec.id } });
      const renderInto = () => {
        clear(fieldsWrap);
        // Re-render the group so showIf toggles (e.g. adaptive) take effect.
        fieldsWrap.appendChild(renderFields(sec.fields, state.spec, () => { renderInto(); onChange(); }));
      };
      renderInto();
      stepBody.appendChild(fieldsWrap);
    });
    body.appendChild(numberedStep(idx + 1, step.title, step.sub, stepBody));
  });

  const runBtn = runButton("⚡ Run Backtest", runBacktest);
  runBtn.classList.add("btn-block");
  const actions = el("div", { class: "stack", style: { gap: "10px", marginTop: "6px" } }, runBtn,
    el("div", { style: { display: "flex", gap: "8px" } },
      el("button", { class: "btn btn-ghost btn-sm", style: { flex: "1" }, onclick: copySpec }, "Copy JSON"),
      el("button", { class: "btn btn-ghost btn-sm", style: { flex: "1" }, onclick: downloadReport }, "⬇ HTML report")));

  return cardWithActions("Configuration", "Set up your grid in four steps", [], body, actions);
}

const refreshPreview = debounce(async () => {
  const target = document.getElementById("ladder");
  if (!target) return; // results are showing instead of the preview
  let grid = null;
  try {
    grid = await api.gridPreview(specForRun());
    clear(target).appendChild(gridLadder(grid));
  } catch (e) {
    clear(target).appendChild(el("div", { class: "text-mute", style: { fontSize: "12px" } }, "Preview unavailable: " + e.message));
  }
  const stats = document.getElementById("preview-stats");
  if (stats) clear(stats).appendChild(previewStats(grid));
  const ctx = document.getElementById("preview-context");
  if (ctx) clear(ctx).appendChild(previewContext());
}, 200);

// ---- live preview stats: the cost-edge check before spending a run --------
function previewStats(grid) {
  const spec = state.spec;
  const cap = getPath(spec, "initial_cash") || 0;
  const levels = grid && grid.levels ? grid.levels.length : (getPath(spec, "grid.levels") || 0);
  const makerPct = (getPath(spec, "fees.maker") || 0) * 100;
  const takerPct = (getPath(spec, "fees.taker") || 0) * 100;
  const roundTrip = makerPct + takerPct;
  const spacingPct = grid && !grid.error && grid.spacing_pct != null ? grid.spacing_pct * 100 : null;
  const netEdge = spacingPct != null ? spacingPct - roundTrip : null;
  const capPerLevel = levels > 0 ? cap / levels : 0;

  const tile = (label, val, note, tone = "", tip) =>
    el("div", { class: "preview-stat" },
      el("div", { class: "ps-label" }, label, tip ? infoTip(tip) : null),
      el("div", { class: "ps-val " + tone }, val),
      el("div", { class: "ps-note" }, note));

  const edgeTone = netEdge == null ? "" : netEdge > 0 ? "pos" : "neg";
  const frag = document.createDocumentFragment();
  frag.appendChild(tile("Net edge / cycle",
    netEdge == null ? "—" : (netEdge > 0 ? "+" : "") + netEdge.toFixed(3) + "%",
    netEdge == null ? "set a static range to preview" : netEdge > 0 ? "clears fees per round-trip" : "loses to fees per round-trip",
    edgeTone,
    "Grid spacing minus the maker+taker round-trip fee. If this is negative, every completed buy→sell cycle loses money before any market move — widen spacing or cut fees."));
  frag.appendChild(tile("Grid spacing", spacingPct == null ? "—" : spacingPct.toFixed(3) + "%", "between adjacent rungs"));
  frag.appendChild(tile("Round-trip cost", roundTrip.toFixed(3) + "%", "maker + taker fee"));
  frag.appendChild(tile("Capital / rung", fmt.money(capPerLevel), `${levels || "—"} rungs, even split`));
  return frag;
}

function venueName(id) {
  const v = (state.meta.venues || []).find((x) => x.id === id);
  return v ? v.name : id;
}

function previewContext() {
  const spec = state.spec;
  const kind = getPath(spec, "data.kind") || "synthetic";
  const venue = getPath(spec, "venue");
  let source, bars, barsLabel;
  if (kind === "binance") {
    source = `Binance ${getPath(spec, "data.symbol") || getPath(spec, "symbol") || ""} · ${getPath(spec, "data.interval") || "1h"}`;
    bars = getPath(spec, "data.max_candles");
    barsLabel = "Candles";
  } else {
    source = `Synthetic · ${getPath(spec, "data.regime") || "range"}`;
    bars = getPath(spec, "data.n");
    barsLabel = "Bars";
  }
  const frag = document.createDocumentFragment();
  const row = (k, v, cls = "") => {
    frag.appendChild(el("dt", {}, k));
    frag.appendChild(el("dd", { class: cls }, v));
  };
  row("Data source", source);
  row(barsLabel, bars != null ? fmt.int(bars) : "—");
  row("Venue", venue ? venueName(venue) : "—");
  row("Realism", kind === "binance" ? "Real market data" : "Synthetic", kind === "binance" ? "pos" : "warnc");
  return frag;
}

function specForRun() {
  // JSON round-trip drops undefined leaves so engine defaults apply.
  return JSON.parse(JSON.stringify(state.spec));
}

async function runBacktest() {
  try {
    const spec = specForRun();
    const result = await api.backtest(spec, { include_trades: true });
    state.result = result;
    try { history.add(result, spec); } catch (e) { /* history is best-effort */ }
    const r = document.getElementById("results");
    clear(r).appendChild(dashboard(result));
    toast(`Backtest complete — ${fmt.pctSigned(result.metrics.total_return)} return · saved to Dashboard`, result.metrics.total_return >= 0 ? "good" : "bad");
  } catch (e) {
    toast("Backtest failed: " + e.message, "bad", 6000);
  }
}

async function copySpec() {
  await navigator.clipboard.writeText(JSON.stringify(specForRun(), null, 2));
  toast("Spec JSON copied to clipboard", "good");
}

async function downloadReport() {
  try { toast("Generating report…", "info"); await api.downloadReport(specForRun()); }
  catch (e) { toast("Report failed: " + e.message, "bad"); }
}

// ---- saas-style headline hero cards --------------------------------------
function miniStat(k, v, tone = "") {
  return el("div", { class: "mini-stat" },
    el("div", { class: "ms-k" }, k),
    el("div", { class: "ms-v " + tone }, v));
}
function heroRow(k, v, tone = "") {
  return el("div", { class: "hero-row" },
    el("span", { class: "hr-k" }, k),
    el("span", { class: "hr-v " + tone }, v));
}

function heroCards(r) {
  const m = r.metrics || {};
  const initial = r.initial_cash || 0;
  const finalEq = r.final_equity || 0;
  const net = finalEq - initial;
  const retPct = m.total_return;
  const trades = r.n_closed_trades || 0;
  const wr = m.win_rate;
  const wins = wr != null ? Math.round(wr * trades) : null;
  const losses = wins != null ? trades - wins : null;
  const pf = m.profit_factor;

  const grid = el("div", { class: "hero-grid" });

  // 1 — Final portfolio value (colored top border)
  grid.appendChild(el("div", { class: "hero-card " + (net >= 0 ? "pos-top" : "neg-top") },
    el("div", { class: "hero-label" }, "Final portfolio value"),
    el("div", { class: "hero-value" }, fmt.money(finalEq)),
    el("div", { class: "hero-meta" },
      el("span", { class: net >= 0 ? "pos" : "neg", style: { fontWeight: 700 } }, (net >= 0 ? "▲ " : "▼ ") + fmt.money(net)),
      el("span", { class: "hero-pill " + (retPct >= 0 ? "pos" : "neg") }, fmt.pctSigned(retPct))),
    el("div", { class: "hero-foot" }, "Started with " + fmt.money(initial))));

  // 2 — Trade performance
  grid.appendChild(el("div", { class: "hero-card" },
    el("div", { class: "hero-label" }, "Trade performance"),
    el("div", { class: "hero-split" },
      el("div", {}, el("div", { class: "hero-num" }, fmt.int(trades)), el("div", { class: "hero-sub" }, "Closed trades")),
      el("div", {}, el("div", { class: "hero-num " + (wr >= 0.5 ? "pos" : "neg") }, wr == null ? "—" : fmt.pct(wr, 1)), el("div", { class: "hero-sub" }, "Win rate"))),
    el("div", { class: "hero-mini-grid" },
      miniStat("Winning", wins == null ? "—" : fmt.int(wins), "pos"),
      miniStat("Losing", losses == null ? "—" : fmt.int(losses), "neg"))));

  // 3 — Risk snapshot
  grid.appendChild(el("div", { class: "hero-card" },
    el("div", { class: "hero-label" }, "Risk snapshot"),
    el("div", { class: "hero-rows" },
      heroRow("Max drawdown", fmt.pct(m.max_drawdown), "neg"),
      heroRow("Profit factor", fmt.ratio(pf), pf == null ? "" : pf >= 1 ? "pos" : "neg"),
      heroRow("Avg trade PnL", fmt.money(m.avg_trade_pnl), m.avg_trade_pnl == null ? "" : m.avg_trade_pnl >= 0 ? "pos" : "neg"),
      heroRow("Fees paid", fmt.money(r.fees_paid)))));

  return grid;
}

// ---------------------------------------------------------------- dashboard tabs
function dashboard(r) {
  const wrap = el("div", { class: "stack fade-in" });
  const meta = state.meta.metric_meta;
  charts.destroyAll();

  const warn = resultWarnings(r);
  if (warn) wrap.appendChild(warn);

  // --- compact results header: data ribbon + verdict + saas-style hero cards ---
  const header = el("div", { class: "results-header" });
  const ribbon = dataRibbon(r.data_source);
  if (ribbon) header.appendChild(ribbon);
  header.appendChild(verdictBanner(r.verdict, r));
  header.appendChild(heroCards(r));
  wrap.appendChild(header);

  // --- tabbed body (kills the endless scroll) ---
  wrap.appendChild(tabbed([
    { id: "overview", label: "Overview", render: () => overviewTab(r, meta) },
    { id: "performance", label: "Performance", render: () => performanceTab(r) },
    { id: "economics", label: "Economics", render: () => economicsTab(r, meta) },
    { id: "trades", label: "Trades", badge: r.n_closed_trades, render: () => tradesTab(r, meta) },
    { id: "robustness", label: "Robustness", render: () => robustnessTab(r) },
    { id: "metrics", label: "All metrics", render: () => card("All Metrics", "Hover the ? for definitions", metricGrid(r.metrics, meta)) },
  ]));
  return wrap;
}

function resultWarnings(r) {
  if (!(r.liquidated || (r.rejections && Object.keys(r.rejections).length))) return null;
  const msgs = [];
  if (r.liquidated) msgs.push("Position was liquidated during the run.");
  if (r.rejections && Object.keys(r.rejections).length) {
    const tot = Object.values(r.rejections).reduce((a, b) => a + b, 0);
    msgs.push(`${tot} orders rejected (${Object.entries(r.rejections).map(([k, v]) => `${k}: ${v}`).join(", ")}).`);
  }
  return el("div", { class: "insight bad" },
    el("span", { class: "ico", style: { color: "var(--neg)", fontWeight: "800" } }, "!"),
    el("span", {}, msgs.join(" ")));
}

// ---- Overview tab: the at-a-glance read ----------------------------------
function overviewTab(r, meta) {
  const benchCanvas = el("canvas");
  const node = el("div", { class: "stack" },
    el("div", { class: "grid-2" },
      card("What this means", "Plain-English read of the results", insightList(r.insights)),
      card("Benchmarks", "Return vs passive baselines",
        el("div", {},
          el("div", { class: "chart-box h-sm" }, benchCanvas),
          el("dl", { class: "kv", style: { marginTop: "12px" } },
            el("dt", {}, "Final equity"), el("dd", {}, fmt.money(r.final_equity)),
            el("dt", {}, "Realized PnL"), el("dd", {}, fmt.money(r.realized_pnl)),
            el("dt", {}, "Fees paid"), el("dd", {}, fmt.money(r.fees_paid)),
            el("dt", {}, "Net vs Buy & Hold"),
            el("dd", { class: toneClass(r.metrics.return_over_buy_hold, "high") },
              fmt.pctSigned(r.metrics.return_over_buy_hold)))))),
    econHighlights(r, meta));
  node.__mount = () => charts.compareChart(benchCanvas, ["Grid", "Buy & Hold", "DCA"],
    [r.metrics.total_return, r.benchmarks.buy_and_hold.total_return, r.benchmarks.dca.total_return]);
  return node;
}

function econHighlights(r, meta) {
  const keys = ["return_over_buy_hold", "fee_to_profit_ratio", "avg_capital_utilization", "trades_per_day"];
  const grid = el("div", { class: "econ-tiles" });
  for (const k of keys) {
    const m = meta[k];
    if (!m) continue;
    const v = r.metrics[k];
    const rd = econRead(k, v);
    grid.appendChild(el("div", { class: "econ-tile" },
      el("div", { class: "econ-label" }, m.label, infoTip(m.help)),
      el("div", { class: "econ-val " + rd.tone }, fmt.metric(v, m.fmt)),
      el("div", { class: "econ-read" }, rd.read)));
  }
  return card("Money signals", "The few numbers that decide whether this earns", grid);
}

function econRead(key, v) {
  if (v == null) return { tone: "", read: "—" };
  if (key === "return_over_buy_hold")
    return v > 0.02 ? { tone: "pos", read: "beats just holding" }
      : v >= -0.005 ? { tone: "warnc", read: "roughly matches holding" }
      : { tone: "neg", read: "holding would win" };
  if (key === "fee_to_profit_ratio")
    return v < 0.3 ? { tone: "pos", read: "fees under control" }
      : v < 0.6 ? { tone: "warnc", read: "fees eating the edge" }
      : v < 1 ? { tone: "warnc", read: "fees dominate the edge" }
      : { tone: "neg", read: "fees ate the edge" };
  if (key === "avg_capital_utilization")
    return v < 0.15 ? { tone: "warnc", read: "mostly idle cash" }
      : v > 0.85 ? { tone: "warnc", read: "little dry powder" }
      : { tone: "pos", read: "well deployed" };
  if (key === "trades_per_day")
    return v > 20 ? { tone: "warnc", read: "very fee-exposed" }
      : v < 0.2 ? { tone: "", read: "rarely trades" }
      : { tone: "", read: "moderate turnover" };
  return { tone: "", read: "" };
}

// ---- Performance tab: the charts -----------------------------------------
function performanceTab(r) {
  const eqCanvas = el("canvas");
  const priceCanvas = el("canvas");
  const ddCanvas = el("canvas");
  const node = el("div", { class: "stack" },
    cardWithActions("Equity Curve", "Grid vs Buy & Hold vs DCA",
      [el("button", { class: "btn btn-ghost btn-sm", onclick: downloadReport }, "⬇ Report")],
      el("div", { class: "chart-box h-lg" }, eqCanvas),
      legend([["Grid equity", "var(--brand-2)"], ["Buy & Hold", "var(--text-mute)"], ["DCA", "var(--brand-3)"]])),
    el("div", { class: "grid-2" },
      card("Price & Grid Ladder", "Rungs with entry/exit markers",
        el("div", { class: "chart-box h-md" }, priceCanvas),
        legend([["Price", "var(--brand-3)"], ["Buy rung", "rgba(34,197,94,.6)"], ["Sell rung", "rgba(244,63,94,.6)"]])),
      card("Drawdown", "Underwater equity (% from peak)", el("div", { class: "chart-box h-md" }, ddCanvas))));
  node.__mount = () => {
    charts.equityChart(eqCanvas, r.series);
    charts.priceGridChart(priceCanvas, r.series, r.grid, r.trades);
    charts.drawdownChart(ddCanvas, r.series);
  };
  return node;
}

// ---- Economics tab: where the money comes from + leaks out ---------------
function economicsTab(r, meta) {
  const keys = state.meta.economics_metrics || [
    "return_over_buy_hold", "fee_to_profit_ratio", "avg_capital_utilization",
    "trades_per_day", "avg_round_trip_bps", "time_in_market_frac", "realized_grid_pnl", "fee_drag"];
  return el("div", { class: "stack" },
    card("Grid Economics", "Spot grids earn the spread between rungs — and bleed it back in fees. These are the numbers that decide net profitability.",
      metricGrid(r.metrics, meta, keys)),
    card("How to read this", null, insightList(r.insights.filter((i) =>
      /fee|capital|round-trip|day|hold|synthetic/i.test(i.text)))));
}

// ---- Trades tab ----------------------------------------------------------
function tradesTab(r, meta) {
  const histCanvas = el("canvas");
  const node = el("div", { class: "stack" },
    el("div", { class: "grid-2" },
      card("Trade PnL Distribution", `${fmt.int(r.n_closed_trades)} closed trades`,
        el("div", { class: "chart-box h-md" }, histCanvas)),
      tradeStatsCard(r, meta)),
    tradesCard(r));
  node.__mount = () => {
    const pnls = r.trades.map((t) => t.pnl).filter((v) => v != null);
    const hist = histogram(pnls, 30);
    charts.histogramChart(histCanvas, hist.centers, hist.counts, { unit: "trades", color: "var(--brand-1)" });
  };
  return node;
}

// ---- Robustness tab: the deployment trust score (run on demand) ----------
function robustnessTab(r) {
  const slot = el("div");
  const runBtn = runButton("🛡 Run trust analysis", async () => {
    try {
      const rep = await api.robustness(specForRun(), robustSpace(), 3, 800);
      clear(slot).appendChild(robustnessResult(rep));
    } catch (e) { toast("Robustness failed: " + e.message, "bad", 6000); }
  });
  return el("div", { class: "stack" },
    card("Deployment Trust Score",
      "Before risking capital: re-optimise and re-test this config across multiple time splits, then stress it.",
      el("div", {},
        el("ul", { class: "trust-explain" },
          el("li", {}, el("b", {}, "Out-of-sample"), " — walk-forward: do re-optimised params hold up on unseen data?"),
          el("li", {}, el("b", {}, "Overfit guard"), " — deflated Sharpe: discounts the edge for how many configs were tried."),
          el("li", {}, el("b", {}, "Path risk"), " — Monte-Carlo trade reshuffle: does it survive alternate orderings?")),
        el("p", { class: "text-mute", style: { fontSize: "12.5px" } },
          "Runs a small sweep around your current grid levels and order size. Takes ~10-60s on real data."),
        runBtn)),
    slot);
}

function robustSpace() {
  const lv = Math.round(getPath(state.spec, "grid.levels") || 12);
  const sz = getPath(state.spec, "sizing.value") || 60;
  const uniq = (a) => [...new Set(a)];
  return {
    "grid.levels": uniq([Math.max(4, lv - 4), lv, lv + 4]),
    "sizing.value": uniq([+(sz * 0.75).toFixed(4), sz, +(sz * 1.25).toFixed(4)]),
  };
}

function robustnessResult(rep) {
  const c = rep.components || {};
  const num = (x) => (x == null || typeof x === "object" ? null : x);
  const score = (comp) => (comp && typeof comp === "object" ? num(comp.score) : num(comp));
  const oos = c.out_of_sample || {}, ov = c.overfitting || {}, pr = c.path_risk || {};
  const notes = (rep.notes || []).map((n) => (typeof n === "string" ? { tone: "info", text: n } : n));

  const oosNote = oos.n_folds != null
    ? `${oos.positive_oos_folds ?? "?"}/${oos.n_folds} folds profitable out-of-sample · mean OOS ${fmt.pctSigned(oos.mean_oos_return)}`
    : null;
  const ovNote = ov.deflated_sharpe != null
    ? `Deflated Sharpe ${fmt.num(ov.deflated_sharpe, 2)} (raw ${fmt.num(ov.sharpe, 2)}, ${ov.n_trials ?? "?"} configs tried)`
    : null;
  const prNote = pr.prob_loss != null
    ? `${fmt.pct(pr.prob_loss)} of Monte-Carlo paths lost money · worst drawdown ${fmt.pct(pr.worst_max_drawdown)}`
    : null;

  return el("div", { class: "stack", style: { marginTop: "14px" } },
    card("Trust scorecard", rep.grade,
      el("div", { class: "trust-row" },
        trustGauge(rep.trust_score, rep.grade),
        el("div", { class: "stack", style: { flex: "1", gap: "14px", minWidth: "240px" } },
          meterRow("Out-of-sample", score(c.out_of_sample), {
            tip: "Walk-forward: how re-optimised params held up on unseen data.", note: oosNote }),
          meterRow("Overfit guard", score(c.overfitting), {
            tip: "Deflated Sharpe — discounts for the number of configs tried.", note: ovNote }),
          meterRow("Path risk", score(c.path_risk), {
            tip: "Monte-Carlo trade reshuffle — survival across alternate orderings.", note: prNote })))),
    notes.length ? card("Notes", null, insightList(notes)) : null);
}

function kpiFor(key, r, meta) {
  const m = meta[key];
  const v = r.metrics[key];
  let tone = "";
  if (m.good === "high" && v != null) tone = v > 0 ? "pos" : v < 0 ? "neg" : "";
  if (m.good === "low" && v != null) tone = v <= 0 ? "pos" : "neg";
  let sub = "";
  if (key === "total_return") {
    sub = `Buy & Hold ${fmt.pctSigned(r.benchmarks.buy_and_hold.total_return)}`;
  } else if (key === "return_over_buy_hold") {
    tone = v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
    sub = `Grid ${fmt.pctSigned(r.metrics.total_return)} vs B&H ${fmt.pctSigned(r.benchmarks.buy_and_hold.total_return)}`;
  } else if (key === "max_drawdown") {
    sub = `${fmt.int(r.metrics.max_drawdown_duration)} bars underwater`;
  } else if (key === "sharpe") {
    sub = `Sortino ${fmt.ratio(r.metrics.sortino)}`;
  } else if (key === "fee_to_profit_ratio") {
    tone = v == null ? "" : v < 0.3 ? "pos" : v < 0.6 ? "" : "neg";
    sub = `${fmt.money(r.fees_paid)} fees paid`;
  } else if (key === "win_rate") {
    sub = `Expectancy ${fmt.money(r.metrics.expectancy)}`;
  } else if (key === "n_trades") {
    sub = `${fmt.num(r.metrics.avg_bars_held, 1)} avg bars held`;
  } else if (key === "fee_drag") {
    sub = `${fmt.money(r.fees_paid)} fees paid`;
  } else if (key === "deflated_sharpe") {
    sub = "overfit-adjusted";
  } else if (key === "profit_factor") {
    sub = `Calmar ${fmt.ratio(r.metrics.calmar)}`;
  }
  return kpi({ label: m.label, value: fmt.metric(v, m.fmt), sub, tone, tip: m.help });
}

function toneClass(v, good) {
  if (v == null) return "";
  if (good === "high") return v > 0 ? "pos" : v < 0 ? "neg" : "";
  if (good === "low") return v <= 0 ? "pos" : "neg";
  return "";
}

function tradeStatsCard(r, meta) {
  const m = r.metrics;
  const order = ["win_rate", "profit_factor", "avg_win", "avg_loss", "largest_win", "largest_loss", "expectancy", "avg_bars_held"];
  return card("Trade Statistics", "Quality of the round-trips", metricGrid(m, meta, order));
}

function tradesCard(r) {
  const cols = [
    { key: "side", label: "Side", fmt: (t) => badge(t.side, t.side === "LONG" ? "good" : "bad") },
    { key: "entry_price", label: "Entry", align: "right", fmt: (t) => fmt.price(t.entry_price) },
    { key: "exit_price", label: "Exit", align: "right", fmt: (t) => fmt.price(t.exit_price) },
    { key: "qty", label: "Qty", align: "right", fmt: (t) => fmt.num(t.qty, 4) },
    { key: "pnl", label: "PnL", align: "right", fmt: (t) => el("span", { class: t.pnl >= 0 ? "pos" : "neg" }, fmt.money(t.pnl)) },
    { key: "return_pct", label: "Return", align: "right", fmt: (t) => el("span", { class: t.return_pct >= 0 ? "pos" : "neg" }, fmt.pctSigned(t.return_pct)) },
    { key: "bars_held", label: "Bars", align: "right", fmt: (t) => fmt.int(t.bars_held) },
    { key: "exit_reason", label: "Exit", fmt: (t) => t.exit_reason || "—" },
  ];
  return card("Trade Log", `Showing ${fmt.int(r.trades.length)} of ${fmt.int(r.n_closed_trades)} trades — click a header to sort`,
    dataTable(cols, r.trades, { scroll: true, sortKey: "pnl", sortDir: -1 }));
}

// ================================================================ RESEARCH
function renderResearch() {
  const tabs = ["grid-search", "walk-forward", "monte-carlo"];
  const labels = { "grid-search": "Parameter Sweep", "walk-forward": "Walk-Forward", "monte-carlo": "Monte Carlo" };
  const seg = el("div", { class: "segment", style: { maxWidth: "440px", marginBottom: "18px" } });
  for (const t of tabs) {
    const b = el("button", { type: "button" }, labels[t]);
    if (state.research.tab === t) b.classList.add("on");
    b.addEventListener("click", () => { state.research.tab = t; renderResearch(); });
    seg.appendChild(b);
  }
  charts.destroyAll();
  clear(view);
  const base = el("div", { class: "fade-in" }, seg,
    el("div", { class: "insight info", style: { marginBottom: "18px" } },
      el("span", { class: "ico", style: { color: "var(--info)" } }, "ℹ"),
      el("span", {}, "Research runs use your current Strategy Lab configuration as the base spec.")));
  view.appendChild(base);
  if (state.research.tab === "grid-search") base.appendChild(gridSearchPanel());
  else if (state.research.tab === "walk-forward") base.appendChild(walkForwardPanel());
  else base.appendChild(monteCarloPanel());
}

// ---- Research Wizard: guided parameter sweep builder ---------------------
// Adapts the saas multi-step "search space" wizard to gridlab's spot params.
// Builds the same {dotted.path:[values]} space the backend grid-search expects,
// with a live, conditional-aware experiment-size counter.

// shared value parser (also used by walk-forward / monte-carlo axis pickers)
function parseValues(str) {
  return String(str).split(",").map((s) => s.trim()).filter(Boolean).map((s) => (isNaN(Number(s)) ? s : Number(s)));
}

// simple single-axis picker retained for walk-forward / monte-carlo panels
const SWEEPABLE = [
  { path: "grid.levels", label: "Grid levels", ex: "8, 12, 16, 20" },
  { path: "sizing.value", label: "Order size", ex: "40, 60, 80, 100" },
  { path: "grid.spacing", label: "Spacing", ex: "arithmetic, geometric" },
  { path: "grid.atr_mult", label: "ATR multiple", ex: "1.5, 2, 2.5, 3" },
  { path: "fees.taker", label: "Taker fee", ex: "0.0002, 0.0005, 0.001" },
  { path: "slippage.impact_frac", label: "Slippage", ex: "0, 0.0005, 0.001" },
  { path: "grid.direction", label: "Direction", ex: "neutral, long" },
  { path: "grid.recenter_drift_frac", label: "Recenter drift", ex: "0, 0.1, 0.2" },
];
function axisPicker(defPath, defVals) {
  const sel = el("select");
  sel.appendChild(el("option", { value: "" }, "— none —"));
  for (const s of SWEEPABLE) {
    const o = el("option", { value: s.path }, s.label);
    if (s.path === defPath) o.selected = true;
    sel.appendChild(o);
  }
  const vals = el("input", { type: "text", placeholder: "comma-separated, e.g. 8, 12, 20", value: defVals || "" });
  sel.addEventListener("change", () => {
    const s = SWEEPABLE.find((x) => x.path === sel.value);
    if (s && !vals.value) vals.value = s.ex;
  });
  return { node: el("div", { class: "field-row" }, el("div", { class: "field" }, el("label", { class: "lbl" }, "Parameter"), sel), el("div", { class: "field" }, el("label", { class: "lbl" }, "Values"), vals)), sel, vals };
}

const SWEEP_PARAMS = [
  { path: "grid.levels", label: "Grid levels", group: "Grid geometry", kind: "int", ex: [8, 12, 16, 20], hint: "Number of rungs. More rungs = tighter spacing, more trades & fees." },
  { path: "grid.spacing", label: "Spacing mode", group: "Grid geometry", kind: "enum", options: () => state.meta.enums.spacing, hint: "How the gap between rungs scales: arithmetic, geometric or ATR-based." },
  { path: "grid.atr_mult", label: "ATR multiple", group: "Grid geometry", kind: "float", ex: [1.5, 2, 2.5, 3], hint: "Rung width measured in ATRs. Only used when spacing is ATR-based.", requires: { path: "grid.spacing", value: "atr" } },
  { path: "grid.direction", label: "Direction", group: "Grid geometry", kind: "enum", options: () => state.meta.enums.direction, hint: "Spot grids run neutral (both sides) or long-only." },
  { path: "sizing.value", label: "Order size", group: "Capital & sizing", kind: "float", ex: [40, 60, 80, 100], hint: "Quote spent per rung (or equity fraction in percent mode)." },
  { path: "grid.recenter_drift_frac", label: "Recenter drift", group: "Dynamic movement", kind: "float", ex: [0, 0.1, 0.2], hint: "Re-center the grid after price drifts this far. Adaptive grids only." },
  { path: "fees.taker", label: "Taker fee", group: "Costs & robustness", kind: "float", ex: [0.0002, 0.0005, 0.001], hint: "Stress-test how sensitive the edge is to trading fees." },
  { path: "slippage.impact_frac", label: "Slippage", group: "Costs & robustness", kind: "float", ex: [0, 0.0005, 0.001], hint: "Per-fill price impact as a fraction of price." },
];
const BUDGET_WARN = 120;
const BUDGET_SOFT = 400;
const WIZ_STEPS = ["Search space", "Objective & budget", "Review & run"];

function initWizard() {
  if (state.research.wizard) return state.research.wizard;
  const params = {};
  for (const p of SWEEP_PARAMS) params[p.path] = { mode: "fixed", list: "", range: { start: "", stop: "", step: "" }, set: [] };
  params["grid.levels"] = { mode: "list", list: "8, 12, 16, 20", range: { start: "", stop: "", step: "" }, set: [] };
  params["sizing.value"] = { mode: "list", list: "40, 60, 80", range: { start: "", stop: "", step: "" }, set: [] };
  state.research.wizard = { step: 1, objective: state.meta.objectives[0], top_k: 20, params };
  return state.research.wizard;
}

function rangeValues(r) {
  const a = Number(r.start), b = Number(r.stop), s = Number(r.step);
  if (![a, b, s].every(isFinite) || s <= 0 || b < a) return [];
  const out = [];
  const eps = s / 1000;
  for (let v = a; v <= b + eps; v += s) { out.push(+v.toFixed(8)); if (out.length > 500) break; }
  return out;
}
function paramValues(p, cfg) {
  if (cfg.mode === "list") return parseValues(cfg.list);
  if (cfg.mode === "range") return rangeValues(cfg.range);
  if (cfg.mode === "set") return cfg.set.slice();
  return [];
}
function requireMet(p, model) {
  if (!p.requires) return true;
  const req = p.requires;
  const reqCfg = model.params[req.path];
  if (reqCfg.mode === "fixed") return getPath(specForRun(), req.path) === req.value;
  return paramValues(SWEEP_PARAMS.find((x) => x.path === req.path), reqCfg).includes(req.value);
}
function analyzeModel(model) {
  const space = {};
  const ignored = [];
  for (const p of SWEEP_PARAMS) {
    const cfg = model.params[p.path];
    if (cfg.mode === "fixed") continue;
    const vals = paramValues(p, cfg);
    if (!vals.length) continue;
    if (!requireMet(p, model)) { ignored.push(p); continue; }
    space[p.path] = vals;
  }
  const axes = Object.keys(space);
  const n = axes.length ? Object.values(space).reduce((a, v) => a * v.length, 1) : 0;
  return { space, ignored, axes, n };
}

function gridSearchPanel() {
  const model = initWizard();
  const wrap = el("div", { class: "stack wizard" });
  const main = el("div", { class: "wizard-main", id: "wiz-main" });
  const rail = el("div", { class: "wizard-rail", id: "wiz-rail" });
  wrap.appendChild(stepperHeader(model, main, rail));
  wrap.appendChild(el("div", { class: "wizard-body" }, main, rail));
  renderWizardStep(model, main, rail);

  const resultBox = el("div", { id: "gs-result", style: { marginTop: "18px" } });
  if (state.research.lastGS) resultBox.appendChild(gridSearchResult(state.research.lastGS));
  wrap.appendChild(resultBox);
  return wrap;
}

function stepperHeader(model, main, rail) {
  const bar = el("div", { class: "wiz-stepper" });
  WIZ_STEPS.forEach((label, i) => {
    const n = i + 1;
    const cls = n === model.step ? "active" : n < model.step ? "done" : "";
    const dot = el("button", { class: "wiz-step " + cls },
      el("span", { class: "wiz-step-num" }, n < model.step ? "✓" : String(n)),
      el("span", { class: "wiz-step-label" }, label));
    dot.addEventListener("click", () => { model.step = n; renderWizardStep(model, main, rail); });
    bar.appendChild(dot);
    if (i < WIZ_STEPS.length - 1) bar.appendChild(el("div", { class: "wiz-step-line" + (n < model.step ? " done" : "") }));
  });
  return bar;
}

function renderWizardStep(model, main, rail) {
  const refreshRail = () => { clear(rail).appendChild(buildRail(model)); };
  const rerender = () => renderWizardStep(model, main, rail);
  // keep the stepper header in sync
  const wrap = main.closest(".wizard");
  if (wrap) { const old = wrap.querySelector(".wiz-stepper"); if (old) old.replaceWith(stepperHeader(model, main, rail)); }
  refreshRail();
  clear(main);
  if (model.step === 1) main.appendChild(wizStepSpace(model, refreshRail, rerender));
  else if (model.step === 2) main.appendChild(wizStepObjective(model, refreshRail));
  else main.appendChild(wizStepReview(model));
  main.appendChild(wizardNav(model, rerender));
}

function fieldBox(label, node) {
  return el("div", { class: "field" }, el("label", { class: "lbl" }, label), node);
}

function modeToggle(model, p, onModeChange) {
  const cfg = model.params[p.path];
  const modes = p.kind === "enum" ? [["fixed", "Base"], ["set", "Pick set"]] : [["fixed", "Base"], ["list", "List"], ["range", "Range"]];
  const seg = el("div", { class: "segment seg-sm" });
  for (const [m, lbl] of modes) {
    const b = el("button", { type: "button" }, lbl);
    if (cfg.mode === m) b.classList.add("on");
    b.addEventListener("click", () => { cfg.mode = m; onModeChange(); });
    seg.appendChild(b);
  }
  return seg;
}

function valueControl(model, p, refreshRail) {
  const cfg = model.params[p.path];
  if (cfg.mode === "fixed") {
    const base = getPath(specForRun(), p.path);
    return el("div", { class: "wp-fixed" }, "Held at base value: ", el("b", {}, base == null ? "engine default" : String(base)));
  }
  if (cfg.mode === "list") {
    const inp = el("input", { type: "text", value: cfg.list, placeholder: "e.g. " + (p.ex || []).join(", ") });
    inp.addEventListener("input", () => { cfg.list = inp.value; refreshRail(); });
    return fieldBox("Specific values (comma-separated)", inp);
  }
  if (cfg.mode === "range") {
    const mk = (k, ph) => { const i = el("input", { type: "number", value: cfg.range[k], placeholder: ph, step: "any" }); i.addEventListener("input", () => { cfg.range[k] = i.value; refreshRail(); }); return i; };
    return el("div", { class: "wp-range" },
      fieldBox("Start", mk("start", String((p.ex || [0])[0]))),
      fieldBox("Stop", mk("stop", String((p.ex || [0]).slice(-1)[0]))),
      fieldBox("Step", mk("step", "1")));
  }
  // enum "set"
  const opts = (typeof p.options === "function" ? p.options() : p.options) || [];
  const chips = el("div", { class: "wp-chips" });
  for (const o of opts) {
    const c = el("button", { type: "button", class: "chip" + (cfg.set.includes(String(o)) || cfg.set.includes(o) ? " on" : "") }, String(o));
    c.addEventListener("click", () => {
      const i = cfg.set.indexOf(o);
      if (i >= 0) cfg.set.splice(i, 1); else cfg.set.push(o);
      c.classList.toggle("on");
      refreshRail();
    });
    chips.appendChild(c);
  }
  return chips;
}

function paramRow(model, p, refreshRail, rerender) {
  const cfg = model.params[p.path];
  const unmet = cfg.mode !== "fixed" && paramValues(p, cfg).length && !requireMet(p, model);
  const row = el("div", { class: "wiz-param" + (cfg.mode !== "fixed" ? " swept" : "") },
    el("div", { class: "wp-head" },
      el("div", { class: "wp-id" },
        el("div", { class: "wp-label" }, p.label, infoTip(p.hint)),
        el("div", { class: "wp-path" }, p.path)),
      modeToggle(model, p, rerender)),
    el("div", { class: "wp-values" }, valueControl(model, p, refreshRail)));
  if (unmet) row.appendChild(el("div", { class: "wp-note warnc" }, `Ignored — needs ${p.requires.path} = "${p.requires.value}" in the base or swept set.`));
  return row;
}

function wizStepSpace(model, refreshRail, rerender) {
  const groups = {};
  for (const p of SWEEP_PARAMS) (groups[p.group] = groups[p.group] || []).push(p);
  const container = el("div", { class: "stack" });
  container.appendChild(el("div", { class: "wiz-intro" },
    el("div", { class: "wiz-intro-title" }, "Define the search space"),
    el("div", { class: "wiz-intro-sub" }, "Sweep runs your current Strategy Lab config as the base, varying the parameters you set below. Each parameter held at Base contributes nothing to the search; List, Range or Pick set adds an axis.")));
  for (const [g, ps] of Object.entries(groups)) {
    container.appendChild(card(g, null, ...ps.map((p) => paramRow(model, p, refreshRail, rerender))));
  }
  return container;
}

function wizStepObjective(model, refreshRail) {
  const objSel = el("select");
  for (const o of state.meta.objectives) { const op = el("option", { value: o }, o); if (o === model.objective) op.selected = true; objSel.appendChild(op); }
  objSel.addEventListener("change", () => { model.objective = objSel.value; });
  const objDesc = {
    deflated_sharpe: "Sharpe penalised for the number of configs tried — the best guard against over-fitting a sweep.",
    sharpe: "Risk-adjusted return. Rewards smooth equity curves.",
    total_return: "Raw return. Ignores risk — prone to picking fragile outliers.",
    calmar: "Return divided by max drawdown. Favours shallow drawdowns.",
    profit_factor: "Gross profit / gross loss. Above 1 is profitable.",
    sortino: "Like Sharpe but only penalises downside volatility.",
  };
  const topk = el("input", { type: "number", value: String(model.top_k), min: "1", max: "200" });
  topk.addEventListener("input", () => { model.top_k = Math.max(1, Number(topk.value) || 20); });

  return el("div", { class: "stack" },
    card("Ranking objective", "How each candidate configuration is scored and ranked.",
      el("div", { class: "field", style: { maxWidth: "300px" } }, el("label", { class: "lbl" }, "Objective"), objSel),
      el("div", { class: "obj-desc", id: "obj-desc" }, objDesc[model.objective] || ""),
      (() => { objSel.addEventListener("change", () => { document.getElementById("obj-desc").textContent = objDesc[objSel.value] || ""; }); return null; })()),
    card("Compute budget", "Each candidate is a full backtest on your real data. Keep the search focused.",
      fieldBox("Keep top-N results", topk),
      el("div", { class: "budget-note" }, "Tip: start broad with a coarse grid, then zoom into the best region with a Range sweep. Deflated Sharpe already discounts large searches.")));
}

function wizStepReview(model) {
  const { space, axes, n, ignored } = analyzeModel(model);
  const spec = specForRun();
  const rows = [
    ["Symbol", spec.symbol || (spec.data && spec.data.symbol) || "—"],
    ["Data", (spec.data && spec.data.kind) === "binance" ? `Binance ${spec.data.interval || ""}` : "Synthetic"],
    ["Base direction", (spec.grid && spec.grid.direction) || "neutral"],
    ["Base spacing", (spec.grid && spec.grid.spacing) || "arithmetic"],
    ["Objective", model.objective],
    ["Keep top-N", String(model.top_k)],
  ];
  const summary = el("dl", { class: "kv review-kv" });
  for (const [k, v] of rows) { summary.appendChild(el("dt", {}, k)); summary.appendChild(el("dd", {}, v)); }

  const axList = el("div", { class: "review-axes" });
  if (!axes.length) axList.appendChild(el("div", { class: "wp-note warnc" }, "No parameters are being swept yet — go back to Search space and set at least one to List, Range or Pick set."));
  for (const ax of axes) {
    const p = SWEEP_PARAMS.find((x) => x.path === ax);
    axList.appendChild(el("div", { class: "review-axis" },
      el("span", { class: "ra-k" }, p ? p.label : ax),
      el("span", { class: "ra-c" }, space[ax].length + " values"),
      el("span", { class: "ra-v" }, "[" + space[ax].join(", ") + "]")));
  }
  for (const p of ignored) axList.appendChild(el("div", { class: "wp-note warnc" }, `${p.label} ignored (needs ${p.requires.path} = "${p.requires.value}").`));

  const big = el("div", { class: "review-count " + (n === 0 ? "warnc" : n > BUDGET_SOFT ? "neg" : n > BUDGET_WARN ? "warnc" : "pos") },
    el("span", { class: "rc-num" }, fmt.int(n)),
    el("span", { class: "rc-lbl" }, n === 1 ? "backtest will run" : "backtests will run"));

  return el("div", { class: "stack" },
    card("Review", "Confirm the sweep before spending compute.", el("div", { class: "review-grid" }, summary, big)),
    card("Search axes", `${axes.length} axis${axes.length === 1 ? "" : "es"} → ${fmt.int(n)} combinations`, axList));
}

function wizardNav(model, rerender) {
  const { n } = analyzeModel(model);
  const nav = el("div", { class: "wiz-nav" });
  if (model.step > 1) {
    const back = el("button", { class: "btn btn-ghost" }, "← Back");
    back.addEventListener("click", () => { model.step--; rerender(); });
    nav.appendChild(back);
  } else nav.appendChild(el("div"));

  if (model.step < WIZ_STEPS.length) {
    const next = el("button", { class: "btn btn-primary" }, "Next →");
    next.addEventListener("click", () => { model.step++; rerender(); });
    nav.appendChild(next);
  } else {
    const run = runButton(`⚡ Run sweep (${fmt.int(n)})`, async () => {
      const { space, n: cnt } = analyzeModel(model);
      if (!cnt) { toast("No swept axes — set at least one parameter to List, Range or Pick set.", "bad"); return; }
      if (cnt > BUDGET_SOFT && !confirm(`This will run ${cnt} full backtests and may take a while. Continue?`)) return;
      toast(`Running ${cnt} backtests…`, "info");
      const res = await api.gridSearch(specForRun(), space, model.objective, model.top_k);
      state.research.lastGS = res;
      const box = document.getElementById("gs-result");
      if (box) { clear(box).appendChild(gridSearchResult(res)); box.scrollIntoView({ behavior: "smooth", block: "start" }); }
      toast(`Sweep complete — best ${model.objective} ${fmt.ratio(res.results[0] && res.results[0].score, 3)}`, "good");
    });
    nav.appendChild(run);
  }
  return nav;
}

function buildRail(model) {
  const { space, axes, n, ignored } = analyzeModel(model);
  const tone = n === 0 ? "warnc" : n > BUDGET_SOFT ? "neg" : n > BUDGET_WARN ? "warnc" : "pos";
  const budgetLabel = n === 0 ? "Set an axis to begin" : n <= 60 ? "Fast — runs in seconds" : n <= BUDGET_WARN ? "Moderate search" : n <= BUDGET_SOFT ? "Heavy — be patient" : "Very large — consider narrowing";
  const inner = el("div", { class: "rail-inner" });
  inner.appendChild(el("div", { class: "rail-head" }, "Experiment size"));
  inner.appendChild(el("div", { class: "rail-count " + tone },
    el("div", { class: "rc-num" }, fmt.int(n)),
    el("div", { class: "rc-lbl" }, n === 1 ? "backtest" : "backtests")));
  inner.appendChild(el("div", { class: "rail-budget " + tone }, budgetLabel));

  const axBox = el("div", { class: "rail-axes" });
  if (!axes.length) axBox.appendChild(el("div", { class: "rail-empty" }, "No swept axes yet. Set a parameter to List, Range or Pick set to add a dimension."));
  for (const ax of axes) {
    const p = SWEEP_PARAMS.find((x) => x.path === ax);
    const vals = space[ax];
    axBox.appendChild(el("div", { class: "rail-axis" },
      el("span", { class: "ra-k" }, p ? p.label : ax),
      el("span", { class: "ra-v" }, vals.length + " × [" + vals.slice(0, 5).join(", ") + (vals.length > 5 ? ", …" : "") + "]")));
  }
  inner.appendChild(axBox);
  if (ignored.length) inner.appendChild(el("div", { class: "rail-note warnc" }, ignored.map((p) => p.label + " ignored (conditional)").join(" · ")));
  return inner;
}



function gridSearchResult(res) {
  const wrap = el("div", { class: "stack" });
  if (res.heatmap) {
    wrap.appendChild(card(`Heatmap — ${res.objective}`, `${res.heatmap.y_label} (rows) × ${res.heatmap.x_label} (cols)`, heatmapTable(res.heatmap)));
  }
  const cols = [
    { key: "rank", label: "#", fmt: (r) => String(r.rank), sortable: false },
    ...res.axes.map((ax) => ({ key: ax, label: ax, fmt: (r) => String(r.params[ax]) })),
    { key: "score", label: "Score", align: "right", fmt: (r) => fmt.ratio(r.score, 3) },
    { key: "total_return", label: "Return", align: "right", fmt: (r) => el("span", { class: (r.total_return || 0) >= 0 ? "pos" : "neg" }, fmt.pctSigned(r.total_return)) },
    { key: "max_drawdown", label: "Max DD", align: "right", fmt: (r) => fmt.pct(r.max_drawdown) },
    { key: "sharpe", label: "Sharpe", align: "right", fmt: (r) => fmt.ratio(r.sharpe) },
    { key: "deflated_sharpe", label: "Defl. Sharpe", align: "right", fmt: (r) => fmt.pct(r.deflated_sharpe) },
    { key: "n_trades", label: "Trades", align: "right", fmt: (r) => fmt.int(r.n_trades) },
  ];
  const rows = res.results.map((r, i) => ({ ...r, ...r.params, rank: i + 1 }));
  wrap.appendChild(card("Leaderboard", `${res.n_results} configurations, best first`, dataTable(cols, rows, { scroll: true })));
  return wrap;
}

function heatmapTable(h) {
  const vals = h.z.flat().filter((v) => v != null);
  const min = Math.min(...vals), max = Math.max(...vals);
  const colorFor = (v) => {
    if (v == null) return "var(--surface-3)";
    const t = max === min ? 0.5 : (v - min) / (max - min);
    const r = Math.round(244 + (34 - 244) * t), g = Math.round(63 + (197 - 63) * t), b = Math.round(94 + (94 - 94) * t);
    return `rgba(${r},${g},${b},${0.25 + 0.55 * t})`;
  };
  const table = el("table", { class: "tbl" });
  const thead = el("thead");
  const htr = el("tr", {}, el("th", {}, `${h.y_label} \\ ${h.x_label}`));
  for (const x of h.x) htr.appendChild(el("th", { class: "num" }, String(x)));
  thead.appendChild(htr);
  const tbody = el("tbody");
  h.y.forEach((y, yi) => {
    const tr = el("tr", {}, el("td", { style: { fontWeight: "600" } }, String(y)));
    h.x.forEach((x, xi) => {
      const v = h.z[yi][xi];
      tr.appendChild(el("td", { class: "num", style: { background: colorFor(v), textAlign: "center", fontWeight: "600" } }, v == null ? "—" : fmt.ratio(v, 2)));
    });
    tbody.appendChild(tr);
  });
  table.appendChild(thead); table.appendChild(tbody);
  return el("div", { class: "table-wrap" }, table);
}

function walkForwardPanel() {
  const wrap = el("div", { class: "stack" });
  const a1 = axisPicker("grid.levels", "8, 12, 16, 20");
  const splits = el("input", { type: "number", value: "4", min: "2", max: "12" });
  const objSel = el("select");
  for (const o of state.meta.objectives) objSel.appendChild(el("option", { value: o }, o));
  const resultBox = el("div");
  const run = runButton("⚡ Run Walk-Forward", async () => {
    const space = {};
    if (a1.sel.value && a1.vals.value) space[a1.sel.value] = parseValues(a1.vals.value);
    if (Object.keys(space).length === 0) { toast("Pick a parameter axis to optimise", "bad"); return; }
    toast("Running expanding-window walk-forward…", "info");
    const res = await api.walkForward(specForRun(), space, parseInt(splits.value), objSel.value);
    state.research.lastWF = res;
    clear(resultBox).appendChild(walkForwardResult(res));
  });
  wrap.appendChild(card("Walk-Forward Optimisation", "Optimise in-sample, measure out-of-sample. The IS↔OOS gap is the honest robustness signal.",
    a1.node,
    el("div", { class: "field-row" },
      el("div", { class: "field" }, el("label", { class: "lbl" }, "Splits"), splits),
      el("div", { class: "field" }, el("label", { class: "lbl" }, "Objective"), objSel)),
    run));
  if (state.research.lastWF) resultBox.appendChild(walkForwardResult(state.research.lastWF));
  wrap.appendChild(resultBox);
  return wrap;
}

function walkForwardResult(res) {
  const wrap = el("div", { class: "stack" });
  const s = res.summary;
  const kg = el("div", { class: "kpi-grid" },
    kpi({ label: "Folds", value: fmt.int(s.n_folds) }),
    kpi({ label: "Mean OOS score", value: fmt.ratio(s.mean_oos_score, 3), tone: (s.mean_oos_score || 0) >= 0 ? "pos" : "neg" }),
    kpi({ label: "Mean OOS return", value: fmt.pctSigned(s.mean_oos_return), tone: (s.mean_oos_return || 0) >= 0 ? "pos" : "neg" }),
    kpi({ label: "Positive folds", value: `${s.positive_oos_folds} / ${s.n_folds}` }));
  wrap.appendChild(kg);

  const canvas = el("canvas");
  wrap.appendChild(card("In-sample vs Out-of-sample", `Objective: ${s.objective}`, el("div", { class: "chart-box h-md" }, canvas)));
  queueMicrotask(() => charts.walkForwardChart(canvas, res.folds));

  const cols = [
    { key: "fold", label: "Fold", fmt: (f) => `#${f.fold + 1}` },
    { key: "best", label: "Best params", fmt: (f) => el("span", { class: "mono", style: { fontSize: "12px" } }, JSON.stringify(f.best_params)) },
    { key: "is_score", label: "IS score", align: "right", fmt: (f) => fmt.ratio(f.is_score, 3) },
    { key: "oos_score", label: "OOS score", align: "right", fmt: (f) => el("span", { class: (f.oos_score || 0) >= 0 ? "pos" : "neg" }, fmt.ratio(f.oos_score, 3)) },
    { key: "oos_total_return", label: "OOS return", align: "right", fmt: (f) => el("span", { class: (f.oos_total_return || 0) >= 0 ? "pos" : "neg" }, fmt.pctSigned(f.oos_total_return)) },
    { key: "oos_max_drawdown", label: "OOS Max DD", align: "right", fmt: (f) => fmt.pct(f.oos_max_drawdown) },
  ];
  wrap.appendChild(card("Fold detail", null, dataTable(cols, res.folds, {})));
  return wrap;
}

function monteCarloPanel() {
  const wrap = el("div", { class: "stack" });
  let method = "trades";
  const seg = el("div", { class: "segment", style: { maxWidth: "320px" } });
  for (const mth of [["trades", "Bootstrap trades"], ["returns", "Shuffle returns"]]) {
    const b = el("button", { type: "button" }, mth[1]);
    if (mth[0] === method) b.classList.add("on");
    b.addEventListener("click", () => { method = mth[0]; [...seg.children].forEach((c) => c.classList.remove("on")); b.classList.add("on"); });
    seg.appendChild(b);
  }
  const sims = el("input", { type: "number", value: "2000", min: "100", max: "20000", step: "100" });
  const resultBox = el("div");
  const run = runButton("⚡ Run Monte Carlo", async () => {
    toast("Resampling…", "info");
    const res = await api.monteCarlo(specForRun(), method, parseInt(sims.value), 0);
    state.research.lastMC = res;
    clear(resultBox).appendChild(monteCarloResult(res));
  });
  wrap.appendChild(card("Monte Carlo Robustness", "Resample the edge to see how bad drawdowns get and how often the strategy ends underwater.",
    el("div", { class: "field" }, el("label", { class: "lbl" }, "Method", infoTip("Bootstrap closed-trade PnLs, or shuffle per-bar returns.")), seg),
    el("div", { class: "field", style: { maxWidth: "200px" } }, el("label", { class: "lbl" }, "Simulations"), sims),
    run));
  if (state.research.lastMC) resultBox.appendChild(monteCarloResult(state.research.lastMC));
  wrap.appendChild(resultBox);
  return wrap;
}

function monteCarloResult(res) {
  if (res.n_sims === 0 || !res.histogram || !res.histogram.counts.length) {
    return card(null, null, emptyState("∅", "No distribution", res.note || "Not enough trades to resample."));
  }
  const fr = res.final_return || {};
  const wrap = el("div", { class: "stack" });
  const kg = el("div", { class: "kpi-grid" },
    kpi({ label: "Prob. of loss", value: fmt.pct(res.prob_loss), tone: (res.prob_loss || 0) < 0.2 ? "pos" : "neg", tip: "Share of simulations ending below starting capital." }),
    kpi({ label: "Median return", value: fmt.pctSigned(fr.p50), tone: (fr.p50 || 0) >= 0 ? "pos" : "neg" }),
    kpi({ label: "5th pct return", value: fmt.pctSigned(fr.p5), tone: (fr.p5 || 0) >= 0 ? "pos" : "neg", tip: "Bad-case outcome — 95% of sims did better." }),
    kpi({ label: "Worst drawdown", value: fmt.pct(res.worst_max_drawdown), tone: "neg" }));
  wrap.appendChild(kg);
  const canvas = el("canvas");
  wrap.appendChild(card("Distribution of Final Return", `${fmt.int(res.n_sims)} simulations · base run ${fmt.pctSigned(res.base_total_return)}`,
    el("div", { class: "chart-box h-md" }, canvas)));
  queueMicrotask(() => charts.histogramChart(canvas, res.histogram.centers, res.histogram.counts, { pct: true, unit: "sims", color: "var(--brand-2)" }));
  return wrap;
}

// ================================================================ LEARN
function renderLearn() {
  const g = state.meta.guide;
  const wrap = el("div", { class: "stack fade-in", style: { maxWidth: "980px" } });
  wrap.appendChild(card("What is grid trading?", null, el("p", { style: { margin: "0", color: "var(--text-dim)", lineHeight: "1.7" } }, g.intro)));

  const toneIcon = { good: "✓", bad: "✕", warn: "!", info: "◆" };
  const toneColor = { good: "var(--pos)", bad: "var(--neg)", warn: "var(--warn)", info: "var(--info)" };
  const sgrid = el("div", { class: "grid-2" });
  for (const sec of g.sections) {
    const pts = el("div", {});
    for (const p of sec.points) {
      pts.appendChild(el("div", { class: "guide-point" },
        el("span", { class: "mk", style: { color: toneColor[sec.tone] } }, toneIcon[sec.tone]),
        el("span", {}, p)));
    }
    sgrid.appendChild(card(sec.title, null, pts));
  }
  wrap.appendChild(sgrid);

  const regs = el("div", { class: "pill-row" });
  for (const r of g.regimes) {
    regs.appendChild(el("div", { class: "insight " + (r.verdict === "good" ? "good" : r.verdict === "bad" ? "bad" : "warn"), style: { flex: "1", minWidth: "240px" } },
      el("div", {}, el("div", { style: { fontWeight: "700", marginBottom: "3px" } }, r.label + " market"), el("div", { class: "text-dim", style: { fontSize: "13px" } }, r.note))));
  }
  wrap.appendChild(card("Market regimes", "Where a grid lives or dies", regs));

  const src = el("div", { class: "stack", style: { gap: "8px" } });
  for (const s of g.sources) src.appendChild(el("a", { href: s.url, target: "_blank", rel: "noopener" }, "↗ " + s.label));
  wrap.appendChild(card("Further reading", "External references", src));
  view.appendChild(wrap);
}

// ---------------------------------------------------------------- helpers
function legend(items) {
  const wrap = el("div", { class: "legend" });
  for (const [label, color] of items) {
    wrap.appendChild(el("span", { class: "lg" }, el("span", { class: "sw", style: { background: color } }), label));
  }
  return wrap;
}

function histogram(values, bins = 30) {
  if (!values.length) return { centers: [], counts: [] };
  const min = Math.min(...values), max = Math.max(...values);
  if (min === max) return { centers: [min], counts: [values.length] };
  const width = (max - min) / bins;
  const counts = new Array(bins).fill(0);
  for (const v of values) {
    let idx = Math.floor((v - min) / width);
    if (idx >= bins) idx = bins - 1; if (idx < 0) idx = 0;
    counts[idx]++;
  }
  const centers = counts.map((_, i) => min + width * (i + 0.5));
  return { centers, counts };
}

function initTheme() {
  const saved = localStorage.getItem("gl-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  document.getElementById("theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("gl-theme", next);
    charts.applyChartTheme();
    go(state.route); // re-render so charts pick up theme colors
  });
}

function icon(name) {
  const p = {
    grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
    flask: "M9 3h6M10 3v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3",
    search: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.3-4.3",
    book: "M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5A2.5 2.5 0 006.5 22H20V2H6.5A2.5 2.5 0 004 4.5v15z",
  }[name];
  return `<svg fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="${p}"/></svg>`;
}

init();
