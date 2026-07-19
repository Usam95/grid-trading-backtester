// Chart.js builders. All charts plot in "sample position" space (0..N-1) so the
// down-sampled curves and the trade markers share one x-axis.
import { fmt } from "./format.js";

const registry = new Map(); // canvas -> Chart instance

function css(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function applyChartTheme() {
  if (!window.Chart) return;
  const C = window.Chart;
  C.defaults.color = css("--text-dim");
  C.defaults.borderColor = css("--border");
  C.defaults.font.family = "'Inter', sans-serif";
  C.defaults.font.size = 11.5;
  C.defaults.plugins.legend.display = false;
  C.defaults.plugins.tooltip.backgroundColor = css("--elevated");
  C.defaults.plugins.tooltip.titleColor = css("--text");
  C.defaults.plugins.tooltip.bodyColor = css("--text-dim");
  C.defaults.plugins.tooltip.borderColor = css("--border-2");
  C.defaults.plugins.tooltip.borderWidth = 1;
  C.defaults.plugins.tooltip.padding = 10;
  C.defaults.plugins.tooltip.cornerRadius = 8;
  C.defaults.maintainAspectRatio = false;
}

function mount(canvas, config) {
  if (registry.has(canvas)) registry.get(canvas).destroy();
  const chart = new window.Chart(canvas.getContext("2d"), config);
  registry.set(canvas, chart);
  return chart;
}

export function destroyAll() {
  for (const c of registry.values()) c.destroy();
  registry.clear();
}

const grad = (ctx, color, alpha = 0.28) => {
  const { chartArea, ctx: c } = ctx.chart;
  if (!chartArea) return color;
  const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  g.addColorStop(0, color.replace(")", `, ${alpha})`).replace("rgb", "rgba"));
  g.addColorStop(1, color.replace(")", ", 0)").replace("rgb", "rgba"));
  return g;
};

const baseScales = (tsLabels) => ({
  x: {
    type: "linear",
    grid: { color: css("--border"), drawTicks: false },
    ticks: {
      maxTicksLimit: 7,
      callback(v) {
        if (tsLabels) {
          const t = tsLabels[v];
          if (t) { try { return new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" }); } catch { return ""; } }
          return ""; // out-of-range index when timestamps are present
        }
        return v;
      },
    },
  },
  y: { grid: { color: css("--border") }, ticks: { maxTicksLimit: 6 } },
});

// ---- equity vs benchmarks -------------------------------------------------
export function equityChart(canvas, series) {
  const n = series.equity.length;
  const xs = Array.from({ length: n }, (_, i) => i);
  const ds = [
    { label: "Grid equity", color: css("--brand-2"), data: series.equity, fill: true, width: 2.2 },
    { label: "Buy & Hold", color: css("--text-mute"), data: series.buy_and_hold, dash: [5, 4] },
    { label: "DCA", color: css("--brand-3"), data: series.dca, dash: [2, 3] },
  ].filter((d) => d.data && d.data.length);

  return mount(canvas, {
    type: "line",
    data: {
      labels: xs,
      datasets: ds.map((d) => ({
        label: d.label,
        data: d.data.map((y, i) => ({ x: i, y })),
        borderColor: d.color,
        borderWidth: d.width || 1.6,
        borderDash: d.dash || [],
        pointRadius: 0,
        tension: 0.12,
        fill: d.fill ? "origin" : false,
        backgroundColor: d.fill ? (ctx) => grad(ctx, "rgb(139,92,246)", 0.22) : undefined,
      })),
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: (() => { const s = baseScales(series.timestamps); s.x.min = 0; s.x.max = n - 1; return s; })(),
      plugins: {
        tooltip: {
          callbacks: {
            title: (items) => series.timestamps?.[items[0].parsed.x] ? new Date(series.timestamps[items[0].parsed.x]).toLocaleString() : `#${items[0].parsed.x}`,
            label: (it) => `${it.dataset.label}: ${fmt.money(it.parsed.y)}`,
          },
        },
      },
    },
  });
}

// ---- price + grid overlay + trade markers ---------------------------------
export function priceGridChart(canvas, series, grid, trades) {
  const price = series.price || [];
  const n = price.length;
  const datasets = [];

  // grid rung lines
  if (grid && grid.levels && !grid.error) {
    const center = grid.center;
    for (const lvl of grid.levels) {
      const isBuy = lvl < center;
      datasets.push({
        label: "_grid",
        data: [{ x: 0, y: lvl }, { x: n - 1, y: lvl }],
        borderColor: isBuy ? "rgba(34,197,94,.35)" : "rgba(244,63,94,.35)",
        borderWidth: 1,
        borderDash: [3, 3],
        pointRadius: 0,
        tension: 0,
        order: 5,
      });
    }
  }

  // price line
  datasets.push({
    label: "Price",
    data: price.map((y, i) => ({ x: i, y })),
    borderColor: css("--brand-3"),
    borderWidth: 1.8,
    pointRadius: 0,
    tension: 0.1,
    order: 1,
  });

  // trade markers (cap to keep it readable)
  const cap = 400;
  const sample = trades.length > cap ? trades.filter((_, i) => i % Math.ceil(trades.length / cap) === 0) : trades;
  const buys = sample.map((t) => ({ x: t.entry_x, y: t.entry_price }));
  const sells = sample.map((t) => ({ x: t.exit_x, y: t.exit_price, pnl: t.pnl }));
  datasets.push({
    type: "scatter", label: "Entries", data: buys, order: 0,
    backgroundColor: "rgba(34,197,94,.9)", pointStyle: "triangle", radius: 4, rotation: 0,
  });
  datasets.push({
    type: "scatter", label: "Exits", data: sells, order: 0,
    backgroundColor: "rgba(244,63,94,.9)", pointStyle: "triangle", radius: 4, rotation: 180,
  });

  return mount(canvas, {
    type: "line",
    data: { datasets },
    options: {
      interaction: { mode: "nearest", intersect: true },
      scales: { ...baseScales(series.timestamps), x: { ...baseScales(series.timestamps).x, min: 0, max: n - 1 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: (it) => it.dataset.label !== "_grid",
          callbacks: {
            label: (it) => {
              if (it.dataset.label === "Price") return `Price: ${fmt.price(it.parsed.y)}`;
              if (it.dataset.label === "Exits") return `Exit ${fmt.price(it.parsed.y)} (pnl ${fmt.money(it.raw.pnl)})`;
              return `Entry: ${fmt.price(it.parsed.y)}`;
            },
          },
        },
      },
    },
  });
}

// ---- drawdown underwater --------------------------------------------------
export function drawdownChart(canvas, series) {
  const dd = (series.drawdown || []).map((v, i) => ({ x: i, y: (v || 0) * 100 }));
  const n = dd.length;
  return mount(canvas, {
    type: "line",
    data: { datasets: [{
      label: "Drawdown",
      data: dd,
      borderColor: css("--neg"),
      borderWidth: 1.4,
      pointRadius: 0,
      fill: "origin",
      backgroundColor: (ctx) => grad(ctx, "rgb(244,63,94)", 0.32),
      tension: 0.1,
    }] },
    options: {
      scales: {
        x: { ...baseScales(series.timestamps).x, min: 0, max: n - 1 },
        y: { grid: { color: css("--border") }, ticks: { callback: (v) => `${+Number(v).toFixed(2)}%`, maxTicksLimit: 5 } },
      },
      plugins: { tooltip: { callbacks: { label: (it) => `Drawdown: ${it.parsed.y.toFixed(2)}%` } } },
    },
  });
}

// ---- histogram (generic bars) ---------------------------------------------
export function histogramChart(canvas, centers, counts, opts = {}) {
  return mount(canvas, {
    type: "bar",
    data: {
      labels: centers.map((c) => opts.pct ? (c * 100).toFixed(1) + "%" : fmt.num(c, 1)),
      datasets: [{
        data: counts,
        backgroundColor: opts.color || css("--brand-1"),
        borderRadius: 3,
        barPercentage: 1.0,
        categoryPercentage: 0.96,
      }],
    },
    options: {
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
        y: { grid: { color: css("--border") }, ticks: { maxTicksLimit: 5 } },
      },
      plugins: { tooltip: { callbacks: { label: (it) => `${it.parsed.y} ${opts.unit || "trades"}` } } },
    },
  });
}

// ---- walk-forward IS vs OOS ----------------------------------------------
export function walkForwardChart(canvas, folds) {
  const labels = folds.map((f) => `Fold ${f.fold + 1}`);
  return mount(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "In-sample", data: folds.map((f) => f.is_score), backgroundColor: css("--brand-2"), borderRadius: 4 },
        { label: "Out-of-sample", data: folds.map((f) => f.oos_score), backgroundColor: css("--brand-3"), borderRadius: 4 },
      ],
    },
    options: {
      scales: { x: { grid: { display: false } }, y: { grid: { color: css("--border") } } },
      plugins: { legend: { display: true, labels: { boxWidth: 12, boxHeight: 12 } } },
    },
  });
}

