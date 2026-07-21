import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type {
  ResearchPort,
  StudioBacktestRun,
  StudioConfiguration,
} from "./research/port";


const completedRun: StudioBacktestRun = {
  id: "run-typed-001",
  status: "completed",
  created_at: "2026-07-19T12:00:00Z",
  specification: { symbol: "ETHUSDT" },
  primary_result: {
    net_return: 0.0312,
    final_equity: 10312,
    max_drawdown: -0.018,
    completed_trades: 42,
    fees_paid: 14.2,
    verdict: "Strong",
  },
  result: {
    symbol: "ETHUSDT",
    bars: 300,
    initial_cash: 10000,
    final_equity: 10312,
    fees_paid: 14.2,
    metrics: {
      total_return: 0.0312,
      max_drawdown: -0.018,
      n_trades: 42,
      win_rate: 0.62,
    },
    verdict: { label: "Strong", tone: "good", score: 6, max_score: 7 },
    trades: [],
  },
};

const configuration: StudioConfiguration = {
  default_spec: {
    symbol: "BTCUSDT",
    market_type: "spot",
    initial_cash: 10000,
    grid: {
      levels: 12,
      lower: 92,
      upper: 108,
      spacing: "arithmetic",
      direction: "neutral",
      stop_loss_frac: 0.12,
    },
    sizing: { mode: "fixed_quote", value: 80 },
    fees: { maker: 0.001, taker: 0.001 },
    data: {
      kind: "synthetic",
      n: 300,
      start_price: 100,
      seed: 7,
      sigma: 0.012,
      regime: "range",
    },
    n_trials: 1,
  },
  spacing: ["geometric", "arithmetic"],
  data_regimes: ["range", "trend", "random"],
};


function researchPort(): ResearchPort {
  return {
    getConfiguration: vi.fn().mockResolvedValue(configuration),
    executeBacktest: vi.fn().mockResolvedValue(completedRun),
    getBacktest: vi.fn().mockResolvedValue(completedRun),
  };
}


describe("typed Studio shell", () => {
  it("keeps the trust boundary and permanent navigation visible", () => {
    render(<App research={researchPort()} />);

    expect(screen.getByText("RESEARCH")).toBeTruthy();
    expect(screen.getByText("LOCAL")).toBeTruthy();
    expect(screen.getByText("NO ONLINE TRADING AUTHORITY")).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Studio" }).textContent).toContain("Experiments");
    expect(screen.getByRole("navigation", { name: "Studio" }).textContent).toContain("Command Center");
  });

  it("configures and executes the migrated backtest through the Research port", async () => {
    const research = researchPort();
    render(<App research={research} />);

    expect(await screen.findByText("Market & Data")).toBeTruthy();
    expect(screen.getByText("Grid & Capital")).toBeTruthy();
    expect(screen.getByText("Costs & Execution")).toBeTruthy();
    expect(screen.getByText("Risk & Evaluation")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Symbol"), {
      target: { value: "ETHUSDT" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run backtest" }));

    await waitFor(() => expect(research.executeBacktest).toHaveBeenCalledOnce());
    expect(screen.getByText("+3.12%")).toBeTruthy();
    expect(screen.getByText("10,312.00 USDT")).toBeTruthy();
    expect(screen.getByText("run-typed-001")).toBeTruthy();
  });

  it("presents Operations without implying or exposing command authority", () => {
    render(<App research={researchPort()} />);

    fireEvent.click(screen.getByRole("button", { name: "Operations workspace" }));

    expect(screen.getByText("OPERATIONS")).toBeTruthy();
    expect(screen.getAllByText("GATEWAY NOT CONFIGURED")).toHaveLength(2);
    expect(screen.getAllByText("COMMAND AUTHORITY UNAVAILABLE")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /pause|stop|activate/i })).toBeNull();
  });
});
