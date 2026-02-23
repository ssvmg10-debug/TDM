import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, CheckCircle2, XCircle, AlertCircle, Info, Radio } from "lucide-react";
import { useEffect, useRef } from "react";

interface LogViewerProps {
  jobId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  /** When true, stops polling to avoid endless loop after job completes */
  isJobComplete?: boolean;
}

export function LogViewer({ jobId, autoRefresh = true, refreshInterval = 1000, isJobComplete = false }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["workflow-logs", jobId],
    queryFn: () => api.getWorkflowLogs(jobId),
    enabled: !!jobId,
    staleTime: 0,
    gcTime: 0,
    refetchInterval: (query) => {
      const d = query.state.data as { job_status?: string } | undefined;
      const jobDone = d?.job_status === "completed" || d?.job_status === "failed";
      return autoRefresh && !isJobComplete && !jobDone ? refreshInterval : false;
    },
    refetchOnWindowFocus: (query) => {
      const d = query.state.data as { job_status?: string } | undefined;
      const jobDone = d?.job_status === "completed" || d?.job_status === "failed";
      return autoRefresh && !isJobComplete && !jobDone;
    },
  });
  const jobDoneFromLogs = data?.job_status === "completed" || data?.job_status === "failed";
  const shouldPoll = autoRefresh && !!jobId && !isJobComplete && !jobDoneFromLogs;

  // Auto-scroll to bottom when new logs arrive (ScrollArea viewport is the parent)
  useEffect(() => {
    const el = scrollRef.current;
    const viewport = el?.parentElement;
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [data?.logs]);

  const getLevelIcon = (level: string) => {
    switch (level?.toLowerCase()) {
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "warning":
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case "success":
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const getLevelBadgeColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case "error":
        return "destructive";
      case "warning":
        return "outline";
      case "success":
      case "completed":
        return "default";
      default:
        return "secondary";
    }
  };

  const getStepBadgeColor = (step: string) => {
    const stepColors: Record<string, string> = {
      discover: "bg-blue-500/10 text-blue-500",
      pii: "bg-purple-500/10 text-purple-500",
      subset: "bg-green-500/10 text-green-500",
      mask: "bg-orange-500/10 text-orange-500",
      synthetic: "bg-cyan-500/10 text-cyan-500",
      provision: "bg-pink-500/10 text-pink-500",
    };
    return stepColors[step] || "bg-gray-500/10 text-gray-500";
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Workflow Logs</CardTitle>
          <CardDescription>Loading logs...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Workflow Logs</CardTitle>
          <CardDescription className="text-red-500">
            Error loading logs: {String(error)}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Workflow Logs</CardTitle>
            <CardDescription>
              Real-time execution logs for job {jobId.substring(0, 8)}...
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {shouldPoll && (
              <Badge variant="secondary" className="text-xs gap-1">
                <Radio className="w-3 h-3 animate-pulse" />
                Live
              </Badge>
            )}
            <Badge variant="outline" className="font-mono text-xs">
              {data?.logs?.length ?? 0} entries
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] w-full rounded-lg border bg-muted/20 p-4">
          <div ref={scrollRef} className="min-h-full">
          {Array.isArray(data?.logs) && data.logs.length > 0 ? (
            <div className="space-y-3">
              {data.logs.map((log: { timestamp?: string; step?: string; level?: string; message?: string; details?: Record<string, unknown> }, idx: number) => (
                <div
                  key={idx}
                  className="flex gap-3 p-3 rounded-lg bg-background border border-border hover:border-primary/50 transition-colors"
                >
                  <div className="flex-shrink-0 mt-1">
                    {getLevelIcon(log.level ?? "info")}
                  </div>
                  <div className="flex-1 space-y-2 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {log.step && (
                        <Badge
                          variant="outline"
                          className={`text-xs font-mono ${getStepBadgeColor(log.step)}`}
                        >
                          {log.step}
                        </Badge>
                      )}
                      <Badge variant={getLevelBadgeColor(log.level ?? "info") as "default" | "destructive" | "outline" | "secondary"} className="text-xs">
                        {log.level || "info"}
                      </Badge>
                      {(log.timestamp || (log as { created_at?: string }).created_at) && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {new Date((log.timestamp ?? (log as { created_at?: string }).created_at) ?? "").toLocaleTimeString()}
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-foreground break-words">{log.message ?? ""}</p>
                    {log.details && typeof log.details === "object" && Object.keys(log.details).length > 0 && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                          View details
                        </summary>
                        <pre className="mt-2 p-2 rounded bg-muted overflow-x-auto">
                          {JSON.stringify(log.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center space-y-2">
                <Info className="w-8 h-8 mx-auto opacity-50" />
                <p>No logs available yet</p>
                <p className="text-xs">Logs will appear here when the workflow starts</p>
              </div>
            </div>
          )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