// ---- dashboard: aggregate portfolio equity -------------------------------
// runs ordered oldest -> newest. Plots cumulative capital deployed (baseline)
// vs cumulative ending equity (portfolio) so the gap = total realized edge.
export function aggregateEquityChart(canvas, runs) {
  let deployed = 0;
  let ending = 0;
  const baseline = [];
  const portfolio = [];
  const labels = [];
  runs.forEach((r, i) => {
    deployed += r.initial_cash || 0;
    ending += r.final_equity || 0;
    baseline.push({ x: i, y: deployed });
    portfolio.push({ x: i, y: ending });
    labels.push(r.symbol);
  });
  const n = runs.length;
  return mount(canvas, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Portfolio value", data: portfolio,
          borderColor: css("--brand-2"), borderWidth: 2.4, pointRadius: n <= 30 ? 3 : 0,
          pointBackgroundColor: css("--brand-2"), tension: 0.18, fill: "origin",
          backgroundColor: (ctx) => grad(ctx, "rgb(139,92,246)", 0.20),
        },
        {
          label: "Capital deployed", data: baseline,
          borderColor: css("--text-mute"), borderWidth: 1.6, borderDash: [5, 4],
          pointRadius: 0, tension: 0.18, fill: false,
        },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          type: "linear", min: 0, max: Math.max(0, n - 1),
          grid: { color: css("--border"), drawTicks: false },
          ticks: { maxTicksLimit: 8, callback: (v) => (labels[v] ? `#${v + 1}` : "") },
        },
        y: { grid: { color: css("--border") }, ticks: { maxTicksLimit: 6, callback: (v) => fmt.money(v, 0) } },
      },
      plugins: {
        legend: { display: true, labels: { boxWidth: 12, boxHeight: 12, usePointStyle: true } },
        tooltip: {
          callbacks: {
            title: (items) => `Run #${items[0].parsed.x + 1} · ${labels[items[0].parsed.x] || ""}`,
            label: (it) => `${it.dataset.label}: ${fmt.money(it.parsed.y)}`,
          },
        },
      },
    },
  });
}

