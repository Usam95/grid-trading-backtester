import type { components } from "../api/schema";

export type RunBacktestBody = components["schemas"]["RunBacktestBody"];
export type StudioBacktestRun = components["schemas"]["StudioBacktestRun"];
export type StudioConfiguration = components["schemas"]["StudioConfiguration"];
export type BinanceDatasetRequest = components["schemas"]["BinanceDatasetRequest"];
export type BinanceDatasetPreview = components["schemas"]["BinanceDatasetPreview"];
export type DatasetManifest = components["schemas"]["DatasetManifest"];
export type ManifestedBacktestBody = components["schemas"]["ManifestedBacktestBody"];
export type BinanceEurResearchCatalog = components["schemas"]["BinanceEurResearchCatalog"];

export interface ResearchPort {
  getConfiguration(): Promise<StudioConfiguration>;
  getEurCatalog(refresh?: boolean): Promise<BinanceEurResearchCatalog>;
  executeBacktest(request: RunBacktestBody): Promise<StudioBacktestRun>;
  getBacktest(runId: string): Promise<StudioBacktestRun>;
  previewProductionDataset(request: BinanceDatasetRequest): Promise<BinanceDatasetPreview>;
  importProductionDataset(previewId: string): Promise<DatasetManifest>;
  executeManifestedBacktest(request: ManifestedBacktestBody): Promise<StudioBacktestRun>;
}
