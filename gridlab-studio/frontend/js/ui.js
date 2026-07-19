// Reusable UI components built on the format.js DOM helpers.
import { el, clear, fmt, escapeHtml } from "./format.js";

// ---- toast notifications --------------------------------------------------
export function toast(message, kind = "info", ms = 3600) {
  const wrap = document.getElementById("toasts");
  const icon = { good: "✓", bad: "✕", info: "ℹ" }[kind] || "ℹ";
  const node = el("div", { class: `toast ${kind}` },
    el("span", { style: { fontWeight: 700 } }, icon),
    el("span", {}, message));
  wrap.appendChild(node);
  setTimeout(() => {
    node.style.transition = "opacity .25s, transform .25s";
    node.style.opacity = "0";
    node.style.transform = "translateX(20px)";
    setTimeout(() => node.remove(), 250);
  }, ms);
}

// ---- tooltip (info dot) ---------------------------------------------------
export function infoTip(text) {
  return el("span", { class: "tip" },
    el("span", { class: "ic" }, "?"),
    el("span", { class: "tip-pop" }, text));
}

// ---- badge ----------------------------------------------------------------
export function badge(text, kind = "muted") {
  return el("span", { class: `badge badge-${kind}` }, text);
}

// ---- KPI tile -------------------------------------------------------------
export function kpi({ label, value, sub, tone = "", tip }) {
  return el("div", { class: "kpi" },
    el("div", { class: "kpi-label" }, label, tip ? infoTip(tip) : null),
    el("div", { class: `kpi-value ${tone}` }, value),
    sub ? el("div", { class: "kpi-sub" }, sub) : null);
}

