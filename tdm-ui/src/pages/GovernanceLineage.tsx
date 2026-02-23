import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Lock, Clock, FileText, Database, Globe, Layers, Factory, Table2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const GovernanceLineage = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs() });
  const { data: lineage = [] } = useQuery({
    queryKey: ["lineage", selectedDatasetId],
    queryFn: () => api.getLineage(selectedDatasetId),
    enabled: !!selectedDatasetId,
  });
  const { data: jobLineageFull } = useQuery({
    queryKey: ["job-lineage-full", selectedJobId],
    queryFn: () => api.getJobLineageFull(selectedJobId),
    enabled: !!selectedJobId,
  });
  const { data: auditLogs = [] } = useQuery({ queryKey: ["audit-logs"], queryFn: () => api.listAuditLogs() });
  const workflowJobs = jobs.filter((j) => j.operation === "workflow");
  const events = auditLogs.slice(0, 5).map((log) => ({
    action: log.action,
    user: log.user,
    time: log.time,
  }));

  const lineageSteps =
    lineage.length > 0
      ? lineage.map((l, i) => ({
          label: `${l.source_type} → ${l.target_type}`,
          type: (i === 0 ? "source" : i === lineage.length - 1 ? "target" : "transform") as "source" | "target" | "transform",
        }))
      : [{ label: selectedDatasetId ? "No lineage for this dataset" : "Select a dataset to view lineage", type: "source" as const }];

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Governance & Lineage</h1>
        <p className="text-sm text-muted-foreground mt-1">Full lineage graph: Test Case → Schemas → Unified Schema → SDV → Provisioning → tdm_target</p>
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Full Lineage Graph</h2>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 flex-wrap">
          {[
            { label: "Test Case", icon: FileText, color: "bg-primary/10 text-primary border-primary/20" },
            { label: "UI Schema", icon: Globe, color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
            { label: "API Schema", icon: Database, color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
            { label: "DB Schema", icon: Database, color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
            { label: "Domain Pack", icon: Layers, color: "bg-amber-500/10 text-amber-600 border-amber-500/20" },
            { label: "Unified Schema", icon: Layers, color: "bg-purple-500/10 text-purple-600 border-purple-500/20" },
            { label: "SDV Generator", icon: Factory, color: "bg-accent/10 text-accent border-accent/20" },
            { label: "Generated Data", icon: Database, color: "bg-muted text-foreground/70 border-border/50" },
            { label: "Provisioning", icon: Table2, color: "bg-muted text-foreground/70 border-border/50" },
            { label: "tdm_target", icon: Table2, color: "bg-success/10 text-success border-success/20" },
          ].map((node, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 border ${node.color}`}>
                <node.icon className="w-3 h-3" />
                {node.label}
              </div>
              {i < 9 && <ArrowRight className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
            </div>
          ))}
        </div>
      </motion.div>

      <motion.div variants={item} className="glass-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-4">Job Lineage (Full)</h2>
        <div className="mb-3">
          <label className="text-xs text-muted-foreground block mb-1">Workflow Job</label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="w-full max-w-md px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
          >
            <option value="">Select workflow job</option>
            {workflowJobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.id.slice(0, 8)} — {j.status}
              </option>
            ))}
          </select>
        </div>
        {jobLineageFull && (
          <div className="space-y-3 p-3 rounded-lg bg-muted/20">
            {jobLineageFull.quality_score != null && (
              <p className="text-sm"><span className="text-muted-foreground">Quality Score:</span> {jobLineageFull.quality_score}</p>
            )}
            {jobLineageFull.fallbacks_used?.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Fallbacks used:</p>
                <div className="flex gap-2 flex-wrap">
                  {jobLineageFull.fallbacks_used.map((f: { step?: string }, i: number) => (
                    <span key={i} className="text-xs px-2 py-1 rounded bg-amber-500/10">{f.step}</span>
                  ))}
                </div>
              </div>
            )}
            {jobLineageFull.lineage?.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                {jobLineageFull.lineage.map((l, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="px-2 py-1 rounded text-xs bg-primary/10">{l.source_type} → {l.target_type}</span>
                    {i < (jobLineageFull.lineage?.length ?? 0) - 1 && <ArrowRight className="w-3 h-3" />}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </motion.div>

      <motion.div variants={item} className="glass-card p-5">
        <h2 className="text-sm font-semibold text-foreground mb-2">Dataset Lineage</h2>
        <div className="mb-3">
          <label className="text-xs text-muted-foreground block mb-1">Dataset</label>
          <select
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
            className="w-full max-w-md px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
          >
            <option value="">Select dataset</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>{d.name || d.id.slice(0, 8)} ({d.source_type})</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 flex-wrap">
          {lineageSteps.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`px-4 py-3 rounded-lg text-xs font-medium whitespace-nowrap ${
                step.type === "source" ? "bg-primary/10 text-primary border border-primary/20" :
                step.type === "target" ? "bg-success/10 text-success border border-success/20" :
                "bg-muted text-foreground/70 border border-border/50"
              }`}>{step.label}</div>
              {i < lineageSteps.length - 1 && <ArrowRight className="w-3 h-3 text-muted-foreground/40 flex-shrink-0" />}
            </div>
          ))}
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-6">
        <motion.div variants={item} className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Lock className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Access (Single User)</h2>
          </div>
          <p className="text-sm text-muted-foreground">No RBAC — single user mode. All features are available without role restrictions.</p>
        </motion.div>

        <motion.div variants={item} className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Recent Events</h2>
          </div>
          <div className="space-y-2">
            {events.length === 0 && <p className="text-sm text-muted-foreground">No events yet.</p>}
            {events.map((ev, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">{ev.action}</p>
                  <p className="text-[11px] text-muted-foreground">by {ev.user} · {ev.time}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default GovernanceLineage;
