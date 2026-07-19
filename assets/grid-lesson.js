(function () {
  "use strict";

  const money = (n) => Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const qty = (n) => Number(n).toLocaleString(undefined, { maximumFractionDigits: 6 });

  function geometric(lower, upper, count) {
    const ratio = Math.pow(upper / lower, 1 / (count - 1));
    return Array.from({ length: count }, (_, i) => lower * Math.pow(ratio, i));
  }

  function arithmetic(lower, upper, count) {
    const step = (upper - lower) / (count - 1);
    return Array.from({ length: count }, (_, i) => lower + step * i);
  }

  function renderLadder() {
    const lower = Number(document.getElementById("lower").value);
    const upper = Number(document.getElementById("upper").value);
    const count = Number(document.getElementById("rungs").value);
    const market = Number(document.getElementById("market").value);
    const quote = Number(document.getElementById("quote").value);
    const spacing = document.getElementById("spacing").value;
    const ladder = document.getElementById("ladder");
    const levels = spacing === "geometric" ? geometric(lower, upper, count) : arithmetic(lower, upper, count);
    const valid = market > lower && market < upper;
    let backing = 0;
    let buys = 0;
    let sells = 0;

    ladder.innerHTML = "";
    [...levels].reverse().forEach((price) => {
      const row = document.createElement("div");
      const atMarket = Math.abs(price - market) < 0.000001;
      let side = "inactive";
      if (price < market && !atMarket) { side = "buy"; buys += 1; }
      if (price > market && !atMarket) { side = "sell"; sells += 1; backing += quote / price; }
      row.className = `rung ${side === "inactive" ? "" : side}${atMarket ? " activation" : ""}`;
      row.innerHTML = `<span class="rung-price">${money(price)}</span><span class="market-marker">${Math.abs(price - market) === Math.min(...levels.map(v => Math.abs(v - market))) ? `market ${money(market)}` : ""}</span><span class="rung-side">${atMarket ? "inactive" : side}</span>`;
      ladder.appendChild(row);
    });

    document.getElementById("eligibility").textContent = valid ? "Eligible" : "Rejected";
    document.getElementById("eligibility").style.color = valid ? "var(--buy)" : "var(--sell)";
    document.getElementById("buyCount").textContent = buys;
    document.getElementById("sellCount").textContent = sells;
    document.getElementById("backing").textContent = `${qty(backing)} base`;
    document.getElementById("committed").textContent = `${money((buys + sells) * quote)} quote`;
    document.getElementById("rangeMessage").hidden = valid;
  }

  ["lower", "upper", "rungs", "market", "quote", "spacing"].forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.addEventListener("input", renderLadder);
  });
  if (document.getElementById("ladder")) renderLadder();

  const scenarios = {
    active: {
      title: "Active inside range",
      text: "Buy rungs rest below price and backed sell rungs rest above it. Fills pair inward by one rung.",
      current: "active"
    },
    low: {
      title: "Range-exhausted below",
      text: "All planned buys may be filled. No new buy is created below the lowest rung; valid in-range sells wait for recovery.",
      current: "exhausted"
    },
    pause: {
      title: "Exposure-reducing pause",
      text: "Buys are canceled and blocked. Inventory-reducing sells may remain. Resume requires reconciliation and explicit approval.",
      current: "paused"
    },
    stop: {
      title: "Operator stop",
      text: "All managed orders are canceled and late fills reconciled. You then choose retained holding or deliberate liquidation.",
      current: "closed"
    },
    emergency: {
      title: "Emergency stop",
      text: "All commands are blocked, all managed orders are canceled, state is reconciled, and inventory is retained by default.",
      current: "emergency"
    }
  };

  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-scenario]").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      const scenario = scenarios[button.dataset.scenario];
      document.getElementById("scenarioTitle").textContent = scenario.title;
      document.getElementById("scenarioText").textContent = scenario.text;
      document.querySelectorAll(".state-node").forEach((node) => node.classList.toggle("current", node.dataset.state === scenario.current));
    });
  });

  document.querySelectorAll(".question").forEach((question) => {
    const feedback = question.querySelector(".feedback");
    question.querySelectorAll(".answer").forEach((answer) => {
      answer.addEventListener("click", () => {
        question.querySelectorAll(".answer").forEach((a) => a.classList.remove("correct", "incorrect"));
        const correct = answer.dataset.correct === "true";
        answer.classList.add(correct ? "correct" : "incorrect");
        feedback.textContent = correct ? answer.dataset.explain : `Not quite. ${question.dataset.hint}`;
      });
    });
  });
})();
