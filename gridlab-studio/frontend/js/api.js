// Thin REST client for the gridlab-studio backend.

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

async function get(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  health: () => get("/api/health"),
  backtest: (spec, options = {}) => post("/api/backtest", { spec, options }),
  gridPreview: (spec) => post("/api/grid-preview", { spec }),
  gridSearch: (base, space, objective, top_k) =>
    post("/api/research/grid-search", { base, space, objective, top_k }),
  walkForward: (base, space, n_splits, objective) =>
    post("/api/research/walk-forward", { base, space, n_splits, objective }),
  monteCarlo: (base, method, n_sims, seed = 0) =>
    post("/api/research/monte-carlo", { base, method, n_sims, seed }),
  robustness: (base, space = {}, n_splits = 3, mc_sims = 800) =>
    post("/api/research/robustness", { base, space, n_splits, mc_sims }),

  // Download the standalone HTML report as a file.
  async downloadReport(spec) {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, options: { with_report: true } }),
    });
    if (!res.ok) throw new Error("report failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gridlab-report-${spec.symbol || "strategy"}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
