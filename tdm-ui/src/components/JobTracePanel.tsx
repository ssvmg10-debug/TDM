/**
 * JobTracePanel - Shows full traceability: Test Case → Job → Dataset → tdm_target tables.
 * Production-grade: trace which test case produced which data.
 * Includes "What the workflow did" summary for user visibility.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Workflow, Database, Table2, ArrowRight, Hash, Gauge, CheckCircle2, XCircle, Info } from "lucide-react";

interface JobTracePanelProps {
  jobId: string;
}

export function JobTracePanel({ jobId }: JobTracePanelProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["job-trace", jobId],
    queryFn: () => api.getJobTrace(jobId),
    enabled: !!jobId,
  });
  const { data: jobDetail } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    enabled: !!jobId && !!data,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Data Lineage</CardTitle>
          <CardDescription>Loading traceability...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Data Lineage</CardTitle>
          <CardDescription className="text-destructive">
            {error ? String(error) : "Trace not available"}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const opsResult = (data as { operations_executed?: string[] }).operations_executed
    || (data as { operations?: string[] }).operations
    || [];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Workflow className="w-5 h-5" />
          Data Lineage
        </CardTitle>
        <CardDescription>
          Traceability: Test Case → Job → Dataset → tdm_target tables
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* What the workflow did - user-facing summary */}
        <div className="p-4 rounded-lg bg-primary/5 border border-primary/10 space-y-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Info className="w-4 h-4" />
            What the workflow did
          </h3>
          <ul className="text-sm space-y-1.5">
            {opsResult.length > 0 && (
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                <span>Executed: {opsResult.join(" → ")}</span>
              </li>
            )}
            {data.dataset_version_id && (
              <li className="flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-600 shrink-0" />
                <span>Created dataset: {data.dataset_version_id.slice(0, 8)}...</span>
              </li>
            )}
            {data.provisioned_tables?.length ? (
              <li className="flex items-center gap-2">
                <Table2 className="w-4 h-4 text-green-600 shrink-0" />
                <span>Provisioned to tdm_target: {data.provisioned_tables.join(", ")}</span>
              </li>
            ) : data.status === "completed" && (
              <li className="flex items-center gap-2 text-muted-foreground">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>No tables provisioned (subset/synthetic may have been skipped)</span>
              </li>
            )}
            {(data as { quality_score?: number }).quality_score != null && (
              <li className="flex items-center gap-2">
                <Gauge className="w-4 h-4 text-success shrink-0" />
                <span>Quality score: {(data as { quality_score?: number }).quality_score}</span>
              </li>
            )}
            {data.status === "failed" && (
              <li className="flex items-center gap-2 text-destructive">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>Workflow failed — check logs for details</span>
              </li>
            )}
          </ul>
          {jobDetail?.logs?.length ? (
            <div className="mt-2 pt-2 border-t border-border/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">Step log:</p>
              <div className="text-xs space-y-0.5 max-h-24 overflow-y-auto">
                {jobDetail.logs.slice(-8).map((l: { message?: string; level?: string }, i: number) => (
                  <div key={i} className={`${l.level === "error" ? "text-destructive" : "text-muted-foreground"}`}>
                    {l.message}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
        {/* Test Case */}
        {(data.test_case_summary || data.test_case_id) && (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border">
            <FileText className="w-5 h-5 text-primary mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">Test Case</p>
              {data.test_case_id && (
                <p className="text-xs text-muted-foreground font-mono flex items-center gap-1 mt-1">
                  <Hash className="w-3 h-3" />
                  {data.test_case_id}
                </p>
              )}
              <p className="text-sm text-foreground mt-1 break-words">
                {data.test_case_summary || "—"}
              </p>
            </div>
          </div>
        )}

        {/* Flow: Job → Dataset → Tables */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 border border-primary/20">
            <Workflow className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Job</span>
            <Badge variant="outline" className="font-mono text-xs">{data.job_id.slice(0, 8)}</Badge>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground" />
          {data.dataset_version_id ? (
            <>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <Database className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium">Dataset</span>
                <Badge variant="outline" className="font-mono text-xs">{data.dataset_version_id.slice(0, 8)}</Badge>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground" />
            </>
          ) : null}
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20">
            <Table2 className="w-4 h-4 text-green-600" />
            <span className="text-sm font-medium">tdm_target</span>
            {data.provisioned_tables?.length ? (
              <div className="flex gap-1 flex-wrap">
                {data.provisioned_tables.map((t) => (
                  <Badge key={t} variant="secondary" className="text-xs">
                    {t}
                    {data.row_counts?.[t] != null && ` (${data.row_counts[t]})`}
                  </Badge>
                ))}
              </div>
            ) : (
              <span className="text-xs text-muted-foreground">No tables provisioned</span>
            )}
          </div>
        </div>

        {data.operations?.length ? (
          <p className="text-xs text-muted-foreground">
            Operations: {data.operations.join(" → ")}
          </p>
        ) : null}

        {(data as { quality_score?: number }).quality_score != null && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-success/10 border border-success/20 mt-2">
            <Gauge className="w-4 h-4 text-success" />
            <span className="text-sm font-medium">Quality Score: {(data as { quality_score?: number }).quality_score}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
