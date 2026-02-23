import { motion } from "framer-motion";
import {
  Play, ArrowUpRight, Clock, CheckCircle2, AlertTriangle, Loader2,
  Layers, BarChart3, Database, TrendingUp, CheckCircle, XCircle, Gauge, GitMerge
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
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
  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const { data: jobs = [] } = useQuery({ queryKey: ["jobs"], queryFn: () => api.listJobs() });

  const totalRows = datasets.reduce((acc, d) => {
    const rc = d.row_counts;
    if (rc && typeof rc === "object") return acc + Object.values(rc).reduce((a, b) => a + Number(b), 0);
    return acc;
  }, 0);
  const jobsByStatus = {
    completed: jobs.filter((j) => j.status === "completed" || j.status === "done").length,
    failed: jobs.filter((j) => j.status === "failed").length,
    running: jobs.filter((j) => j.status === "running").length,
    pending: jobs.filter((j) => j.status === "pending").length,
  };
  const totalJobs = jobs.length;
  const successRate = totalJobs > 0 ? Math.round((jobsByStatus.completed / totalJobs) * 100) : 100;
  const meaningfulMetrics = [
    { label: "Datasets Ready", value: String(datasets.length), sub: "available for provisioning", icon: Database, color: "text-primary" },
    { label: "Rows Generated", value: totalRows >= 1e6 ? `${(totalRows / 1e6).toFixed(1)}M` : totalRows >= 1e3 ? `${(totalRows / 1e3).toFixed(0)}K` : String(totalRows), sub: "total test data volume", icon: TrendingUp, color: "text-accent" },
    { label: "Workflows Completed", value: String(jobsByStatus.completed), sub: `${successRate}% success rate`, icon: CheckCircle, color: "text-success" },
    { label: "Failed Jobs", value: String(jobsByStatus.failed), sub: jobsByStatus.failed > 0 ? "needs attention" : "all clear", icon: XCircle, color: "text-destructive" },
    { label: "Running Jobs", value: String(jobsByStatus.running), sub: jobsByStatus.running > 0 ? "in progress now" : "idle", icon: Loader2, color: "text-primary" },
  ];
  const datasetsByType = datasets.reduce<Record<string, number>>((acc, d) => {
    acc[d.source_type] = (acc[d.source_type] || 0) + 1;
    return acc;
  }, {});

  const recentJobs = jobs.slice(0, 5);
  const recentDatasets = datasets.slice(0, 4);

  // Chart data: Jobs by status (pie)
  const jobStatusChartData = [
    { name: "Completed", value: jobsByStatus.completed, color: "hsl(var(--success))" },
    { name: "Failed", value: jobsByStatus.failed, color: "hsl(var(--destructive))" },
    { name: "Running", value: jobsByStatus.running, color: "hsl(var(--primary))" },
    { name: "Pending", value: jobsByStatus.pending, color: "hsl(var(--muted-foreground))" },
  ].filter((d) => d.value > 0);

  // Chart data: Job activity over last 7 days
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toISOString().slice(0, 10);
  });
  const jobActivityData = last7Days.map((day) => {
    const dayJobs = jobs.filter((j) => j.started_at && j.started_at.startsWith(day));
    return {
      date: day.slice(5),
      total: dayJobs.length,
      completed: dayJobs.filter((j) => j.status === "completed" || j.status === "done").length,
      failed: dayJobs.filter((j) => j.status === "failed").length,
    };
  });

  // Chart data: Datasets by type (bar)
  const typeColors: Record<string, string> = {
    synthetic: "hsl(var(--success))",
    subset: "hsl(var(--accent))",
    masked: "hsl(var(--warning))",
    synthetic_test_content: "hsl(var(--primary))",
    synthetic_crawled: "hsl(var(--chart-3))",
  };
  const datasetTypeChartData = Object.entries(datasetsByType).map(([type, count]) => ({
    type,
    count,
    fill: typeColors[type] || "hsl(var(--primary))",
  }));

  // Chart data: Row volume per dataset (top 6)
  const volumeChartData = datasets
    .slice(0, 6)
    .map((d) => {
      const rows = d.row_counts && typeof d.row_counts === "object"
        ? Object.values(d.row_counts).reduce((a, b) => a + Number(b), 0)
        : 0;
      return { name: (d.name || d.id.slice(0, 8)).slice(0, 12), rows };
    })
    .filter((d) => d.rows > 0);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-5 max-w-[1400px] mx-auto px-1">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-display font-bold text-foreground">Command Center</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Real-time overview of your test data operations</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>{datasets.length} datasets</span>
          <span>•</span>
          <span className="text-success">{jobsByStatus.completed} completed</span>
          {jobsByStatus.running > 0 && (
            <>
              <span>•</span>
              <span className="text-primary">{jobsByStatus.running} running</span>
            </>
          )}
          {jobsByStatus.failed > 0 && (
            <>
              <span>•</span>
              <span className="text-destructive">{jobsByStatus.failed} failed</span>
            </>
          )}
        </div>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {meaningfulMetrics.map((m) => (
          <div key={m.label} className="glass-card p-3 flex items-center gap-3">
            <div className={`w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0 ${m.color}`}>
              <m.icon className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-lg font-display font-bold text-foreground leading-tight">{m.value}</p>
              <p className="text-[11px] font-medium text-foreground truncate">{m.label}</p>
              <p className="text-[10px] text-muted-foreground truncate">{m.sub}</p>
            </div>
          </div>
        ))}
      </motion.div>

      <motion.div variants={item}>
        <h2 className="text-xs font-semibold text-foreground mb-2 uppercase tracking-wider">Quick Actions</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Link to="/workflows" className="glass-card-hover p-4 flex items-center gap-3 bg-gradient-to-br from-primary/15 to-primary/5 group">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Play className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground block truncate">Execute Workflow</span>
              <span className="text-[11px] text-muted-foreground line-clamp-2">Generate synthetic data, provision to tdm_target</span>
            </div>
            <ArrowUpRight className="w-4 h-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link to="/datasets" className="glass-card-hover p-4 flex items-center gap-3 bg-gradient-to-br from-accent/15 to-accent/5 group">
            <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
              <Layers className="w-5 h-5 text-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground block truncate">Browse Datasets</span>
              <span className="text-[11px] text-muted-foreground line-clamp-2">View and manage generated test data</span>
            </div>
            <ArrowUpRight className="w-4 h-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link to="/quality" className="glass-card-hover p-4 flex items-center gap-3 bg-gradient-to-br from-success/15 to-success/5 group">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center shrink-0">
              <Gauge className="w-5 h-5 text-success" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground block truncate">Quality Dashboard</span>
              <span className="text-[11px] text-muted-foreground line-clamp-2">Quality metrics & drift detection</span>
            </div>
            <ArrowUpRight className="w-4 h-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
          <Link to="/schema-fusion" className="glass-card-hover p-4 flex items-center gap-3 bg-gradient-to-br from-warning/15 to-warning/5 group">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center shrink-0">
              <GitMerge className="w-5 h-5 text-warning" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground block truncate">Schema Fusion</span>
              <span className="text-[11px] text-muted-foreground line-clamp-2">UI + API + DB + Domain fusion</span>
            </div>
            <ArrowUpRight className="w-4 h-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
        </div>
      </motion.div>

      {/* Charts Row */}
      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">Job Status Distribution</h2>
          <div className="h-[180px]">
            {jobStatusChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={jobStatusChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={65}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {jobStatusChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} stroke="hsl(var(--background))" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [v, "Jobs"]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">No job data yet</div>
            )}
          </div>
        </div>

        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">Job Activity (Last 7 Days)</h2>
          <div className="h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={jobActivityData} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--success))" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="hsl(var(--success))" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                  labelStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Legend />
                <Area type="monotone" dataKey="total" name="Total" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorTotal)" />
                <Area type="monotone" dataKey="completed" name="Completed" stroke="hsl(var(--success))" fillOpacity={1} fill="url(#colorCompleted)" />
                <Area type="monotone" dataKey="failed" name="Failed" stroke="hsl(var(--destructive))" fillOpacity={1} fill="url(#colorFailed)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">Datasets by Type</h2>
          <div className="h-[180px]">
            {datasetTypeChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={datasetTypeChartData} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis type="category" dataKey="type" width={80} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                  />
                  <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                    {datasetTypeChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill || "hsl(var(--primary))"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">No datasets yet</div>
            )}
          </div>
        </div>

        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">Data Volume (Top Datasets)</h2>
          <div className="h-[180px]">
            {volumeChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={volumeChartData} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                    formatter={(v: number) => [v >= 1000 ? `${(v / 1000).toFixed(1)}K` : v, "Rows"]}
                  />
                  <Bar dataKey="rows" name="Rows" fill="hsl(var(--accent))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">No volume data yet</div>
            )}
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <motion.div variants={item} className="lg:col-span-2 glass-card p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-foreground uppercase tracking-wider">Job Timeline</h2>
            <Link to="/workflows" className="text-xs text-primary hover:underline">View All</Link>
          </div>
          <div className="space-y-3">
            {recentJobs.length === 0 && <p className="text-sm text-muted-foreground">No jobs yet. Run discovery or subset to start.</p>}
            {recentJobs.map((job) => (
              <Link key={job.id} to="/workflows" className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors block">
                <StatusIcon status={job.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{job.operation} — {job.id.slice(0, 8)}</p>
                  <p className="text-[11px] text-muted-foreground">{formatTime(job.started_at)}</p>
                </div>
                {job.status === "running" && <span className="text-[10px] text-primary font-medium">Running</span>}
                {job.status === "completed" && <span className="text-[10px] text-success font-medium">Complete</span>}
                {job.status === "pending" && <span className="text-[10px] text-muted-foreground font-medium">Queued</span>}
                {job.status === "failed" && <span className="text-[10px] text-destructive font-medium">Failed</span>}
              </Link>
            ))}
          </div>
        </motion.div>

        <motion.div variants={item} className="glass-card p-4">
          <h2 className="text-xs font-semibold text-foreground mb-3 uppercase tracking-wider">Success Rate</h2>
          <div className="flex flex-col items-center justify-center h-[160px]">
            <div className="relative w-24 h-24">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="hsl(var(--muted))"
                  strokeWidth="3"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="hsl(var(--primary))"
                  strokeWidth="3"
                  strokeDasharray={`${successRate}, 100`}
                  strokeLinecap="round"
                  className="transition-all duration-700"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-foreground">{successRate}%</span>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5">Workflow success</p>
          </div>
        </motion.div>
      </div>

      <motion.div variants={item} className="glass-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold text-foreground uppercase tracking-wider">Recent Datasets</h2>
          <Link to="/datasets" className="text-xs text-primary hover:underline">View Catalog</Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {recentDatasets.length === 0 && <p className="col-span-4 text-xs text-muted-foreground">No datasets yet.</p>}
          {recentDatasets.map((ds) => {
            const rows = ds.row_counts && typeof ds.row_counts === "object"
              ? Object.values(ds.row_counts).reduce((a, b) => a + Number(b), 0)
              : 0;
            const rowsStr = rows >= 1e6 ? `${(rows / 1e6).toFixed(1)}M` : rows >= 1e3 ? `${(rows / 1e3).toFixed(0)}K` : String(rows);
            return (
              <Link key={ds.id} to="/datasets" className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer group block min-h-[72px]">
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
              </Link>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default Dashboard;
