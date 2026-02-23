import { motion } from "framer-motion";
import { Play, CheckCircle2, XCircle, Loader2, Clock, Plus, Trash2, Database, Link2, Sparkles, Upload } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { LogViewer } from "@/components/LogViewer";

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

const WorkflowOrchestrator = () => {
  const queryClient = useQueryClient();
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs() });
  const { data: templates } = useQuery({ queryKey: ["workflow-templates"], queryFn: () => api.getWorkflowTemplates() });
  const { data: domains } = useQuery({ queryKey: ["synthetic-domains"], queryFn: () => api.getSyntheticDomains() });

  const [testCaseUrls, setTestCaseUrls] = useState<string[]>([""]);
  const [testCaseContent, setTestCaseContent] = useState("");
  const [connectionString, setConnectionString] = useState("postgresql://postgres:12345@localhost:5432/tdm");
  const [domain, setDomain] = useState("");
  const [selectedOps, setSelectedOps] = useState<string[]>(["discover", "pii", "subset", "mask", "synthetic", "provision"]);
  const [targetConnection, setTargetConnection] = useState("");
  const [rowCount, setRowCount] = useState("1000");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const executeWorkflowMutation = useMutation({
    mutationFn: (body: Parameters<typeof api.executeWorkflow>[0]) => api.executeWorkflow(body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setCurrentJobId(data.job_id);
    },
  });

  const addTestCaseUrl = () => setTestCaseUrls([...testCaseUrls, ""]);
  const removeTestCaseUrl = (idx: number) => setTestCaseUrls(testCaseUrls.filter((_, i) => i !== idx));
  const updateTestCaseUrl = (idx: number, value: string) => {
    const updated = [...testCaseUrls];
    updated[idx] = value;
    setTestCaseUrls(updated);
  };

  const toggleOp = (op: string) => {
    setSelectedOps(prev => prev.includes(op) ? prev.filter(o => o !== op) : [...prev, op]);
  };

  const runQuickSynthetic = () => {
    const filteredUrls = testCaseUrls.filter(u => u.trim());
    if (!domain) {
      alert("Please select a domain");
      return;
    }
    executeWorkflowMutation.mutate({
      test_case_content: testCaseContent || undefined,
      test_case_urls: filteredUrls.length > 0 ? filteredUrls : undefined,
      domain,
      operations: ["synthetic"],
      config: {
        synthetic: { row_counts: { "*": parseInt(rowCount) || 1000 } },
      },
    });
  };

  const runFullWorkflow = () => {
    // Only require connection string if doing discovery/pii/subset operations
    const needsConnection = selectedOps.some(op => ['discover', 'pii', 'subset'].includes(op));
    if (needsConnection && !connectionString) {
      alert("Please provide a database connection string for discovery/pii/subset operations");
      return;
    }
    const filteredUrls = testCaseUrls.filter(u => u.trim());
    executeWorkflowMutation.mutate({
      connection_string: connectionString,
      test_case_content: testCaseContent || undefined,
      test_case_urls: filteredUrls.length > 0 ? filteredUrls : undefined,
      domain: domain || undefined,
      operations: selectedOps.length > 0 ? selectedOps : undefined,
      config: {
        synthetic: { row_counts: { "*": parseInt(rowCount) || 1000 } },
        provision: targetConnection ? { target_connection: targetConnection, mode: "copy" } : undefined,
      },
    });
  };

  const loadTemplate = (templateName: string) => {
    const template = templates?.templates.find(t => t.name === templateName);
    if (!template) return;
    setSelectedOps(template.operations);
    // You can further populate form fields based on template.example
  };

  const operations = [
    { id: "discover", label: "Schema Discovery", icon: Database },
    { id: "pii", label: "PII Detection", icon: Link2 },
    { id: "subset", label: "Subsetting", icon: Database },
    { id: "mask", label: "Masking", icon: Link2 },
    { id: "synthetic", label: "Synthetic Gen", icon: Sparkles },
    { id: "provision", label: "Provisioning", icon: Upload },
  ];

  const workflowJobs = jobs.filter(j => j.operation === "workflow");

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Test Data Management Workflow</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Generate synthetic data, discover schemas, mask PII, subset data, and provision to environments - all in one place
          </p>
        </div>
      </motion.div>

      {executeWorkflowMutation.isSuccess && (
        <Alert className="bg-green-500/10 border-green-500">
          <AlertDescription>Workflow started successfully!</AlertDescription>
        </Alert>
      )}
      {executeWorkflowMutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{String(executeWorkflowMutation.error)}</AlertDescription>
        </Alert>
      )}

      <motion.div variants={item} className="glass-card p-6 space-y-6">
        <div>
          <h2 className="text-lg font-semibold">Execute Workflow</h2>
          <p className="text-sm text-muted-foreground">
            Paste your test case content and select operations to execute
          </p>
        </div>

        <div className="space-y-3">
          <Label>Test Case Content</Label>
          <p className="text-xs text-muted-foreground">
            Paste your complete test case here (Cucumber scenarios, Selenium scripts, manual test steps, etc.)
          </p>
          <textarea
            className="w-full min-h-[250px] p-3 rounded-lg bg-background border border-input font-mono text-sm"
            placeholder={`Example:
Feature: User Registration
  Scenario: Successful user registration
    Given I am on the registration page
    When I enter "John Doe" in the name field
    And I enter "john@example.com" in the email field
    And I enter "password123" in the password field
    And I click the "Register" button
    Then I should see "Registration successful"
    
Or paste Selenium code, API test cases, etc.`}
            value={testCaseContent}
            onChange={(e) => setTestCaseContent(e.target.value)}
          />
        </div>

        <div>
          <Label className="mb-3 block">Operations to Run</Label>
          <p className="text-xs text-muted-foreground mb-3">Select the TDM operations you want to execute</p>
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

        <div>
          <Label>Row Count</Label>
          <Input
            type="number"
            value={rowCount}
            onChange={(e) => setRowCount(e.target.value)}
            placeholder="1000"
            className="max-w-xs"
          />
        </div>

        <Button onClick={runFullWorkflow} disabled={executeWorkflowMutation.isPending} className="w-full" size="lg">
          {executeWorkflowMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Executing Workflow...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-2" />
              Execute Workflow
            </>
          )}
        </Button>
      </motion.div>

      <motion.div variants={item} className="glass-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Execution History</h2>
        <div className="space-y-2">
          {workflowJobs.length === 0 && <p className="text-sm text-muted-foreground">No workflow executions yet.</p>}
          {workflowJobs.map((j) => (
            <div 
              key={j.id} 
              className={`flex items-center gap-4 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors cursor-pointer ${currentJobId === j.id ? 'ring-2 ring-primary' : ''}`}
              onClick={() => setCurrentJobId(j.id)}
            >
              <NodeStatus status={j.status} />
              <span className="text-sm font-mono text-foreground flex-1">{j.id.slice(0, 8)}</span>
              <span className="text-xs text-muted-foreground">{formatTime(j.started_at)}</span>
              <Badge variant="outline">{j.status}</Badge>
            </div>
          ))}
        </div>
      </motion.div>

      {currentJobId && (
        <motion.div variants={item}>
          <LogViewer jobId={currentJobId} autoRefresh={true} refreshInterval={2000} />
        </motion.div>
      )}
    </motion.div>
  );
};

export default WorkflowOrchestrator;
