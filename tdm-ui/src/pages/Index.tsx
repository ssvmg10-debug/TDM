import { motion } from "framer-motion";
import {
  Database, Server, Cpu, Activity, Play, Shield, Factory, Eye,
  ArrowUpRight, Clock, CheckCircle2, AlertTriangle, Loader2,
  TrendingUp, Layers, Globe, BarChart3
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function StatusIcon({ status }: { status: string }) {
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />;
  if (status === "completed" || status === "done") return <CheckCircle2 className="w-3.5 h-3.5 text-success" />;
  if (status === "pending") return <Clock className="w-3.5 h-3.5 text-muted-foreground" />;
  return <AlertTriangle className="w-3.5 h-3.5 text-warning" />;
}

function BadgeType({ type }: { type: string }) {
  const styles: Record<string, string> = {
    masked: "bg-accent/10 text-accent",
    subset: "bg-primary/10 text-primary",
    synthetic: "bg-success/10 text-success",
    relational: "bg-warning/10 text-warning",
  };
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${styles[type] || "bg-muted text-muted-foreground"}`}>
      {type}
    </span>
  );
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

const Dashboard = () => {
  const { data: schemas = [] } = useQuery({ queryKey: ["schemas"], queryFn: () => api.listSchemas() });
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs() });

  const totalRows = datasets.reduce((acc, d) => {
    const rc = d.row_counts;
    if (rc && typeof rc === "object") return acc + Object.values(rc).reduce((a, b) => a + Number(b), 0);
    return acc;
  }, 0);
  const piiCount = schemas.length ? 0 : 0; // could sum from PII endpoint if needed

  const healthCards = [
    { label: "Dataset Store", value: "Connected", status: "online", icon: Database, change: "Local" },
    { label: "Metadata DB", value: "Healthy", status: "online", icon: Server, change: "PostgreSQL" },
    { label: "Schemas", value: `${schemas.length}`, status: "online", icon: Cpu, change: "Discovered" },
    { label: "API", value: "Running", status: "online", icon: Activity, change: "Ready" },
  ];

  const analyticsCards = [
    { label: "Rows Processed", value: totalRows > 0 ? (totalRows >= 1e6 ? `${(totalRows / 1e6).toFixed(1)}M` : `${(totalRows / 1e3).toFixed(0)}K`) : "0", icon: TrendingUp, color: "text-primary" },
    { label: "Datasets Created", value: String(datasets.length), icon: Layers, color: "text-accent" },
    { label: "Environments", value: "—", icon: Globe, color: "text-success" },
    { label: "PII Fields", value: String(piiCount), icon: Shield, color: "text-warning" },
  ];

  const recentJobs = jobs.slice(0, 5);
  const recentDatasets = datasets.slice(0, 4);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Command Center</h1>
        <p className="text-sm text-muted-foreground mt-1">Real-time overview of your test data operations</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-4 gap-4">
        {healthCards.map((card) => (
          <div key={card.label} className="glass-card-hover p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-lg bg-primary/5 flex items-center justify-center">
                <card.icon className="w-4 h-4 text-primary" />
              </div>
              <div className={`status-${card.status}`} />
            </div>
            <p className="text-xs text-muted-foreground">{card.label}</p>
            <p className="text-lg font-display font-semibold text-foreground mt-0.5">{card.value}</p>
            <p className="text-[11px] text-muted-foreground mt-1">{card.change}</p>
          </div>
        ))}
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-4 gap-4">
        {analyticsCards.map((card) => (
          <div key={card.label} className="glass-card p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
              <card.icon className={`w-5 h-5 ${card.color}`} />
            </div>
            <div>
              <p className="text-xl font-display font-bold text-foreground">{card.value}</p>
              <p className="text-xs text-muted-foreground">{card.label}</p>
            </div>
          </div>
        ))}
      </motion.div>

      <motion.div variants={item}>
        <h2 className="text-sm font-semibold text-foreground mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3">
          <Link to="/workflows" className="glass-card-hover p-6 flex items-center gap-4 bg-gradient-to-br from-primary/20 to-primary/5 group">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <Play className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <span className="text-base font-semibold text-foreground block">Execute Workflow</span>
              <span className="text-xs text-muted-foreground">Generate synthetic data, discover schemas, mask PII, and more</span>
            </div>
            <ArrowUpRight className="w-4 h-4 ml-auto text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link to="/datasets" className="glass-card-hover p-6 flex items-center gap-4 bg-gradient-to-br from-accent/20 to-accent/5 group">
            <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center">
              <Layers className="w-6 h-6 text-accent" />
            </div>
            <div className="flex-1">
              <span className="text-base font-semibold text-foreground block">Browse Datasets</span>
              <span className="text-xs text-muted-foreground">View and manage generated test data</span>
            </div>
            <ArrowUpRight className="w-4 h-4 ml-auto text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
        </div>
      </motion.div>

      <div className="grid grid-cols-3 gap-6">
        <motion.div variants={item} className="col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-foreground">Job Timeline</h2>
            <Link to="/workflows" className="text-xs text-primary hover:underline">View All</Link>
          </div>
          <div className="space-y-3">
            {recentJobs.length === 0 && <p className="text-sm text-muted-foreground">No jobs yet. Run discovery or subset to start.</p>}
            {recentJobs.map((job) => (
              <div key={job.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                <StatusIcon status={job.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{job.operation} — {job.id.slice(0, 8)}</p>
                  <p className="text-[11px] text-muted-foreground">{formatTime(job.started_at)}</p>
                </div>
                {job.status === "running" && <span className="text-[10px] text-primary font-medium">Running</span>}
                {job.status === "completed" && <span className="text-[10px] text-success font-medium">Complete</span>}
                {job.status === "pending" && <span className="text-[10px] text-muted-foreground font-medium">Queued</span>}
                {job.status === "failed" && <span className="text-[10px] text-destructive font-medium">Failed</span>}
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Pipeline</h2>
          <div className="space-y-1">
            {["Schema Discovery", "PII Detection", "Subsetting", "Masking", "Provisioning"].map((label, i) => (
              <div key={label} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/30 transition-colors">
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono bg-muted text-muted-foreground">
                  {i + 1}
                </div>
                <span className="text-sm text-foreground">{label}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <motion.div variants={item} className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-foreground">Recent Datasets</h2>
          <Link to="/datasets" className="text-xs text-primary hover:underline">View Catalog</Link>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {recentDatasets.length === 0 && <p className="col-span-4 text-sm text-muted-foreground">No datasets yet.</p>}
          {recentDatasets.map((ds) => {
            const rows = ds.row_counts && typeof ds.row_counts === "object"
              ? Object.values(ds.row_counts).reduce((a, b) => a + Number(b), 0)
              : 0;
            const rowsStr = rows >= 1e6 ? `${(rows / 1e6).toFixed(1)}M` : rows >= 1e3 ? `${(rows / 1e3).toFixed(0)}K` : String(rows);
            return (
              <div key={ds.id} className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer group">
                <div className="flex items-center justify-between mb-2">
                  <BadgeType type={ds.source_type} />
                  <BarChart3 className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <p className="text-sm font-medium text-foreground font-mono truncate">{ds.name || ds.id.slice(0, 8)}</p>
                <div className="flex items-center gap-3 mt-2 text-[11px] text-muted-foreground">
                  <span>{rowsStr} rows</span>
                  <span>{ds.tables_count} tables</span>
                  <span className="ml-auto">{formatTime(ds.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default Dashboard;
