// Formatting + tiny DOM helpers. No dependencies.

export const fmt = {
  pct(v, dp = 2) {
    if (v == null || !isFinite(v)) return "—";
    return (v * 100).toFixed(dp) + "%";
  },
  pctSigned(v, dp = 2) {
    if (v == null || !isFinite(v)) return "—";
    const s = (v * 100).toFixed(dp) + "%";
    return v > 0 ? "+" + s : s;
  },
  ratio(v, dp = 2) {
    if (v == null || !isFinite(v)) return "—";
    return v.toFixed(dp);
  },
  num(v, dp = 2) {
    if (v == null || !isFinite(v)) return "—";
    return Number(v).toLocaleString(undefined, { maximumFractionDigits: dp });
  },
  int(v) {
    if (v == null || !isFinite(v)) return "—";
    return Math.round(v).toLocaleString();
  },
  money(v, dp = 2) {
    if (v == null || !isFinite(v)) return "—";
    const sign = v < 0 ? "-" : "";
    return sign + "$" + Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
  },
  price(v) {
    if (v == null || !isFinite(v)) return "—";
    return Number(v).toLocaleString(undefined, { maximumFractionDigits: 4 });
  },
  date(iso) {
    if (!iso) return "—";
    try { return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }
    catch { return iso; }
  },
  // Format a value by metric format key.
  metric(v, kind) {
    switch (kind) {
      case "pct": return fmt.pct(v);
      case "ratio": return fmt.ratio(v);
      case "money": return fmt.money(v);
      case "int": return fmt.int(v);
      case "num": return fmt.num(v);
      default: return fmt.num(v);
    }
  },
};

export function colorForMetric(value, good) {
  // returns 'pos' | 'neg' | '' based on whether higher/lower is desirable
  if (value == null || !isFinite(value) || good === "neutral") return "";
  if (good === "high") return value > 0 ? "pos" : value < 0 ? "neg" : "";
  if (good === "low") return value <= 0 ? "pos" : "neg"; // for drawdown/fees (negative or small good)
  return "";
}

// ---- DOM helpers ----------------------------------------------------------

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "style" && typeof v === "object") Object.assign(node.style, v);
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  return node;
}

export function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Read/write a nested value by dotted path on an object.
export function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}
export function setPath(obj, path, value) {
  const parts = path.split(".");
  let node = obj;
  for (const p of parts.slice(0, -1)) {
    if (typeof node[p] !== "object" || node[p] == null) node[p] = {};
    node = node[p];
  }
  node[parts[parts.length - 1]] = value;
}

export function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

export function deepClone(o) { return JSON.parse(JSON.stringify(o)); }
