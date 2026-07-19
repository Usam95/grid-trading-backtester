// Declarative config-form schema + renderer, and the live grid ladder preview.
import { el, getPath, setPath, fmt } from "./format.js";
import { infoTip } from "./ui.js";

// Venue presets are injected from the backend /api/meta payload so the venue
// picker can apply real fee defaults and explain each venue inline.
let VENUES = [];
export function setVenues(v) { VENUES = v || []; }

// Each field binds a dotted path in the spec. `scale` shows a fraction as a
// percentage. `showIf` hides a field based on the current spec.
export const SECTIONS = [
  {
    id: "asset", title: "Asset & Capital", icon: "◎", open: true,
    fields: [
      { path: "symbol", label: "Symbol", type: "text",
        tip: "The market to trade, e.g. BTCUSDT (Binance) or AAPL (stocks)." },
      { path: "initial_cash", label: "Starting capital", type: "number", suffix: "$", min: 10, step: 100 },
    ],
  },
  {
    id: "data", title: "Data Source", icon: "≈", open: true,
    fields: [
      { path: "data.kind", label: "Data", type: "segment", options: ["binance", "synthetic"],
        tip: "Binance = real market history (recommended). Synthetic = a generated path for stress-testing only." },
      // --- real Binance data ---
      { path: "data.symbol", label: "Binance symbol", type: "text",
        showIf: (s) => getPath(s, "data.kind") === "binance",
        tip: "Binance trading pair to download, e.g. BTCUSDT, ETHUSDT." },
      { path: "data.interval", label: "Candle interval", type: "select",
        options: [{ v: "1m", t: "1m" }, { v: "5m", t: "5m" }, { v: "15m", t: "15m" }, { v: "1h", t: "1h" }, { v: "4h", t: "4h" }, { v: "1d", t: "1d" }],
        showIf: (s) => getPath(s, "data.kind") === "binance" },
      { path: "data.max_candles", label: "Candles", type: "number", min: 100, step: 100,
        showIf: (s) => getPath(s, "data.kind") === "binance",
        tip: "How many recent candles to fetch (cached locally after the first run)." },
      // --- synthetic data ---
      { path: "data.regime", label: "Regime", type: "segment", options: ["range", "trend", "random"],
        showIf: (s) => getPath(s, "data.kind") !== "binance",
        tip: "Synthetic regime: ranging (grid-friendly), trending (hostile), or random walk." },
      { path: "data.n", label: "Bars", type: "number", min: 100, step: 100,
        showIf: (s) => getPath(s, "data.kind") !== "binance" },
      { path: "data.start_price", label: "Start price", type: "number", min: 1, step: 1,
        showIf: (s) => getPath(s, "data.kind") !== "binance" },
      { path: "data.sigma", label: "Volatility / bar", type: "number", scale: 100, suffix: "%", step: 0.1,
        showIf: (s) => getPath(s, "data.kind") !== "binance",
        tip: "Per-bar return standard deviation of the synthetic series." },
      { path: "data.seed", label: "Random seed", type: "number", step: 1,
        showIf: (s) => getPath(s, "data.kind") !== "binance" },
    ],
  },
  {
    id: "venue", title: "Venue & Costs", icon: "₿", open: true,
    fields: [
      { path: "venue", label: "Exchange / broker", type: "venue",
        tip: "Pick a venue to apply realistic fees and real lot/tick/min-notional filters." },
      { path: "fees.maker", label: "Maker fee", type: "number", scale: 100, suffix: "%", step: 0.01,
        tip: "Charged on resting limit fills (most grid fills)." },
      { path: "fees.taker", label: "Taker fee", type: "number", scale: 100, suffix: "%", step: 0.01,
        tip: "Charged on market + triggered-stop fills." },
      { path: "slippage.spread_frac", label: "Half spread", type: "number", scale: 100, suffix: "%", step: 0.01 },
      { path: "slippage.impact_frac", label: "Market impact", type: "number", scale: 100, suffix: "%", step: 0.01 },
    ],
  },
  {
    id: "grid", title: "Grid Geometry", icon: "⊞", open: true,
    fields: [
      { path: "grid.adaptive", label: "Adaptive range (ATR/rolling)", type: "toggle",
        tip: "Derive the grid range from recent volatility instead of fixed bounds." },
      { path: "grid.levels", label: "Levels", type: "number", min: 2, max: 200, step: 1 },
      { path: "grid.spacing", label: "Spacing", type: "segment", options: ["arithmetic", "geometric", "atr"] },
      { path: "grid.direction", label: "Direction", type: "segment", options: ["neutral", "long"],
        tip: "Long = buy dips / sell rallies of inventory you accumulate. Neutral = seed inventory and trade both sides. (Spot can't short.)" },
      { path: "grid.lower", label: "Lower bound", type: "number", step: 1, showIf: (s) => !getPath(s, "grid.adaptive") },
      { path: "grid.upper", label: "Upper bound", type: "number", step: 1, showIf: (s) => !getPath(s, "grid.adaptive") },
      { path: "grid.lookback", label: "Lookback bars", type: "number", min: 2, step: 10, showIf: (s) => getPath(s, "grid.adaptive") },
      { path: "grid.atr_period", label: "ATR period", type: "number", min: 2, step: 1, showIf: (s) => getPath(s, "grid.adaptive") },
      { path: "grid.atr_mult", label: "ATR multiple", type: "number", min: 0.1, step: 0.1, showIf: (s) => getPath(s, "grid.adaptive") },
      { path: "grid.recenter_drift_frac", label: "Recenter on drift", type: "number", scale: 100, suffix: "%", step: 1,
        tip: "Rebuild the grid when price drifts this far beyond the range. 0 = never." },
    ],
  },
  {
    id: "sizing", title: "Order Sizing", icon: "⊟", open: false,
    fields: [
      { path: "sizing.mode", label: "Mode", type: "select",
        options: [{ v: "fixed_quote", t: "Fixed quote ($)" }, { v: "fixed_base", t: "Fixed base (units)" }, { v: "percent_equity", t: "% of equity" }, { v: "martingale", t: "Martingale" }] },
      { path: "sizing.value", label: "Size value", type: "number", step: 1,
        tip: "Quote $ per rung, base units, or fraction of equity depending on mode." },
      { path: "sizing.martingale_factor", label: "Martingale factor", type: "number", min: 1, step: 0.1, showIf: (s) => getPath(s, "sizing.mode") === "martingale" },
      { path: "sizing.max_martingale_steps", label: "Max steps", type: "number", min: 0, step: 1, showIf: (s) => getPath(s, "sizing.mode") === "martingale" },
    ],
  },
  {
    id: "filters", title: "Filters & Risk", icon: "⛉", open: false,
    fields: [
      { path: "filter.kind", label: "Entry filter", type: "segment", options: ["none", "trend", "regime", "rsi"],
        tip: "Pause buys when a filter says the range is breaking (trend/regime) or price is overbought (rsi)." },
      { path: "filter.adx_threshold", label: "ADX threshold", type: "number", step: 1, showIf: (s) => getPath(s, "filter.kind") === "regime" },
      { path: "filter.oversold", label: "RSI oversold (buy below)", type: "number", min: 1, max: 99, step: 1, showIf: (s) => getPath(s, "filter.kind") === "rsi" },
      { path: "filter.overbought", label: "RSI overbought (sell above)", type: "number", min: 1, max: 99, step: 1, showIf: (s) => getPath(s, "filter.kind") === "rsi" },
      { path: "grid.stop_loss_frac", label: "Grid stop-loss", type: "number", scale: 100, suffix: "%", step: 1,
        tip: "Flatten everything if price falls this far below the range. 0 = off." },
      { path: "grid.take_profit_frac", label: "Per-rung take-profit", type: "number", scale: 100, suffix: "%", step: 0.1 },
      { path: "constraints.max_base_inventory", label: "Max base inventory", type: "number", step: 1,
        tip: "Hard cap on accumulated units — bounds the worst-case bag in a downtrend." },
      { path: "constraints.max_open_orders", label: "Max open orders", type: "number", step: 1 },
    ],
  },
  {
    id: "advanced", title: "Fill Model & Bootstrap", icon: "⇄", open: false,
    fields: [
      { path: "fill.mode", label: "Intrabar fills", type: "segment", options: ["conservative", "optimistic"],
        tip: "Conservative removes look-ahead bias (orders eligible next bar)." },
      { path: "fill.fill_on_touch", label: "Fill on touch (vs penetration)", type: "toggle" },
      { path: "fill.fill_gaps_at_open", label: "Fill gaps at open price", type: "toggle" },
      { path: "bootstrap.base_fraction", label: "Seed inventory", type: "number", scale: 100, suffix: "%", step: 5,
        tip: "Convert this share of starting capital to base inventory so a neutral grid can sell from bar 0." },
    ],
  },
];

