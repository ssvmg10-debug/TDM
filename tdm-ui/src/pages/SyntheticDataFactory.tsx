import { motion } from "framer-motion";
import { Factory, Play, Link as LinkIcon, Database, FileCode } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const SyntheticDataFactory = () => {
  // Generation mode: 'schema' | 'domain' | 'testcase'
  const [mode, setMode] = useState<'schema' | 'domain' | 'testcase'>('domain');
  
  // Mode: schema
  const [schemaVersionId, setSchemaVersionId] = useState("");
  
  // Mode: domain
  const [selectedDomain, setSelectedDomain] = useState("");
  const [selectedScenario, setSelectedScenario] = useState("default");
  
  // Mode: testcase
  const [testCaseUrls, setTestCaseUrls] = useState<string[]>([""]);
  const [testCaseDomain, setTestCaseDomain] = useState("generic");
  
  // Common
  const [rowCount, setRowCount] = useState(1000);
  
  const queryClient = useQueryClient();

  const { data: schemas = [] } = useQuery({ queryKey: ["schemas"], queryFn: () => api.listSchemas() });
  const { data: domainsData } = useQuery({ queryKey: ["synthetic-domains"], queryFn: () => api.getSyntheticDomains() });
  
  const domains = domainsData?.domains || [];
  const currentDomain = domains.find(d => d.name === selectedDomain);
  const currentScenarios = currentDomain?.scenarios || ["default"];

  const syntheticMutation = useMutation({
    mutationFn: (requestBody: any) => api.synthetic(requestBody),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Synthetic generation started. Check Jobs or Datasets.");
    },
    onError: (err: any) => toast.error(err?.message ?? "Synthetic generation failed"),
  });

  const handleGenerate = () => {
    const baseRequest = { row_counts: { "*": rowCount } };
    
    if (mode === 'schema') {
      const effectiveSchemaVersionId = schemaVersionId || (schemas[0]?.latest_version_id ?? schemas[0]?.id ?? "");
      if (!effectiveSchemaVersionId) {
        toast.error("No schema version available. Run schema discovery first.");
        return;
      }
      syntheticMutation.mutate({ ...baseRequest, schema_version_id: effectiveSchemaVersionId });
    } else if (mode === 'domain') {
      if (!selectedDomain) {
        toast.error("Please select a domain.");
        return;
      }
      syntheticMutation.mutate({
        ...baseRequest,
        domain: selectedDomain,
        scenario: selectedScenario
      });
    } else if (mode === 'testcase') {
      const validUrls = testCaseUrls.filter(url => url.trim());
      if (validUrls.length === 0) {
        toast.error("Please provide at least one test case URL.");
        return;
      }
      syntheticMutation.mutate({
        ...baseRequest,
        test_case_urls: validUrls,
        domain: testCaseDomain,
        scenario: "default"
      });
    }
  };

  const addTestCaseUrl = () => setTestCaseUrls([...testCaseUrls, ""]);
  const updateTestCaseUrl = (index: number, value: string) => {
    const newUrls = [...testCaseUrls];
    newUrls[index] = value;
    setTestCaseUrls(newUrls);
  };
  const removeTestCaseUrl = (index: number) => {
    if (testCaseUrls.length > 1) {
      setTestCaseUrls(testCaseUrls.filter((_, i) => i !== index));
    }
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Synthetic Data Factory</h1>
          <p className="text-sm text-muted-foreground mt-1">Generate realistic test data dynamically</p>
        </div>
      </motion.div>

      {/* Mode Selection */}
      <motion.div variants={item} className="glass-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Generation Mode</h2>
        <div className="grid grid-cols-3 gap-3">
          <button
            onClick={() => setMode('domain')}
            className={`p-4 rounded-lg border-2 transition-all ${
              mode === 'domain'
                ? 'border-primary bg-primary/10'
                : 'border-border bg-muted/30 hover:border-primary/50'
            }`}
          >
            <Database className="w-5 h-5 mb-2 text-primary" />
            <p className="font-semibold text-sm">Domain Pack</p>
            <p className="text-xs text-muted-foreground mt-1">Pre-defined domain schemas</p>
          </button>
          
          <button
            onClick={() => setMode('testcase')}
            className={`p-4 rounded-lg border-2 transition-all ${
              mode === 'testcase'
                ? 'border-primary bg-primary/10'
                : 'border-border bg-muted/30 hover:border-primary/50'
            }`}
          >
            <LinkIcon className="w-5 h-5 mb-2 text-primary" />
            <p className="font-semibold text-sm">Test Case URLs</p>
            <p className="text-xs text-muted-foreground mt-1">Crawl and extract schema</p>
          </button>
          
          <button
            onClick={() => setMode('schema')}
            className={`p-4 rounded-lg border-2 transition-all ${
              mode === 'schema'
                ? 'border-primary bg-primary/10'
                : 'border-border bg-muted/30 hover:border-primary/50'
            }`}
          >
            <FileCode className="w-5 h-5 mb-2 text-primary" />
            <p className="font-semibold text-sm">Existing Schema</p>
            <p className="text-xs text-muted-foreground mt-1">From discovered schemas</p>
          </button>
        </div>
      </motion.div>

      {/* Configuration based on mode */}
      {mode === 'domain' && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Domain & Scenario</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {domains.map((domain) => (
                <div
                  key={domain.name}
                  onClick={() => {
                    setSelectedDomain(domain.name);
                    setSelectedScenario("default");
                  }}
                  className={`p-4 rounded-lg cursor-pointer border-2 transition-all ${
                    selectedDomain === domain.name
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50 bg-muted/30'
                  }`}
                >
                  <p className="text-sm font-semibold text-primary">{domain.label}</p>
                  <p className="text-xs text-muted-foreground mt-1">{domain.description}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Entities: {domain.entities.length}
                  </p>
                </div>
              ))}
            </div>
            
            {selectedDomain && currentScenarios.length > 1 && (
              <div>
                <label className="text-xs text-muted-foreground block mb-2">Scenario</label>
                <div className="flex gap-2">
                  {currentScenarios.map((scenario) => (
                    <button
                      key={scenario}
                      onClick={() => setSelectedScenario(scenario)}
                      className={`px-4 py-2 rounded-lg text-sm transition-all ${
                        selectedScenario === scenario
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted/50 hover:bg-muted'
                      }`}
                    >
                      {scenario}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {mode === 'testcase' && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Test Case URLs</h2>
          <div className="space-y-3">
            {testCaseUrls.map((url, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateTestCaseUrl(index, e.target.value)}
                  placeholder="https://example.com/test-case-page"
                  className="flex-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
                />
                {testCaseUrls.length > 1 && (
                  <button
                    onClick={() => removeTestCaseUrl(index)}
                    className="px-3 py-2 rounded-lg bg-destructive/10 text-destructive hover:bg-destructive/20 text-sm"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button
              onClick={addTestCaseUrl}
              className="px-4 py-2 rounded-lg bg-muted/50 hover:bg-muted text-sm"
            >
              + Add URL
            </button>
            
            <div className="mt-4">
              <label className="text-xs text-muted-foreground block mb-2">Domain Hint</label>
              <select
                value={testCaseDomain}
                onChange={(e) => setTestCaseDomain(e.target.value)}
                className="px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm w-64"
              >
                {domains.map((d) => (
                  <option key={d.name} value={d.name}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>
        </motion.div>
      )}

      {mode === 'schema' && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Select Schema</h2>
          <select
            value={schemaVersionId}
            onChange={(e) => setSchemaVersionId(e.target.value)}
            className="px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm w-full max-w-md"
          >
            <option value="">{schemas.length === 0 ? "No schemas — run discovery first" : "Select schema"}</option>
            {schemas.map((s) => (
              <option key={s.id} value={s.latest_version_id ?? s.id}>
                {s.name} ({s.tables_count} tables)
              </option>
            ))}
          </select>
        </motion.div>
      )}

      {/* Common Controls */}
      <motion.div variants={item} className="glass-card p-5">
        <div className="flex items-center justify-between">
          <div>
            <label className="text-xs text-muted-foreground block">Default Rows per Table</label>
            <input
              type="number"
              value={rowCount}
              onChange={(e) => setRowCount(Number(e.target.value))}
              className="mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm w-32"
              min="1"
              max="1000000"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={syntheticMutation.isPending}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            <Play className="w-4 h-4" /> Generate Synthetic Data
          </button>
        </div>
      </motion.div>

      {syntheticMutation.isSuccess && (
        <motion.div variants={item} className="glass-card p-4 bg-success/10 border border-success/20">
          <p className="text-sm text-success">Synthetic generation job started. Check Jobs or Dataset Catalog for results.</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default SyntheticDataFactory;

