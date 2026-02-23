import { motion } from "framer-motion";
import { BookOpen, Download, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function Badge({ type }: { type: string }) {
  const s: Record<string, string> = {
    masked: "bg-accent/10 text-accent",
    subset: "bg-primary/10 text-primary",
    synthetic: "bg-success/10 text-success",
    relational: "bg-warning/10 text-warning",
  };
  return <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${s[type] || "bg-muted text-muted-foreground"}`}>{type}</span>;
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

const DatasetCatalog = () => {
  const { data: datasets = [], isLoading } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const { data: lineageSteps } = useQuery({
    queryKey: ["lineage-steps"],
    queryFn: async () => ["Production DB", "Subset", "PII Mask", "Synthetic Augment", "Provisioned"],
  });

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Dataset Catalog</h1>
          <p className="text-sm text-muted-foreground mt-1">Browse, compare, and manage dataset versions</p>
        </div>
      </motion.div>

      {lineageSteps && lineageSteps.length > 0 && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Data Lineage</h2>
          <div className="flex items-center gap-2">
            {lineageSteps.map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <div className={`px-4 py-2 rounded-lg text-xs font-medium ${i === 0 ? "bg-primary/10 text-primary" : i === lineageSteps.length - 1 ? "bg-success/10 text-success" : "bg-muted text-foreground/70"}`}>{step}</div>
                {i < lineageSteps.length - 1 && <ArrowRight className="w-3 h-3 text-muted-foreground/40" />}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <motion.div variants={item} className="glass-card p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50">
              {["Dataset", "Type", "Rows", "Tables", "Created", ""].map((h) => (
                <th key={h} className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="py-4 text-muted-foreground">Loading...</td></tr>}
            {datasets.map((ds) => {
              const rows = ds.row_counts && typeof ds.row_counts === "object" ? Object.values(ds.row_counts).reduce((a, b) => a + Number(b), 0) : 0;
              const rowsStr = rows >= 1e6 ? `${(rows / 1e6).toFixed(1)}M` : rows >= 1e3 ? `${(rows / 1e3).toFixed(0)}K` : String(rows);
              return (
                <tr key={ds.id} className="border-b border-border/20 hover:bg-muted/20 transition-colors cursor-pointer">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <BookOpen className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="font-mono text-foreground">{ds.name || ds.id.slice(0, 8)}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4"><Badge type={ds.source_type} /></td>
                  <td className="py-3 pr-4 font-mono text-foreground/70">{rowsStr}</td>
                  <td className="py-3 pr-4 text-foreground/70">{ds.tables_count}</td>
                  <td className="py-3 pr-4 text-muted-foreground text-xs">{formatTime(ds.created_at)}</td>
                  <td className="py-3"><button className="p-1.5 rounded hover:bg-muted transition-colors"><Download className="w-3.5 h-3.5 text-muted-foreground" /></button></td>
                </tr>
              );
            })}
            {!isLoading && datasets.length === 0 && <tr><td colSpan={6} className="py-4 text-muted-foreground">No datasets yet.</td></tr>}
          </tbody>
        </table>
      </motion.div>
    </motion.div>
  );
};

export default DatasetCatalog;
