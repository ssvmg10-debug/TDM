/**
 * TDM Backend API client. Set VITE_API_URL in .env (e.g. http://localhost:8002) or it defaults to that.
 */
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8002";
const API = `${BASE}/api/v1`;

async function request<T>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API}${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: { "Content-Type": "application/json", ...opts.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") return {} as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),

  // Discover
  discoverSchema: (body: { connection_string: string; schemas?: string[]; include_stats?: boolean }) =>
    api.post<{ schema_version_id?: string; message: string }>("/discover-schema", body),

  // Schemas
  listSchemas: () => api.get<{ id: string; name: string; latest_version_id?: string; tables_count: number }[]>("/schemas"),
  getSchema: (id: string) =>
    api.get<{
      id: string;
      schema_id: string;
      version_number: number;
      tables: { id: string; name: string; schema_name: string; row_count?: number }[];
      columns_count: number;
      relationships_count: number;
    }>(`/schema/${id}`),
  getSchemaVersionTables: (schemaVersionId: string) =>
    api.get<{ id: string; name: string; schema_name: string; row_count?: number }[]>(
      `/schema/version/${schemaVersionId}/tables`
    ),
  getTableColumns: (schemaVersionId: string, tableName: string) =>
    api.get<{ id: string; name: string; data_type?: string; inferred_type?: string; nullable: boolean }[]>(
      `/schema/version/${schemaVersionId}/tables/${tableName}/columns`
    ),

  // PII
  classifyPII: (body: { schema_version_id: string; use_llm?: boolean }) =>
    api.post<{ pii_map: { table: string; column: string; pii_type: string; confidence: number; technique: string }[] }>(
      "/pii/classify",
      body
    ),
  getPII: (schemaVersionId: string) =>
    api.get<{ pii_map: { table: string; column: string; pii_type: string; confidence: number; technique: string }[] }>(
      `/pii/${schemaVersionId}`
    ),

  // Subset
  subset: (body: {
    schema_version_id: string;
    connection_string?: string;
    root_table: string;
    filters?: Record<string, Record<string, unknown>>;
    max_rows_per_table?: Record<string, number>;
  }) => api.post<{ job_id: string; message: string }>("/subset", body),

  // Mask
  mask: (body: { dataset_version_id: string; rules?: Record<string, string> }) =>
    api.post<{ job_id: string; message: string }>("/mask", body),

  // Synthetic
  getSyntheticDomains: () =>
    api.get<{
      domains: {
        name: string;
        label: string;
        description: string;
        scenarios: string[];
        entities: string[];
      }[];
    }>("/synthetic/domains"),
  synthetic: (body: {
    schema_version_id?: string;
    test_case_urls?: string[];
    domain?: string;
    scenario?: string;
    row_counts?: Record<string, number>;
    // Legacy support
    domain_pack?: string;
    ui_urls?: string[];
  }) => api.post<{ job_id: string; message: string; entities?: string[] }>("/synthetic", body),

  // Provision
  provision: (body: {
    dataset_version_id: string;
    target_env: string;
    reset_env?: boolean;
    run_smoke_tests?: boolean;
  }) => api.post<{ job_id: string; status: string; message: string }>("/provision", body),

  // Datasets
  listDatasets: (params?: { source_type?: string }) => {
    const q = params?.source_type ? `?source_type=${params.source_type}` : "";
    return api.get<
      {
        id: string;
        name?: string;
        source_type: string;
        status: string;
        created_at?: string;
        row_counts?: Record<string, number>;
        tables_count: number;
        schema_version_id?: string;
      }[]
    >(`/datasets${q}`);
  },
  getDataset: (id: string) =>
    api.get<{
      id: string;
      name?: string;
      source_type: string;
      status: string;
      created_at?: string;
      row_counts?: Record<string, number>;
      tables_count: number;
    }>(`/dataset/${id}`),

  // Jobs
  listJobs: (params?: { operation?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.operation) sp.set("operation", params.operation);
    if (params?.status) sp.set("status", params.status);
    const q = sp.toString() ? `?${sp}` : "";
    return api.get<
      {
        id: string;
        operation: string;
        status: string;
        started_at?: string;
        finished_at?: string;
        result_json?: Record<string, unknown>;
      }[]
    >(`/jobs${q}`);
  },
  getJob: (id: string) =>
    api.get<{
      id: string;
      operation: string;
      status: string;
      started_at?: string;
      finished_at?: string;
      request_json?: Record<string, unknown>;
      result_json?: Record<string, unknown>;
      logs: { level: string; message: string; created_at?: string }[];
    }>(`/job/${id}`),

  // Lineage
  getLineage: (datasetId: string) =>
    api.get<{ source_type: string; source_id: string; target_type: string; target_id: string; operation?: string }[]>(
      `/lineage/dataset/${datasetId}`
    ),

  // Environments
  listEnvironments: () =>
    api.get<{ id: string; name: string; config_json?: Record<string, unknown> }[]>("/environments"),
  createEnvironment: (body: { name: string; connection_string?: string }) =>
    api.post<{ id: string; name: string }>("/environments", body),

  // Audit
  listAuditLogs: () =>
    api.get<
      { id: string; action: string; target: string; user: string; role: string; time: string; severity: string }[]
    >("/audit-logs"),

  // Workflow
  executeWorkflow: (body: {
    test_case_content?: string;
    test_case_urls?: string[];
    test_case_files?: string[];
    connection_string?: string;
    domain?: string;
    operations?: string[];
    config?: Record<string, any>;
    schema_version_id?: string;
    dataset_version_id?: string;
  }) =>
    api.post<{
      workflow_id: string;
      job_id: string;
      operations: Record<string, any>;
      overall_status: string;
      start_time: string;
      end_time?: string;
      error?: string;
    }>("/workflow/execute", body),
  getWorkflowTemplates: () =>
    api.get<{
      templates: {
        name: string;
        description: string;
        operations: string[];
        requires: string[];
        optional?: string[];
        example: Record<string, any>;
      }[];
    }>("/workflow/templates"),
  getWorkflowStatus: (workflowId: string) =>
    api.get<{
      workflow_id: string;
      job_id: string;
      status: string;
      start_time?: string;
      end_time?: string;
      details: Record<string, any>;
      error?: string;
      logs: {
        step: string;
        status: string;
        message: string;
        timestamp: string;
        details: Record<string, any>;
      }[];
    }>(`/workflow/status/${workflowId}`),

  getWorkflowLogs: (jobId: string) =>
    api.get<{
      job_id: string;
      logs: {
        timestamp: string;
        step: string;
        level: string;
        message: string;
        details: any;
      }[];
    }>(`/workflow/logs/${jobId}`),
};

export default api;
