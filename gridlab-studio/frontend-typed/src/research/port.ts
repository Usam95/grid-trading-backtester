import type { components } from "../api/schema";

export type RunBacktestBody = components["schemas"]["RunBacktestBody"];
export type StudioBacktestRun = components["schemas"]["StudioBacktestRun"];
export type StudioConfiguration = components["schemas"]["StudioConfiguration"];
export type BinanceDatasetRequest = components["schemas"]["BinanceDatasetRequest"];
export type BinanceDatasetPreview = components["schemas"]["BinanceDatasetPreview"];
export type DatasetManifest = components["schemas"]["DatasetManifest"];
export type ManifestedBacktestBody = components["schemas"]["ManifestedBacktestBody"];
export type ProductionArchiveBacktestBody =
  components["schemas"]["ProductionArchiveBacktestBody"];
export type BinanceEurResearchCatalog = components["schemas"]["BinanceEurResearchCatalog"];
export type FrozenProductionPanel = components["schemas"]["FrozenProductionPanel"];
export type CanonicalAdaptiveRequest = components["schemas"]["CanonicalAdaptiveRequest"];
export type CanonicalAdaptivePresentation =
  components["schemas"]["CanonicalAdaptivePresentation"];
export type SafetyPosturePresentation =
  components["schemas"]["SafetyPosturePresentation"];
export type OperatorControlsPresentation =
  components["schemas"]["OperatorControlsPresentation"];

export interface ResearchPort {
  getConfiguration(): Promise<StudioConfiguration>;
  getEurCatalog(refresh?: boolean): Promise<BinanceEurResearchCatalog>;
  getProductionArchive(refresh?: boolean): Promise<FrozenProductionPanel>;
  synchronizeProductionArchive(): Promise<FrozenProductionPanel>;
  characterizeCanonicalAdaptive(
    request: CanonicalAdaptiveRequest,
  ): Promise<CanonicalAdaptivePresentation>;
  getSafetyPosture(): Promise<SafetyPosturePresentation>;
  getOperatorControls(): Promise<OperatorControlsPresentation>;
  executeBacktest(request: RunBacktestBody): Promise<StudioBacktestRun>;
  getBacktest(runId: string): Promise<StudioBacktestRun>;
  previewProductionDataset(request: BinanceDatasetRequest): Promise<BinanceDatasetPreview>;
  importProductionDataset(previewId: string): Promise<DatasetManifest>;
  executeManifestedBacktest(request: ManifestedBacktestBody): Promise<StudioBacktestRun>;
  executeProductionArchiveBacktest(
    request: ProductionArchiveBacktestBody,
  ): Promise<StudioBacktestRun>;
}
