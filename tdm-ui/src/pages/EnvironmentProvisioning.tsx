import { motion } from "framer-motion";
import { Server, RefreshCw, Terminal } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const EnvironmentProvisioning = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [targetEnv, setTargetEnv] = useState("QA");
  const queryClient = useQueryClient();

  const { data: environments = [] } = useQuery({ queryKey: ["environments"], queryFn: () => api.listEnvironments() });
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const provisionMutation = useMutation({
    mutationFn: () => api.provision({ dataset_version_id: selectedDatasetId || datasets[0]?.id!, target_env: targetEnv, reset_env: true, run_smoke_tests: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Provision job started. Check job logs below.");
    },
    onError: (err) => toast.error(err?.message ?? "Provision failed"),
  });

  const { data: jobDetail } = useQuery({
    queryKey: ["job", provisionMutation.data?.job_id],
    queryFn: () => api.getJob(provisionMutation.data!.job_id),
    enabled: !!provisionMutation.data?.job_id,
    refetchInterval: 2000,
  });
  const logs = jobDetail?.logs ?? [];

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Environment Provisioning</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage and provision test environments</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-5 gap-3">
        {environments.length === 0 && <p className="col-span-5 text-sm text-muted-foreground">No environments. Add one in Settings or use default QA.</p>}
        {["QA", "SIT", "UAT", "PERF", "DEV"].map((name) => (
          <div key={name} className="glass-card-hover p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-display font-bold text-foreground">{name}</span>
              <div className="status-online" />
            </div>
            <p className="text-xs font-mono text-primary truncate">—</p>
            <div className="flex gap-1.5 mt-3">
              <button
                onClick={() => { setTargetEnv(name); setSelectedDatasetId(datasets[0]?.id ?? ""); provisionMutation.mutate(); }}
                disabled={!datasets[0] || provisionMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded bg-muted hover:bg-primary/10 hover:text-primary text-muted-foreground text-[10px] transition-colors disabled:opacity-50"
              >
                <RefreshCw className="w-3 h-3" /> Provision
              </button>
            </div>
          </div>
        ))}
      </motion.div>

      <motion.div variants={item} className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">Provision</h2>
        </div>
        <div className="flex gap-4 mb-4">
          <div>
            <label className="text-xs text-muted-foreground block">Dataset</label>
            <select value={selectedDatasetId} onChange={(e) => setSelectedDatasetId(e.target.value)} className="mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm w-64">
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name || d.id.slice(0, 8)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block">Target env</label>
            <select value={targetEnv} onChange={(e) => setTargetEnv(e.target.value)} className="mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm w-32">
              <option value="QA">QA</option>
              <option value="SIT">SIT</option>
              <option value="UAT">UAT</option>
              <option value="DEV">DEV</option>
            </select>
          </div>
          <button
            onClick={() => provisionMutation.mutate()}
            disabled={!selectedDatasetId || provisionMutation.isPending}
            className="self-end px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            Run Provision
          </button>
        </div>
        <div className="bg-background/50 rounded-lg p-4 font-mono text-xs space-y-1 max-h-64 overflow-y-auto">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-muted-foreground w-16 flex-shrink-0">{log.created_at ? new Date(log.created_at).toLocaleTimeString() : ""}</span>
              <span className={log.level === "success" ? "text-success" : log.level === "error" ? "text-destructive" : "text-foreground/70"}>{log.message}</span>
            </div>
          ))}
          {provisionMutation.isPending && logs.length === 0 && <p className="text-muted-foreground">Starting...</p>}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default EnvironmentProvisioning;
