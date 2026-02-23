import { motion } from "framer-motion";
import { Shield, AlertTriangle, CheckCircle2, Eye } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function ConfBar({ value }: { value: number }) {
  const pct = typeof value === "number" ? Math.round(value * 100) : 0;
  const color = pct >= 90 ? "bg-destructive" : pct >= 70 ? "bg-warning" : "bg-primary";
  return (
    <div className="flex items-center gap-2 w-24">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-muted-foreground w-7 text-right">{pct}%</span>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const s: Record<string, string> = {
    High: "bg-destructive/10 text-destructive",
    Medium: "bg-warning/10 text-warning",
    Low: "bg-primary/10 text-primary",
  };
  return <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${s[level] || "bg-muted text-muted-foreground"}`}>{level}</span>;
}

const PIIClassification = () => {
  const [schemaVersionId, setSchemaVersionId] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: schemas = [] } = useQuery({ queryKey: ["schemas"], queryFn: () => api.listSchemas() });
  const firstVersionId = schemas[0] ? (schemas[0].latest_version_id ?? "") : "";
  const effectiveVersionId = schemaVersionId || firstVersionId;

  const { data: piiResponse, isLoading } = useQuery({
    queryKey: ["pii", effectiveVersionId],
    queryFn: () => api.getPII(effectiveVersionId),
    enabled: !!effectiveVersionId,
  });

  const classifyMutation = useMutation({
    mutationFn: (svId: string) => api.classifyPII({ schema_version_id: svId, use_llm: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pii"] });
      toast.success("PII scan completed");
    },
    onError: (err) => toast.error(err?.message ?? "PII scan failed"),
  });

  const piiMap = piiResponse?.pii_map ?? [];
  const highRisk = piiMap.filter((r) => r.pii_type && ["email", "phone", "ssn", "credit_card"].includes(r.pii_type));
  const mediumRisk = piiMap.filter((r) => r.pii_type && !["email", "phone", "ssn", "credit_card"].includes(r.pii_type));

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">PII Classification</h1>
          <p className="text-sm text-muted-foreground mt-1">Detect and classify sensitive data across your schemas</p>
        </div>
        <div className="flex gap-2">
          <select
            value={effectiveVersionId}
            onChange={(e) => setSchemaVersionId(e.target.value)}
            className="px-3 py-2 rounded-lg bg-muted text-sm text-foreground border border-border"
          >
            {schemas.map((s) => (
              <option key={s.id} value={s.latest_version_id ?? s.id}>{s.name}</option>
            ))}
            {schemas.length === 0 && <option value="">No schema version</option>}
          </select>
          <button
            onClick={() => effectiveVersionId && classifyMutation.mutate(effectiveVersionId)}
            disabled={!effectiveVersionId || classifyMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Shield className="w-4 h-4" /> Scan All
          </button>
        </div>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-3 gap-4">
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-destructive" />
          </div>
          <div>
            <p className="text-xl font-display font-bold text-foreground">{highRisk.length}</p>
            <p className="text-xs text-muted-foreground">High Risk Fields</p>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
            <Eye className="w-5 h-5 text-warning" />
          </div>
          <div>
            <p className="text-xl font-display font-bold text-foreground">{mediumRisk.length}</p>
            <p className="text-xs text-muted-foreground">Medium Risk Fields</p>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5 text-success" />
          </div>
          <div>
            <p className="text-xl font-display font-bold text-foreground">{piiMap.length}</p>
            <p className="text-xs text-muted-foreground">Total Fields Classified</p>
          </div>
        </div>
      </motion.div>

      <motion.div variants={item} className="glass-card p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50">
              <th className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">Table</th>
              <th className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">Column</th>
              <th className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">Confidence</th>
              <th className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">Risk</th>
              <th className="text-left text-xs font-semibold text-muted-foreground pb-3">PII Type</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={5} className="py-4 text-muted-foreground">Loading...</td></tr>}
            {piiMap.map((row, i) => (
              <tr key={i} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                <td className="py-3 pr-4 font-mono text-foreground/80">{row.table}</td>
                <td className="py-3 pr-4 font-mono text-primary">{row.column}</td>
                <td className="py-3 pr-4"><ConfBar value={row.confidence} /></td>
                <td className="py-3 pr-4"><RiskBadge level={["email", "phone", "ssn", "credit_card"].includes(row.pii_type) ? "High" : "Medium"} /></td>
                <td className="py-3 text-muted-foreground">{row.pii_type}</td>
              </tr>
            ))}
            {!isLoading && piiMap.length === 0 && <tr><td colSpan={5} className="py-4 text-muted-foreground">No PII data. Run Scan All for a schema version.</td></tr>}
          </tbody>
        </table>
      </motion.div>
    </motion.div>
  );
};

export default PIIClassification;
