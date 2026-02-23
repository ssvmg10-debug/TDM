import { motion } from "framer-motion";
import { Play, CheckCircle2, XCircle, Loader2, Clock, Database, Link2, Sparkles, Upload, FileText, Info, Brain } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { LogViewer } from "@/components/LogViewer";
import { JobTracePanel } from "@/components/JobTracePanel";
import { TargetTablesCard } from "@/components/TargetTablesCard";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function NodeStatus({ status }: { status: string }) {
  if (status === "done" || status === "completed") return <CheckCircle2 className="w-4 h-4 text-green-500" />;
  if (status === "running") return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
  if (status === "failed") return <XCircle className="w-4 h-4 text-red-500" />;
  return <Clock className="w-4 h-4 text-gray-400" />;
}

function formatTime(iso: string | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 60000;
  if (diff < 1) return "just now";
  if (diff < 60) return `${Math.floor(diff)}m ago`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
  return `${Math.floor(diff / 1440)}d ago`;
}

function truncate(s: string, len: number) {
  if (!s) return "";
  return s.length > len ? s.slice(0, len) + "…" : s;
}

const WorkflowOrchestrator = () => {
  const queryClient = useQueryClient();
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const { data: jobs = [], error: jobsError } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs(), retry: 1 });
  const { data: templates } = useQuery({ queryKey: ["workflow-templates"], queryFn: () => api.getWorkflowTemplates(), retry: 1 });
  const { data: domains } = useQuery({ queryKey: ["synthetic-domains"], queryFn: () => api.getSyntheticDomains(), retry: 1 });

  const [testCaseUrls, setTestCaseUrls] = useState<string[]>([""]);
  const [testCaseContent, setTestCaseContent] = useState("");
  const [connectionString, setConnectionString] = useState("postgresql://postgres:12345@localhost:5432/tdm");
  const [domain, setDomain] = useState("");
  const [selectedOps, setSelectedOps] = useState<string[]>([
    "discover", "pii", "subset", "mask", "synthetic", "provision"
  ]);
  const [targetConnection, setTargetConnection] = useState("");
  const [rowCount, setRowCount] = useState("1000");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [analyzeHint, setAnalyzeHint] = useState<{ needs_synthetic_data: boolean; hint: string } | null>(null);
  const [intentResult, setIntentResult] = useState<{ operations: string[]; preferred_synthetic_mode: string } | null>(null);
  const logsSectionRef = useRef<HTMLDivElement>(null);

  // Debounced analyze of test case content
  useEffect(() => {
    if (!testCaseContent?.trim()) {
      setAnalyzeHint(null);
      return;
    }
    const t = setTimeout(() => {
      api.analyzeTestCase(testCaseContent).then((r) => setAnalyzeHint({ needs_synthetic_data: r.needs_synthetic_data, hint: r.hint })).catch(() => setAnalyzeHint(null));
    }, 600);
    return () => clearTimeout(t);
  }, [testCaseContent]);

  const classifyIntentMutation = useMutation({
    mutationFn: () =>
      api.classifyIntent({
        test_case_content: testCaseContent || undefined,
        test_case_urls: testCaseUrls.filter((u) => u.trim()).length > 0 ? testCaseUrls.filter((u) => u.trim()) : undefined,
        connection_string: connectionString || undefined,
        domain: domain || undefined,
      }),
    onSuccess: (data) => {
      setIntentResult({ operations: data.operations, preferred_synthetic_mode: data.preferred_synthetic_mode });
      setSelectedOps(data.operations);
    },
  });

  const executeWorkflowMutation = useMutation({
    mutationFn: (body: Parameters<typeof api.executeWorkflow>[0]) => api.executeWorkflow(body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["target-tables"] });
      queryClient.removeQueries({ queryKey: ["workflow-logs"] });
      setCurrentJobId(data.job_id);
      setRefreshTrigger((t) => t + 1);
    },
  });

  useEffect(() => {
    if (currentJobId && logsSectionRef.current) {
      logsSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [currentJobId]);

  const addTestCaseUrl = () => setTestCaseUrls([...testCaseUrls, ""]);
  const removeTestCaseUrl = (idx: number) => setTestCaseUrls(testCaseUrls.filter((_, i) => i !== idx));
  const updateTestCaseUrl = (idx: number, value: string) => {
    const updated = [...testCaseUrls];
    updated[idx] = value;
    setTestCaseUrls(updated);
  };

  const toggleOp = (op: string) => {
    setSelectedOps((prev) =>
      prev.includes(op) ? prev.filter((o) => o !== op) : [...prev, op]
    );
  };

  const runQuickSynthetic = () => {
    const filteredUrls = testCaseUrls.filter((u) => u.trim());
    if (!domain) {
      alert("Please select a domain");
      return;
    }
    executeWorkflowMutation.mutate({
      test_case_content: testCaseContent || undefined,
      test_case_urls: filteredUrls.length > 0 ? filteredUrls : undefined,
      domain,
      operations: ["synthetic", "provision"],
      config: {
        synthetic: { row_counts: { "*": parseInt(rowCount) || 1000 } },
        provision: { target_env: "default", run_smoke_tests: true },
      },
    });
  };

  const runFullWorkflow = () => {
    const needsConnection = selectedOps.some((op) =>
      ["discover", "pii", "subset"].includes(op)
    );
    if (needsConnection && !connectionString) {
      alert("Please provide a database connection string for discovery/pii/subset operations");
      return;
    }
    const filteredUrls = testCaseUrls.filter((u) => u.trim());
    executeWorkflowMutation.mutate({
      connection_string: connectionString,
      test_case_content: testCaseContent || undefined,
      test_case_urls: filteredUrls.length > 0 ? filteredUrls : undefined,
      domain: domain || undefined,
      operations: selectedOps.length > 0 ? selectedOps : undefined,
      config: {
        synthetic: { row_counts: { "*": parseInt(rowCount) || 1000 } },
        provision: {
          target_env: "default",
          run_smoke_tests: true,
          ...(targetConnection ? { target_connection: targetConnection, mode: "copy" } : {}),
        },
      },
    });
  };

  const loadTemplate = (templateName: string) => {
    const template = templates?.templates.find((t) => t.name === templateName);
    if (!template) return;
    setSelectedOps(template.operations);
  };

  const operations = [
    { id: "discover", label: "Schema Discovery", icon: Database },
    { id: "pii", label: "PII Detection", icon: Link2 },
    { id: "subset", label: "Subsetting", icon: Database },
    { id: "mask", label: "Masking", icon: Link2 },
    { id: "synthetic", label: "Synthetic Gen", icon: Sparkles },
    { id: "provision", label: "Provisioning", icon: Upload },
  ];

  const workflowJobs = jobs.filter((j) => j.operation === "workflow");

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-6 max-w-[1600px] mx-auto"
    >
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">
            Test Data Management Workflow
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generate synthetic data from test cases, provision to tdm_target, and trace which test produced which data
          </p>
        </div>
      </motion.div>

      {jobsError && (
        <Alert variant="destructive" className="border-red-500">
          <AlertDescription>
            <strong>Backend not reachable.</strong> {String(jobsError)} — Start the backend: <code className="text-xs bg-muted px-1 rounded">cd tdm-backend &amp;&amp; .\start_backend.ps1</code>
          </AlertDescription>
        </Alert>
      )}
      {executeWorkflowMutation.isSuccess && !jobsError && (
        <Alert className="bg-green-500/10 border-green-500">
          <AlertDescription>Workflow started. Logs and lineage will appear below.</AlertDescription>
        </Alert>
      )}
      {executeWorkflowMutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{String(executeWorkflowMutation.error)}</AlertDescription>
        </Alert>
      )}

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-6 space-y-6">
            <div>
              <h2 className="text-lg font-semibold">Execute Workflow</h2>
              <p className="text-sm text-muted-foreground">
                Paste your test case content and select operations. Data is provisioned to tdm_target.
              </p>
            </div>

            <div className="space-y-3">
              <Label>Test Case Content</Label>
              <p className="text-xs text-muted-foreground">
                Paste Cucumber scenarios, Selenium scripts, or manual test steps. Used for traceability.
              </p>
              <textarea
                className="w-full min-h-[220px] p-3 rounded-lg bg-background border border-input font-mono text-sm resize-y"
                placeholder={`Example:
navigate to https://example.com
Enter email as test@example.com
Enter firstname as John
Enter lastname as Doe
click on submit`}
                value={testCaseContent}
                onChange={(e) => setTestCaseContent(e.target.value)}
              />
              {analyzeHint && (
                <div className={`flex items-center gap-2 text-xs mt-2 p-2 rounded-lg ${analyzeHint.needs_synthetic_data ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400" : "bg-amber-500/10 text-amber-600 dark:text-amber-400"}`}>
                  <Info className="w-4 h-4 shrink-0" />
                  <span>{analyzeHint.hint}</span>
                </div>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <Label className="mb-0">Operations</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => classifyIntentMutation.mutate()}
                  disabled={classifyIntentMutation.isPending}
                >
                  {classifyIntentMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Brain className="w-4 h-4 mr-1" />
                      Classify Intent
                    </>
                  )}
                </Button>
              </div>
              {intentResult && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2 p-2 rounded-lg bg-primary/5 border border-primary/10">
                  <Brain className="w-4 h-4 shrink-0" />
                  <span>Recommended: {intentResult.operations.join(" → ")} · Mode: {intentResult.preferred_synthetic_mode}</span>
                </div>
              )}
              <p className="text-xs text-muted-foreground mb-3">
                Include provision to create tables in tdm_target
              </p>
              <div className="flex flex-wrap gap-2">
                {operations.map((op) => (
                  <Badge
                    key={op.id}
                    variant={selectedOps.includes(op.id) ? "default" : "outline"}
                    className="cursor-pointer px-3 py-2 text-sm"
                    onClick={() => toggleOp(op.id)}
                  >
                    <op.icon className="w-4 h-4 mr-2" />
                    {op.label}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex gap-4 items-end">
              <div>
                <Label>Row Count</Label>
                <Input
                  type="number"
                  value={rowCount}
                  onChange={(e) => setRowCount(e.target.value)}
                  placeholder="1000"
                  className="max-w-[120px] mt-1"
                />
              </div>
              <Button
                onClick={runFullWorkflow}
                disabled={executeWorkflowMutation.isPending}
                className="flex-1"
                size="lg"
              >
                {executeWorkflowMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Execute Workflow
                  </>
                )}
              </Button>
            </div>
          </div>

          <motion.div variants={item} className="glass-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Execution History</h2>
            <p className="text-xs text-muted-foreground mb-3">
              Click a job to see logs and lineage. {currentJobId && (
                <button onClick={() => setCurrentJobId(null)} className="text-primary hover:underline ml-1">Clear</button>
              )}
            </p>
            <div className="space-y-2 max-h-[280px] overflow-y-auto">
              {workflowJobs.length === 0 && (
                <p className="text-sm text-muted-foreground">No workflow executions yet.</p>
              )}
              {workflowJobs.map((j) => (
                <div
                  key={j.id}
                  className={`flex items-center gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors cursor-pointer border ${
                    currentJobId === j.id ? "ring-2 ring-primary border-primary/50" : "border-transparent"
                  }`}
                  onClick={() => setCurrentJobId(j.id)}
                >
                  <NodeStatus status={j.status} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-mono text-foreground">{j.id.slice(0, 8)}</span>
                    {(j as { request_json?: { test_case_summary?: string } }).request_json?.test_case_summary && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        <FileText className="w-3 h-3 inline mr-1" />
                        {truncate((j as { request_json?: { test_case_summary?: string } }).request_json!.test_case_summary!, 50)}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0">{formatTime(j.started_at)}</span>
                  <Badge variant="outline" className="shrink-0">{j.status}</Badge>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="space-y-6">
          <TargetTablesCard refreshTrigger={refreshTrigger} />
        </div>
      </motion.div>

      {currentJobId && (
        <motion.div ref={logsSectionRef} variants={item} className="space-y-6">
          <Tabs defaultValue="logs" className="w-full">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="logs">Logs</TabsTrigger>
              <TabsTrigger value="lineage">Data Lineage</TabsTrigger>
            </TabsList>
            <TabsContent value="logs" className="mt-4">
              <LogViewer
                jobId={currentJobId}
                autoRefresh={true}
                refreshInterval={2000}
                isJobComplete={
                  workflowJobs.some(
                    (j) => j.id === currentJobId && (j.status === "completed" || j.status === "failed")
                  )
                }
              />
            </TabsContent>
            <TabsContent value="lineage" className="mt-4">
              <JobTracePanel jobId={currentJobId} />
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </motion.div>
  );
};

export default WorkflowOrchestrator;
