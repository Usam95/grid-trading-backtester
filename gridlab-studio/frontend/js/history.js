// Client-side run-history store (localStorage). gridlab-studio is a single-user,
// no-backend research tool, so completed backtests are persisted in the browser.
// This powers the portfolio Dashboard / Performance Overview across reloads.

const KEY = "gridlab.history.v2";
const CAP = 50; // keep the most recent N runs

function read() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function write(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, CAP)));
  } catch {
    // quota or private-mode: degrade silently, dashboard just stays empty
  }
}

// Down-sample an equity series to ~n points for a per-run sparkline.
function spark(arr, n = 48) {
  const a = (arr || []).filter((v) => v != null && isFinite(v));
  if (a.length <= n) return a.map((v) => +(+v).toFixed(2));
  const step = (a.length - 1) / (n - 1);
  const out = [];
  for (let i = 0; i < n; i++) out.push(+(+a[Math.round(i * step)]).toFixed(2));
  return out;
}

function strategyLabel(g) {
  if (g.adaptive) return "Adaptive grid";
  if (g.direction === "long") return "Long grid";
  if (g.direction === "short") return "Short grid";
  return "Neutral grid";
}

// Build a compact, self-contained summary from a full backtest result + its spec.
function summarize(r, spec) {
  const m = r.metrics || {};
  const ds = r.data_source || {};
  const g = spec.grid || {};
  const s = spec.sizing || {};
  return {
    id: "run_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7),
    ts: Date.now(),
    symbol: r.symbol || spec.symbol || (spec.data && spec.data.symbol) || "—",
    interval: (spec.data && spec.data.interval) || "—",
    data_kind: ds.kind || (spec.data && spec.data.kind) || "synthetic",
    data_label: ds.label || (ds.is_real ? "Real data" : "Synthetic"),
    is_real: !!ds.is_real,
    venue: ds.venue || spec.venue || null,
    strategy: strategyLabel(g),
    direction: g.direction || "neutral",
    adaptive: !!g.adaptive,
    spacing: g.spacing || "arithmetic",
    levels: g.levels != null ? g.levels : null,
    sizing_mode: s.mode || null,
    sizing_value: s.value != null ? s.value : null,
    start: r.start || null,
    end: r.end || null,
    bars: r.bars != null ? r.bars : null,
    initial_cash: r.initial_cash != null ? r.initial_cash : 0,
    final_equity: r.final_equity != null ? r.final_equity : 0,
    net_pnl: (r.final_equity != null ? r.final_equity : 0) - (r.initial_cash != null ? r.initial_cash : 0),
    total_return: m.total_return != null ? m.total_return : null,
    max_drawdown: m.max_drawdown != null ? m.max_drawdown : null,
    win_rate: m.win_rate != null ? m.win_rate : null,
    sharpe: m.sharpe != null ? m.sharpe : null,
    sortino: m.sortino != null ? m.sortino : null,
    profit_factor: m.profit_factor != null ? m.profit_factor : null,
    n_trades: r.n_closed_trades != null ? r.n_closed_trades : (m.n_trades || 0),
    fees_paid: r.fees_paid != null ? r.fees_paid : null,
    ret_over_bh: m.return_over_buy_hold != null ? m.return_over_buy_hold : null,
    bh_return: r.benchmarks && r.benchmarks.buy_and_hold ? r.benchmarks.buy_and_hold.total_return : null,
    liquidated: !!r.liquidated,
    verdict_score: r.verdict ? r.verdict.score : null,
    verdict_max: r.verdict ? r.verdict.max_score : null,
    verdict_label: r.verdict ? r.verdict.label : null,
    verdict_tone: r.verdict ? r.verdict.tone : "",
    spark: spark(r.series && r.series.equity),
  };
}

export const history = {
  // newest first
  list() {
    return read().sort((a, b) => b.ts - a.ts);
  },
  add(r, spec) {
    const list = read();
    const entry = summarize(r, spec);
    list.unshift(entry);
    write(list);
    return entry;
  },
  remove(id) {
    write(read().filter((x) => x.id !== id));
  },
  clear() {
    write([]);
  },
  count() {
    return read().length;
  },
  cap: CAP,
};
