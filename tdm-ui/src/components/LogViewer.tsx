import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, CheckCircle2, XCircle, AlertCircle, Info } from "lucide-react";
import { useEffect, useRef } from "react";

interface LogViewerProps {
  jobId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function LogViewer({ jobId, autoRefresh = true, refreshInterval = 2000 }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const { data, isLoading, error } = useQuery({
    queryKey: ["workflow-logs", jobId],
    queryFn: () => api.getWorkflowLogs(jobId),
    refetchInterval: autoRefresh ? refreshInterval : false,
    enabled: !!jobId,
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
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
          <Badge variant="outline" className="font-mono text-xs">
            {data?.logs?.length || 0} entries
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] w-full rounded-lg border bg-muted/20 p-4" ref={scrollRef}>
          {data?.logs && data.logs.length > 0 ? (
            <div className="space-y-3">
              {data.logs.map((log, idx) => (
                <div
                  key={idx}
                  className="flex gap-3 p-3 rounded-lg bg-background border border-border hover:border-primary/50 transition-colors"
                >
                  <div className="flex-shrink-0 mt-1">
                    {getLevelIcon(log.level)}
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
                      <Badge variant={getLevelBadgeColor(log.level) as any} className="text-xs">
                        {log.level || "info"}
                      </Badge>
                      {log.timestamp && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-foreground break-words">{log.message}</p>
                    {log.details && Object.keys(log.details).length > 0 && (
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
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