function venueControl(field, spec, onChange) {
  const raw = getPath(spec, field.path) || "";
  const label = el("label", { class: "lbl" }, field.label, field.tip ? infoTip(field.tip) : null);
  const sel = el("select");
  for (const v of VENUES) {
    const o = el("option", { value: v.id }, v.name);
    if (raw === v.id) o.selected = true;
    sel.appendChild(o);
  }
  const note = el("div", { class: "field-note" });
  const cur = VENUES.find((v) => v.id === raw);
  if (cur) note.textContent = cur.note;
  sel.addEventListener("change", () => {
    const v = VENUES.find((x) => x.id === sel.value);
    setPath(spec, "venue", sel.value || undefined);
    if (v && v.fees) {
      setPath(spec, "fees.maker", v.fees.maker);
      setPath(spec, "fees.taker", v.fees.taker);
    }
    onChange();
  });
  return el("div", { class: "field" }, label, sel, note);
}

function control(field, spec, onChange) {
  const raw = getPath(spec, field.path);
  const scale = field.scale || 1;

  if (field.type === "venue") return venueControl(field, spec, onChange);

  if (field.type === "toggle") {
    const input = el("input", { type: "checkbox" });
    input.checked = !!raw;
    input.addEventListener("change", () => { setPath(spec, field.path, input.checked); onChange(); });
    return el("label", { class: "toggle" }, input, el("span", { class: "track" }),
      el("span", { class: "tg-label" }, field.label), field.tip ? infoTip(field.tip) : null);
  }

  const label = el("label", { class: "lbl" }, field.label, field.tip ? infoTip(field.tip) : null);

  if (field.type === "segment") {
    const seg = el("div", { class: "segment" });
    for (const opt of field.options) {
      const btn = el("button", { type: "button" }, opt);
      if (raw === opt) btn.classList.add("on");
      btn.addEventListener("click", () => { setPath(spec, field.path, opt); onChange(); });
      seg.appendChild(btn);
    }
    return el("div", { class: "field" }, label, seg);
  }

  if (field.type === "select") {
    const sel = el("select");
    for (const opt of field.options) {
      const v = typeof opt === "object" ? opt.v : opt;
      const t = typeof opt === "object" ? opt.t : opt;
      const o = el("option", { value: v }, t);
      if (String(raw) === String(v)) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => {
      let v = sel.value;
      if (!isNaN(Number(v)) && field.options.some((o) => typeof o === "object" && typeof o.v === "number")) v = Number(v);
      setPath(spec, field.path, v); onChange();
    });
    return el("div", { class: "field" }, label, sel);
  }

  // text / number
  const input = el("input", { type: field.type === "number" ? "number" : "text" });
  if (field.min != null) input.min = field.min;
  if (field.max != null) input.max = field.max;
  if (field.step != null) input.step = field.step;
  if (raw != null && raw !== "") input.value = field.type === "number" ? +(raw * scale).toFixed(6) : raw;
  input.addEventListener("input", () => {
    if (field.type === "number") {
      if (input.value === "") setPath(spec, field.path, undefined);
      else setPath(spec, field.path, parseFloat(input.value) / scale);
    } else {
      setPath(spec, field.path, input.value || undefined);
    }
    onChange();
  });

  const wrapped = field.suffix
    ? el("div", { class: "input-suffix" }, input, el("span", { class: "suffix" }, field.suffix))
    : input;
  return el("div", { class: "field" }, label, wrapped);
}

