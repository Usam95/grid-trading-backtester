export type OperationsConnection = {
  state: "not_configured";
  commandAuthority: "unavailable";
};

export interface OperationsPort {
  connection(): Promise<OperationsConnection>;
}
