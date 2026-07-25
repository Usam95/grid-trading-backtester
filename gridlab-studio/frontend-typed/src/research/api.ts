import type {
  BinanceEurResearchCatalog,
  BinanceDatasetPreview,
  BinanceDatasetRequest,
  CanonicalAdaptivePresentation,
  CanonicalAdaptiveRequest,
  DatasetManifest,
  FrozenProductionPanel,
  ManifestedBacktestBody,
  ProductionArchiveBacktestBody,
  OperatorControlsPresentation,
  ResearchPort,
  RunBacktestBody,
  SafetyPosturePresentation,
  StudioBacktestRun,
  StudioConfiguration,
} from "./port";

async function jsonResponse<T>(request: Promise<Response>): Promise<T> {
  const response = await request;
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(body?.detail ?? `Research service returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export class FastApiResearchClient implements ResearchPort {
  async getConfiguration(): Promise<StudioConfiguration> {
    return jsonResponse(fetch("/api/studio/configuration"));
  }

  async getEurCatalog(refresh = false): Promise<BinanceEurResearchCatalog> {
    return jsonResponse(
      fetch(`/api/studio/catalogs/binance/eur?refresh=${refresh ? "true" : "false"}`),
    );
  }

  async getProductionArchive(refresh = false): Promise<FrozenProductionPanel> {
    return jsonResponse<FrozenProductionPanel>(
      fetch(`/api/studio/archives/binance/eur?refresh=${refresh ? "true" : "false"}`),
    );
  }

  async synchronizeProductionArchive(): Promise<FrozenProductionPanel> {
    return jsonResponse<FrozenProductionPanel>(fetch("/api/studio/archives/binance/eur/synchronize", {
      method: "POST",
    }));
  }

  async characterizeCanonicalAdaptive(
    request: CanonicalAdaptiveRequest,
  ): Promise<CanonicalAdaptivePresentation> {
    return jsonResponse(
      fetch("/api/studio/canonical-adaptive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
  }

  async getSafetyPosture(): Promise<SafetyPosturePresentation> {
    return jsonResponse(fetch("/api/studio/safety-posture"));
  }

  async getOperatorControls(): Promise<OperatorControlsPresentation> {
    return jsonResponse(fetch("/api/studio/operator-controls"));
  }

  async executeBacktest(request: RunBacktestBody): Promise<StudioBacktestRun> {
    return jsonResponse(
      fetch("/api/studio/backtests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
  }

  async getBacktest(runId: string): Promise<StudioBacktestRun> {
    return jsonResponse(fetch(`/api/studio/backtests/${encodeURIComponent(runId)}`));
  }

  async previewProductionDataset(
    request: BinanceDatasetRequest,
  ): Promise<BinanceDatasetPreview> {
    return jsonResponse(fetch("/api/studio/datasets/binance/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }));
  }

  async importProductionDataset(previewId: string): Promise<DatasetManifest> {
    return jsonResponse(fetch("/api/studio/datasets/binance/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview_id: previewId }),
    }));
  }

  async executeManifestedBacktest(
    request: ManifestedBacktestBody,
  ): Promise<StudioBacktestRun> {
    return jsonResponse(fetch("/api/studio/backtests/manifested", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }));
  }

  async executeProductionArchiveBacktest(
    request: ProductionArchiveBacktestBody,
  ): Promise<StudioBacktestRun> {
    return jsonResponse(fetch("/api/studio/backtests/production-archive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }));
  }
}