// ---- dashboard: return leaderboard (horizontal bars) ---------------------
export function returnLeaderboardChart(canvas, labels, values) {
  return mount(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values.map((v) => (v || 0) * 100),
        backgroundColor: values.map((v) => (v >= 0 ? css("--pos") : css("--neg"))),
        borderRadius: 5,
        barPercentage: 0.78,
      }],
    },
    options: {
      indexAxis: "y",
      scales: {
        x: { grid: { color: css("--border") }, ticks: { callback: (v) => `${+Number(v).toFixed(1)}%` } },
        y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 11 } } },
      },
      plugins: { tooltip: { callbacks: { label: (it) => `${it.parsed.x.toFixed(2)}%` } } },
    },
  });
}

// ---- tiny inline SVG sparkline (no Chart.js, cheap for many rows) ---------
export function sparklineSVG(values, { w = 96, h = 28, up = "var(--pos)", down = "var(--neg)" } = {}) {
  const a = (values || []).filter((v) => v != null && isFinite(v));
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("width", w);
  svg.setAttribute("height", h);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.classList.add("spark");
  if (a.length < 2) return svg;
  const min = Math.min(...a), max = Math.max(...a);
  const span = max - min || 1;
  const pad = 2;
  const pts = a.map((v, i) => {
    const x = pad + (i / (a.length - 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / span) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = a[a.length - 1] >= a[0];
  const stroke = rising ? up : down;
  const poly = document.createElementNS(ns, "polyline");
  poly.setAttribute("points", pts.join(" "));
  poly.setAttribute("fill", "none");
  poly.setAttribute("stroke", stroke);
  poly.setAttribute("stroke-width", "1.6");
  poly.setAttribute("stroke-linejoin", "round");
  poly.setAttribute("stroke-linecap", "round");
  svg.appendChild(poly);
  return svg;
}

// ---- benchmark comparison bars -------------------------------------------
export function compareChart(canvas, labels, values) {
  return mount(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: values.map((v) => (v || 0) * 100),
        backgroundColor: values.map((v) => (v >= 0 ? css("--pos") : css("--neg"))),
        borderRadius: 5,
      }],
    },
    options: {
      indexAxis: "y",
      scales: { x: { grid: { color: css("--border") }, ticks: { callback: (v) => `${+Number(v).toFixed(2)}%` } }, y: { grid: { display: false } } },
      plugins: { tooltip: { callbacks: { label: (it) => `${it.parsed.x.toFixed(2)}%` } } },
    },
  });
}