// ---- verdict banner -------------------------------------------------------
export function verdictBanner(verdict, result) {
  const cls = { good: "score-good", warn: "score-warn", bad: "score-bad" }[verdict.tone] || "score-warn";
  const period = result.start && result.end
    ? `${fmt.date(result.start)} → ${fmt.date(result.end)}` : "";
  return el("div", { class: "verdict-banner fade-in" },
    el("div", { class: `verdict-score ${cls}` }, `${verdict.score}`),
    el("div", { style: { flex: "1", minWidth: "0" } },
      el("div", { style: { display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" } },
        el("span", { style: { fontSize: "19px", fontWeight: "800" } }, `${verdict.label} configuration`),
        badge(result.symbol, "info"),
        badge(`${fmt.int(result.bars)} bars`, "muted")),
      el("div", { class: "card-sub", style: { marginTop: "4px" } },
        `Score ${verdict.score}/${verdict.max_score} · ${period} · ${fmt.int(result.n_closed_trades)} closed trades`)));
}

// ---- insight list ---------------------------------------------------------
export function insightList(insights) {
  const icons = { good: "✓", bad: "✕", warn: "!", info: "ℹ" };
  return el("div", { class: "stack", style: { gap: "10px" } },
    ...insights.map((i) =>
      el("div", { class: `insight ${i.tone}` },
        el("span", { class: "ico", style: { fontWeight: "800", color: `var(--${i.tone === "good" ? "pos" : i.tone === "bad" ? "neg" : i.tone === "warn" ? "warn" : "info"})` } }, icons[i.tone] || "ℹ"),
        el("span", {}, i.text))));
}

// ---- accordion section ----------------------------------------------------
export function section(title, icon, bodyNode, open = false) {
  const sec = el("div", { class: `section ${open ? "open" : ""}` });
  const head = el("div", { class: "section-head" },
    el("span", { class: "section-ico" }, icon),
    el("span", {}, title),
    el("span", { class: "chev" }, "›"));
  head.addEventListener("click", () => sec.classList.toggle("open"));
  sec.appendChild(head);
  sec.appendChild(el("div", { class: "section-body" }, bodyNode));
  return sec;
}

// ---- numbered step card (saas-style config wizard look) -------------------
export function numberedStep(n, title, sub, ...body) {
  return el("div", { class: "step-card" },
    el("div", { class: "step-head" },
      el("span", { class: "step-num" }, String(n)),
      el("div", { class: "step-heading" },
        el("div", { class: "step-title" }, title),
        sub ? el("div", { class: "step-sub" }, sub) : null)),
    el("div", { class: "step-body" }, ...body));
}

// ---- card -----------------------------------------------------------------
export function card(title, sub, ...body) {
  const head = title
    ? el("div", { class: "card-head" },
        el("div", {}, el("div", { class: "card-title" }, title), sub ? el("div", { class: "card-sub" }, sub) : null))
    : null;
  return el("div", { class: "card" }, head, ...body);
}

export function cardWithActions(title, sub, actions, ...body) {
  const head = el("div", { class: "card-head" },
    el("div", {}, el("div", { class: "card-title" }, title), sub ? el("div", { class: "card-sub" }, sub) : null),
    el("div", { style: { display: "flex", gap: "8px" } }, ...(actions || [])));
  return el("div", { class: "card" }, head, ...body);
}

// ---- table ----------------------------------------------------------------
// columns: [{key, label, fmt(row)->node|string, align, sortable}]
export function dataTable(columns, rows, opts = {}) {
  let sortKey = opts.sortKey || null;
  let sortDir = opts.sortDir || -1;
  const wrap = el("div", { class: "table-wrap " + (opts.scroll ? "tbl-scroll" : "") });
  const table = el("table", { class: "tbl" });
  const thead = el("thead");
  const tbody = el("tbody");

  function headerRow() {
    const tr = el("tr");
    for (const c of columns) {
      const arrow = sortKey === c.key ? (sortDir === -1 ? " ↓" : " ↑") : "";
      const th = el("th", { class: c.align === "right" ? "num" : "" }, c.label + arrow);
      if (c.sortable !== false) {
        th.addEventListener("click", () => {
          if (sortKey === c.key) sortDir = -sortDir; else { sortKey = c.key; sortDir = -1; }
          renderBody();
          clear(thead).appendChild(headerRow());
        });
      } else th.style.cursor = "default";
      tr.appendChild(th);
    }
    return tr;
  }

  function renderBody() {
    let data = rows.slice();
    if (sortKey) {
      data.sort((a, b) => {
        const va = a[sortKey], vb = b[sortKey];
        if (va == null) return 1; if (vb == null) return -1;
        if (typeof va === "string") return sortDir * va.localeCompare(vb);
        return sortDir * (va - vb);
      });
    }
    clear(tbody);
    for (const row of data) {
      const tr = el("tr");
      for (const c of columns) {
        const content = c.fmt ? c.fmt(row) : row[c.key];
        const td = el("td", { class: c.align === "right" ? "num" : "" });
        if (content instanceof Node) td.appendChild(content); else td.textContent = content == null ? "—" : content;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    if (data.length === 0) {
      tbody.appendChild(el("tr", {}, el("td", { colspan: columns.length, style: { textAlign: "center", color: "var(--text-mute)", padding: "26px" } }, "No rows")));
    }
  }

  thead.appendChild(headerRow());
  renderBody();
  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

// ---- metric grid ----------------------------------------------------------
export function metricGrid(metrics, meta, order) {
  const keys = order || Object.keys(meta);
  const grid = el("div", { class: "metric-list" });
  for (const k of keys) {
    const m = meta[k];
    if (!m) continue;
    const v = metrics[k];
    let tone = "";
    if (m.good === "high" && v != null) tone = v > 0 ? "pos" : v < 0 ? "neg" : "";
    if (m.good === "low" && v != null) tone = v <= 0 ? "pos" : "neg";
    grid.appendChild(el("div", { class: "metric-cell" },
      el("div", { class: "mk" }, m.label, infoTip(m.help)),
      el("div", { class: `mv ${tone}` }, fmt.metric(v, m.fmt))));
  }
  return grid;
}

// ---- skeleton -------------------------------------------------------------
export function skeleton(h = 80) {
  return el("div", { class: "skel", style: { height: h + "px", width: "100%" } });
}

export function emptyState(icon, title, sub) {
  return el("div", { class: "empty" },
    el("div", { class: "big" }, icon),
    el("h3", {}, title),
    el("div", {}, sub));
}

// ---- button with spinner --------------------------------------------------
export function runButton(label, onClick) {
  const btn = el("button", { class: "btn btn-primary" },
    el("span", { class: "btn-label" }, label));
  btn.addEventListener("click", async () => {
    if (btn.disabled) return;
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = "";
    btn.appendChild(el("span", { class: "spinner" }));
    btn.appendChild(el("span", {}, "Running…"));
    try { await onClick(); }
    finally { btn.disabled = false; btn.innerHTML = orig; }
  });
  return btn;
}

// ---- tabs -----------------------------------------------------------------
// tabs: [{ id, label, badge?, render() -> Node }]. Lazily renders the active
// panel and caches it; keeps the results area scannable instead of one scroll.
export function tabbed(tabs, { initial, onChange } = {}) {
  const cache = new Map();
  let active = initial || tabs[0].id;
  const bar = el("div", { class: "tabbar" });
  const panel = el("div", { class: "tab-panel" });

  function show(id) {
    active = id;
    for (const b of bar.children) b.classList.toggle("on", b.dataset.id === id);
    clear(panel);
    if (!cache.has(id)) cache.set(id, tabs.find((t) => t.id === id).render());
    const node = cache.get(id);
    panel.appendChild(node);
    // Build charts only after the panel is actually in the DOM (so canvases
    // have real dimensions). Run each panel's mount hook exactly once.
    if (node.__mount && !node.__mounted) {
      node.__mounted = true;
      requestAnimationFrame(() => node.__mount());
    }
    if (onChange) onChange(id);
  }
  for (const t of tabs) {
    const btn = el("button", { class: "tab", dataset: { id: t.id } },
      el("span", {}, t.label), t.badge != null ? el("span", { class: "tab-badge" }, String(t.badge)) : null);
    btn.addEventListener("click", () => show(t.id));
    bar.appendChild(btn);
  }
  const wrap = el("div", { class: "tabs" }, bar, panel);
  show(active);
  return wrap;
}

// ---- trust-score gauge ----------------------------------------------------
// A 0-100 semicircular gauge for the deployment trust score.
export function trustGauge(score, grade, { size = 168 } = {}) {
  const s = score == null ? 0 : Math.max(0, Math.min(100, score));
  const tone = s >= 75 ? "good" : s >= 60 ? "good" : s >= 40 ? "warn" : "bad";
  const color = `var(--${tone === "good" ? "pos" : tone === "warn" ? "warn" : "neg"})`;
  const r = 52, cx = 60, cy = 60;
  const circ = Math.PI * r;                 // half-circle length
  const off = circ * (1 - s / 100);
  const svg = `
    <svg viewBox="0 0 120 70" width="${size}" height="${size * 70 / 120}">
      <path d="M 8 60 A ${r} ${r} 0 0 1 112 60" fill="none"
            stroke="var(--surface-3)" stroke-width="11" stroke-linecap="round"/>
      <path d="M 8 60 A ${r} ${r} 0 0 1 112 60" fill="none"
            stroke="${color}" stroke-width="11" stroke-linecap="round"
            stroke-dasharray="${circ}" stroke-dashoffset="${off}"/>
    </svg>`;
  return el("div", { class: "gauge" },
    el("div", { class: "gauge-arc", html: svg },
      el("div", { class: "gauge-center" },
        el("div", { class: `gauge-num ${tone === "good" ? "pos" : tone === "warn" ? "warnc" : "neg"}` },
          score == null ? "—" : Math.round(s)),
        el("div", { class: "gauge-of" }, "/ 100"))),
    el("div", { class: `gauge-grade badge badge-${tone}` }, grade || "—"));
}

// ---- horizontal component bar (for trust breakdown) -----------------------
export function meterRow(label, value, { tip, suffix = "/100", note } = {}) {
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));
  const tone = v >= 66 ? "pos" : v >= 40 ? "warn" : "neg";
  return el("div", { class: "meter" },
    el("div", { class: "meter-top" },
      el("span", { class: "meter-label" }, label, tip ? infoTip(tip) : null),
      el("span", { class: "meter-val" }, value == null ? "—" : `${Math.round(v)}${suffix}`)),
    el("div", { class: "meter-track" },
      el("div", { class: `meter-fill ${tone}`, style: { width: v + "%" } })),
    note ? el("div", { class: "meter-note" }, note) : null);
}

// ---- data-source ribbon ---------------------------------------------------
export function dataRibbon(ds) {
  if (!ds) return null;
  const tone = ds.is_real ? "good" : "warn";
  const ico = ds.is_real ? "✓" : "⚠";
  const txt = ds.is_real
    ? `Real data — ${ds.label}${ds.venue ? ` · ${ds.venue} costs & filters` : ""}`
    : `${ds.label} — synthetic, for stress-testing only. Switch to Binance for live expectations.`;
  return el("div", { class: `ribbon ${tone}` },
    el("span", { class: "ribbon-ico" }, ico), el("span", {}, txt));
}
