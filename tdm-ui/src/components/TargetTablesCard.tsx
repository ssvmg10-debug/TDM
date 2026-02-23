/**
 * TargetTablesCard - Shows tables in tdm_target database.
 * Refreshes when workflows complete so users see provisioned data.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table2, RefreshCw } from "lucide-react";

interface TargetTablesCardProps {
  refreshTrigger?: number; // Increment to force refetch (e.g. when workflow completes)
}

export function TargetTablesCard({ refreshTrigger = 0 }: TargetTablesCardProps) {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["target-tables", refreshTrigger],
    queryFn: () => api.getTargetTables(),
    refetchInterval: 10000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">tdm_target Database</CardTitle>
          <CardDescription>Loading tables...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    const msg = String(error).includes("not reachable")
      ? String(error)
      : `Backend not reachable. ${String(error)}`;
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">tdm_target Database</CardTitle>
          <CardDescription className="text-destructive text-sm">
            {msg}
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
            <CardTitle className="text-lg flex items-center gap-2">
              <Table2 className="w-5 h-5 text-green-600" />
              tdm_target Database
            </CardTitle>
            <CardDescription>
              Tables provisioned from synthetic/subset/mask workflows
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${isFetching ? "animate-spin" : ""}`} />
            {isFetching ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {data?.tables?.length ? (
          <div className="flex flex-wrap gap-2">
            {data.tables.map((t) => (
              <Badge key={t} variant="secondary" className="font-mono">
                {t}
              </Badge>
            ))}
            <p className="text-xs text-muted-foreground w-full mt-2">
              {data.count} table{data.count !== 1 ? "s" : ""} in {data.database}
            </p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No tables yet. Run a workflow with synthetic + provision to create tables.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