// Render fields, pairing simple numbers into two-column rows where it reads well.
export function renderFields(fields, spec, onChange) {
  const wrap = el("div");
  const visible = fields.filter((f) => !f.showIf || f.showIf(spec));
  let i = 0;
  while (i < visible.length) {
    const f = visible[i];
    const next = visible[i + 1];
    const pairable = (x) => x && (x.type === "number" || x.type === "text") && !x.suffixWide;
    if (pairable(f) && pairable(next)) {
      wrap.appendChild(el("div", { class: "field-row" }, control(f, spec, onChange), control(next, spec, onChange)));
      i += 2;
    } else {
      wrap.appendChild(control(f, spec, onChange));
      i += 1;
    }
  }
  return wrap;
}

// ---- live grid ladder preview --------------------------------------------
export function gridLadder(grid) {
  if (!grid || grid.error) {
    return el("div", { class: "text-mute", style: { fontSize: "12.5px", padding: "10px 0" } },
      grid?.error ? `Preview unavailable: ${grid.error}` : "Adjust the grid to preview the ladder.");
  }
  const levels = [...grid.levels].sort((a, b) => b - a); // high to low
  const center = grid.center;
  const wrap = el("div");

  const meta = el("div", { style: { display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-mute)", marginBottom: "8px" } },
    el("span", {}, `Range ${fmt.price(grid.lower)} – ${fmt.price(grid.upper)}`),
    el("span", {}, `${grid.levels.length} rungs · ${fmt.pct(grid.spacing_pct, 2)} step`));
  wrap.appendChild(meta);

  const ladder = el("div", { style: { display: "flex", flexDirection: "column", gap: "2px" } });
  for (const lv of levels) {
    const isBuy = lv < center;
    const color = isBuy ? "var(--pos)" : "var(--neg)";
    const soft = isBuy ? "var(--pos-soft)" : "var(--neg-soft)";
    const widthPct = 30 + 70 * ((lv - grid.lower) / (grid.upper - grid.lower || 1));
    ladder.appendChild(el("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
      el("span", { class: "mono", style: { fontSize: "11px", color: "var(--text-mute)", width: "62px", textAlign: "right" } }, fmt.price(lv)),
      el("div", { style: { flex: "1", height: "8px", borderRadius: "4px", background: soft, position: "relative" } },
        el("div", { style: { position: "absolute", left: "0", top: "0", bottom: "0", width: widthPct + "%", borderRadius: "4px", background: color, opacity: "0.55" } })),
      el("span", { class: "badge " + (isBuy ? "badge-good" : "badge-bad"), style: { fontSize: "10px" } }, isBuy ? "BUY" : "SELL")));
  }
  wrap.appendChild(ladder);
  wrap.appendChild(el("div", { class: "text-mute", style: { fontSize: "11.5px", marginTop: "8px" } },
    grid.adaptive ? `Adaptive range (${grid.source.replace("adaptive_", "")}) — recomputed from data.` : "Static range."));
  return wrap;
}
