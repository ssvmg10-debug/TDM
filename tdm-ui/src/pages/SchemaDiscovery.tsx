import { motion } from "framer-motion";
import { Database, Play, Table, Columns, ChevronRight } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function RiskBadge({ level }: { level: string }) {
  const s: Record<string, string> = {
    High: "bg-destructive/10 text-destructive",
    Medium: "bg-warning/10 text-warning",
    Low: "bg-primary/10 text-primary",
    None: "bg-muted text-muted-foreground",
  };
  return <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${s[level] || s.None}`}>{level}</span>;
}

const SchemaDiscovery = () => {
  const [connectionString, setConnectionString] = useState("");
  const [selectedSchemaId, setSelectedSchemaId] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: schemas = [], isLoading: schemasLoading } = useQuery({
    queryKey: ["schemas"],
    queryFn: () => api.listSchemas(),
  });

  const { data: schemaDetail } = useQuery({
    queryKey: ["schema", selectedSchemaId],
    queryFn: () => api.getSchema(selectedSchemaId!),
    enabled: !!selectedSchemaId,
  });

  const schemaVersionId = schemaDetail?.id;
  const { data: columns = [] } = useQuery({
    queryKey: ["columns", schemaVersionId, selectedTable],
    queryFn: () => api.getTableColumns(schemaVersionId!, selectedTable!),
    enabled: !!schemaVersionId && !!selectedTable,
  });

  const discoverMutation = useMutation({
    mutationFn: (conn: string) =>
      api.discoverSchema({
        connection_string: conn,
        schemas: ["public"],
        include_stats: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schemas"] });
      setConnectionString("");
      toast.success("Schema discovery started");
    },
    onError: (err) => toast.error(err?.message ?? "Discovery failed"),
  });

  const tables = schemaDetail?.tables ?? [];
  if (tables.length && !selectedTable) setSelectedTable(tables[0]?.name ?? null);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Schema Discovery</h1>
          <p className="text-sm text-muted-foreground mt-1">Scan and explore connected database schemas</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            placeholder="postgresql://user:pass@host:5432/dbname"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            className="w-80 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm text-foreground placeholder:text-muted-foreground"
          />
          <button
            onClick={() => discoverMutation.mutate(connectionString)}
            disabled={!connectionString.trim() || discoverMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" /> Run Discovery
          </button>
        </div>
      </motion.div>

      <motion.div variants={item}>
        <h2 className="text-sm font-semibold text-foreground mb-3">Discovered Schemas</h2>
        {schemasLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        <div className="grid grid-cols-4 gap-3">
          {schemas.map((s) => (
            <div
              key={s.id}
              onClick={() => { setSelectedSchemaId(s.id); setSelectedTable(null); }}
              className={`glass-card-hover p-4 cursor-pointer border ${selectedSchemaId === s.id ? "border-primary" : ""}`}
            >
              <div className="flex items-center justify-between mb-3">
                <Database className="w-4 h-4 text-primary" />
              </div>
              <p className="text-sm font-mono font-medium text-foreground">{s.name}</p>
              <p className="text-xs text-muted-foreground mt-0.5">PostgreSQL · {s.tables_count} tables</p>
            </div>
          ))}
          {!schemasLoading && schemas.length === 0 && (
            <p className="col-span-4 text-sm text-muted-foreground">No schemas yet. Run discovery with a connection string above.</p>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-3 gap-6">
        <motion.div variants={item} className="col-span-1 glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Table className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Tables</h2>
          </div>
          <div className="space-y-1">
            {tables.map((t) => (
              <div
                key={t.id}
                onClick={() => setSelectedTable(t.name)}
                className={`flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/30 transition-colors cursor-pointer group ${selectedTable === t.name ? "bg-primary/5" : ""}`}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-foreground truncate">{t.name}</p>
                  <p className="text-[11px] text-muted-foreground">{t.row_count != null ? `${Number(t.row_count).toLocaleString()} rows` : "—"} · columns</p>
                </div>
                <ChevronRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            ))}
            {selectedSchemaId && tables.length === 0 && <p className="text-sm text-muted-foreground">No tables in this version.</p>}
          </div>
        </motion.div>

        <motion.div variants={item} className="col-span-2 glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Columns className="w-4 h-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">
              Column Details — <span className="font-mono text-primary">{selectedTable ?? "—"}</span>
            </h2>
          </div>
          <div className="space-y-2">
            {columns.map((col) => (
              <div key={col.id} className="flex items-center gap-4 p-3 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors">
                <div className="w-32 min-w-0">
                  <p className="text-sm font-mono text-foreground truncate">{col.name}</p>
                  <p className="text-[10px] text-muted-foreground">{col.data_type ?? col.inferred_type ?? "—"}</p>
                </div>
                <div className="ml-auto">
                  <RiskBadge level={col.inferred_type ? "Medium" : "None"} />
                </div>
              </div>
            ))}
            {selectedTable && columns.length === 0 && <p className="text-sm text-muted-foreground">No columns or loading.</p>}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default SchemaDiscovery;
