import { motion } from "framer-motion";
import { FileText, Filter, Download } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

function SeverityBadge({ level }: { level: string }) {
  const s: Record<string, string> = {
    info: "bg-primary/10 text-primary",
    warn: "bg-warning/10 text-warning",
    error: "bg-destructive/10 text-destructive",
  };
  return <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${s[level] || "bg-muted text-muted-foreground"}`}>{level}</span>;
}

function exportToCsv(data: { id: string; action: string; target: string; user: string; role: string; time: string; severity: string }[]) {
  const headers = ["ID", "Action", "Target", "User", "Role", "Time", "Severity"];
  const rows = data.map((r) => [r.id, r.action, r.target, r.user, r.role, r.time, r.severity].map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","));
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const AuditLogs = () => {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ["audit-logs"], queryFn: () => api.listAuditLogs({ limit: 1000 }) });
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState<string | null>(null);

  const filtered = logs.filter((l) => {
    if (severityFilter && l.severity !== severityFilter) return false;
    if (actionFilter && !l.action.toLowerCase().includes(actionFilter.toLowerCase())) return false;
    return true;
  });

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Audit Logs</h1>
          <p className="text-sm text-muted-foreground mt-1">Activity trail across the platform</p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted text-sm text-foreground hover:bg-muted/80 transition-colors">
                <Filter className="w-3.5 h-3.5" /> Filter
                {(severityFilter || actionFilter) && (
                  <span className="ml-1 text-xs text-primary">Active</span>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Severity</div>
              <DropdownMenuItem onClick={() => setSeverityFilter(null)}>All</DropdownMenuItem>
              {["info", "warn", "error"].map((s) => (
                <DropdownMenuItem key={s} onClick={() => setSeverityFilter(s)}>{s}</DropdownMenuItem>
              ))}
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground mt-2">Action</div>
              <DropdownMenuItem onClick={() => setActionFilter(null)}>All</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setActionFilter("workflow")}>workflow</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setActionFilter("job")}>job</DropdownMenuItem>
              <div className="border-t my-1" />
              <DropdownMenuItem onClick={() => { setSeverityFilter(null); setActionFilter(null); }}>
                Clear all
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <button
            onClick={() => exportToCsv(filtered)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted text-sm text-foreground hover:bg-muted/80 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> Export
          </button>
        </div>
      </motion.div>

      <motion.div variants={item} className="glass-card p-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50">
              {["ID", "Action", "Target", "User", "Role", "Time", "Severity"].map((h) => (
                <th key={h} className="text-left text-xs font-semibold text-muted-foreground pb-3 pr-4">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={7} className="py-4 text-muted-foreground">Loading...</td></tr>}
            {filtered.map((log) => (
              <tr key={log.id} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                <td className="py-3 pr-4 font-mono text-muted-foreground text-xs">{log.id}</td>
                <td className="py-3 pr-4 text-foreground">{log.action}</td>
                <td className="py-3 pr-4 font-mono text-primary text-xs">{log.target}</td>
                <td className="py-3 pr-4 text-foreground/70">{log.user}</td>
                <td className="py-3 pr-4 text-muted-foreground text-xs">{log.role}</td>
                <td className="py-3 pr-4 text-muted-foreground text-xs font-mono">{log.time}</td>
                <td className="py-3"><SeverityBadge level={log.severity} /></td>
              </tr>
            ))}
            {!isLoading && filtered.length === 0 && <tr><td colSpan={7} className="py-4 text-muted-foreground">No audit logs yet.</td></tr>}
          </tbody>
        </table>
      </motion.div>
    </motion.div>
  );
};

export default AuditLogs;
