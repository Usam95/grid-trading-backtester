import type { components } from "../api/schema";

export type RunBacktestBody = components["schemas"]["RunBacktestBody"];
export type StudioBacktestRun = components["schemas"]["StudioBacktestRun"];
export type StudioConfiguration = components["schemas"]["StudioConfiguration"];

export interface ResearchPort {
  getConfiguration(): Promise<StudioConfiguration>;
  executeBacktest(request: RunBacktestBody): Promise<StudioBacktestRun>;
  getBacktest(runId: string): Promise<StudioBacktestRun>;
}
