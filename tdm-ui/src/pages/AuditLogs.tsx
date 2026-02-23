import { motion } from "framer-motion";
import { FileText, Filter, Download } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

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

const AuditLogs = () => {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ["audit-logs"], queryFn: () => api.listAuditLogs() });

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-foreground">Audit Logs</h1>
          <p className="text-sm text-muted-foreground mt-1">Activity trail across the platform</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted text-sm text-foreground hover:bg-muted/80 transition-colors">
            <Filter className="w-3.5 h-3.5" /> Filter
          </button>
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted text-sm text-foreground hover:bg-muted/80 transition-colors">
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
            {logs.map((log) => (
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
            {!isLoading && logs.length === 0 && <tr><td colSpan={7} className="py-4 text-muted-foreground">No audit logs yet.</td></tr>}
          </tbody>
        </table>
      </motion.div>
    </motion.div>
  );
};

export default AuditLogs;
