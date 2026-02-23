import { motion } from "framer-motion";
import { Scissors, Filter, Table, ArrowRight } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const steps = ["Source Database", "Select Tables", "Define Filters", "Run"];

const SubsettingEngine = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [schemaVersionId, setSchemaVersionId] = useState("");
  const [connectionString, setConnectionString] = useState("");
  const [rootTable, setRootTable] = useState("");
  const [maxRows, setMaxRows] = useState(10000);
  const queryClient = useQueryClient();

  const { data: schemas = [] } = useQuery({ queryKey: ["schemas"], queryFn: () => api.listSchemas() });
  const schemaDetail = useQuery({
    queryKey: ["schema", schemaVersionId || (schemas[0]?.id)],
    queryFn: () => api.getSchema(schemaVersionId || schemas[0]!.id),
    enabled: !!(schemaVersionId || schemas[0]?.id),
  });
  const tables = schemaDetail.data?.tables ?? [];
  const effectiveSchemaVersionId = schemaDetail.data?.id ?? "";

  const subsetMutation = useMutation({
    mutationFn: () =>
      api.subset({
        schema_version_id: effectiveSchemaVersionId,
        connection_string: connectionString || undefined,
        root_table: rootTable || tables[0]?.name || "users",
        max_rows_per_table: { [rootTable || tables[0]?.name || "users"]: maxRows },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Subset job started. Check Jobs or Datasets.");
    },
    onError: (err) => toast.error(err?.message ?? "Subset failed"),
  });

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Subsetting Engine</h1>
        <p className="text-sm text-muted-foreground mt-1">Create referentially-intact data subsets</p>
      </motion.div>

      <motion.div variants={item} className="glass-card p-4">
        <div className="flex items-center gap-2">
          {steps.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(i)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  i === currentStep ? "bg-primary/10 text-primary" : i < currentStep ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"
                }`}
              >
                <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] bg-current/10">{i < currentStep ? "✓" : i + 1}</span>
                {step}
              </button>
              {i < steps.length - 1 && <ArrowRight className="w-3 h-3 text-muted-foreground/30" />}
            </div>
          ))}
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-6">
        <motion.div variants={item} className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Table className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Select Root Table</h2>
          </div>
          <div className="space-y-2 mb-4">
            <label className="text-xs text-muted-foreground block">Schema (version)</label>
            <select
              value={schemaVersionId || (schemas[0]?.id ?? "")}
              onChange={(e) => setSchemaVersionId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
            >
              <option value="">{schemas.length === 0 ? "No schemas — run discovery first" : "Select schema"}</option>
              {schemas.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <label className="text-xs text-muted-foreground block mt-2">Root table</label>
            <select
              value={rootTable || (tables[0]?.name ?? "")}
              onChange={(e) => setRootTable(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
            >
              <option value="">{tables.length === 0 ? "No tables" : "Select table"}</option>
              {tables.map((t) => (
                <option key={t.id} value={t.name}>{t.name} {t.row_count != null ? `(${Number(t.row_count).toLocaleString()} rows)` : ""}</option>
              ))}
            </select>
            <label className="text-xs text-muted-foreground block mt-2">Max rows</label>
            <input type="number" value={maxRows} onChange={(e) => setMaxRows(Number(e.target.value))} className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm" />
          </div>
        </motion.div>

        <motion.div variants={item} className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Connection</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Connection string (optional; uses default if empty)</label>
              <input
                type="password"
                placeholder="postgresql://..."
                value={connectionString}
                onChange={(e) => setConnectionString(e.target.value)}
                className="w-full bg-muted/50 rounded-lg p-3 font-mono text-xs text-foreground placeholder:text-muted-foreground border border-border"
              />
            </div>
            <div className="glass-card p-4 bg-primary/5 border border-primary/20">
              <p className="text-xs text-muted-foreground">Run subset</p>
              <p className="text-sm text-foreground mt-1">Root: <span className="font-mono text-primary">{rootTable || tables[0]?.name || "—"}</span>, max {maxRows.toLocaleString()} rows</p>
              <button
                onClick={() => subsetMutation.mutate()}
                disabled={!effectiveSchemaVersionId || subsetMutation.isPending}
                className="mt-3 flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
              >
                <Scissors className="w-4 h-4" /> Run Subset
              </button>
              {subsetMutation.isSuccess && <p className="text-xs text-success mt-2">Job started. Check Jobs or Datasets.</p>}
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default SubsettingEngine;
