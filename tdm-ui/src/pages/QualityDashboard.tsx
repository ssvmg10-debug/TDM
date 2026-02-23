import { motion } from "framer-motion";
import { Gauge, BarChart3, TrendingUp, AlertTriangle, CheckCircle2, Database } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const QualityDashboard = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs() });

  const { data: qualityData, isLoading: qualityLoading } = useQuery({
    queryKey: ["quality", selectedDatasetId],
    queryFn: () => api.getDatasetQuality(selectedDatasetId),
    enabled: !!selectedDatasetId,
  });

  const workflowJobs = jobs.filter((j) => j.operation === "workflow" && (j.status === "completed" || j.status === "failed"));
  const completedWithContext = workflowJobs.filter(
    (j) => (j as { result_json?: { job_context?: { quality_score?: number } } }).result_json?.job_context?.quality_score != null
  );
  const avgQuality = completedWithContext.length > 0
    ? completedWithContext.reduce(
        (acc, j) => acc + ((j as { result_json?: { job_context?: { quality_score?: number } } }).result_json?.job_context?.quality_score ?? 0),
        0
      ) / completedWithContext.length
    : null;

  const metrics = [
    { label: "Avg Quality Score", value: avgQuality != null ? Math.round(avgQuality) : "—", icon: Gauge, color: "text-primary" },
    { label: "Jobs with Quality Data", value: completedWithContext.length, icon: BarChart3, color: "text-accent" },
    { label: "Total Workflows", value: workflowJobs.length, icon: TrendingUp, color: "text-success" },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Synthetic Quality Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Quality metrics, drift detection, and distribution analysis for synthetic data
        </p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="glass-card p-4 flex items-start gap-4">
            <div className={`w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0 ${m.color}`}>
              <m.icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-2xl font-display font-bold text-foreground">{String(m.value)}</p>
              <p className="text-xs font-medium text-foreground mt-0.5">{m.label}</p>
            </div>
          </div>
        ))}
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Compute Quality for Dataset
        </h2>
        <div className="flex gap-3 items-end mb-4">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground block mb-1">Select Dataset</label>
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="w-full max-w-md px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
              aria-label="Select dataset for quality computation"
            >
              <option value="">Select dataset...</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name || d.id.slice(0, 8)} ({d.source_type})
                </option>
              ))}
            </select>
          </div>
        </div>
        {qualityLoading && selectedDatasetId && (
          <p className="text-sm text-muted-foreground">Computing quality...</p>
        )}
        {qualityData && (
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24 rounded-full border-4 border-muted flex items-center justify-center overflow-hidden">
                <div
                  className="absolute inset-0 rounded-full transition-all"
                  style={{
                    background: `conic-gradient(hsl(var(--primary)) 0deg ${(qualityData.quality_score / 100) * 360}deg, hsl(var(--muted)) ${(qualityData.quality_score / 100) * 360}deg 360deg)`,
                  }}
                />
                <div className="absolute inset-2 rounded-full bg-background flex items-center justify-center">
                  <span className="text-xl font-bold">{qualityData.quality_score}</span>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium">Quality Score: {qualityData.quality_score}/100</p>
                <p className="text-xs text-muted-foreground">Null ratio, type consistency, pattern adherence</p>
              </div>
            </div>
            {qualityData.quality_report && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                {Object.entries(qualityData.quality_report).map(([k, v]) => (
                  <div key={k} className="p-2 rounded bg-muted/30">
                    <span className="text-muted-foreground">{k}:</span>{" "}
                    {typeof v === "object" ? JSON.stringify(v).slice(0, 40) + "..." : String(v)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <Gauge className="w-4 h-4" />
          Radial Quality Score (Overview)
        </h2>
          <div className="flex items-center gap-8">
          <div className="relative w-32 h-32 rounded-full border-4 border-muted flex items-center justify-center overflow-hidden">
            <div
              className="absolute inset-0 rounded-full transition-all"
              style={{
                background: avgQuality != null
                  ? `conic-gradient(hsl(var(--primary)) 0deg ${(avgQuality / 100) * 360}deg, hsl(var(--muted)) ${(avgQuality / 100) * 360}deg 360deg)`
                  : "hsl(var(--muted))",
              }}
            />
            <div className="absolute inset-2 rounded-full bg-background flex items-center justify-center">
              <span className="text-2xl font-bold">{avgQuality != null ? Math.round(avgQuality) : "—"}</span>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Quality score: 0–100</p>
            <p className="text-xs text-muted-foreground">
              Based on null ratio check, type consistency, pattern adherence.
            </p>
            <div className="flex items-center gap-2 mt-2 text-xs">
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span>Drift detection enabled</span>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Quality Metrics
        </h2>
        <p className="text-sm text-muted-foreground">
          KL divergence, correlation matrix similarity, null ratio check, type consistency,
          FK/PK integrity, pattern adherence, outlier detection, categorical & numeric drift.
        </p>
      </motion.div>
    </motion.div>
  );
};

export default QualityDashboard;
