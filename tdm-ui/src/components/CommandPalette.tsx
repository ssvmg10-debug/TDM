import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, LayoutDashboard, Database, Shield, Scissors, Eye,
  Factory, GitBranch, BookOpen, Server, Network, FileText, Settings,
  Command, ArrowRight
} from "lucide-react";

const commands = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Schema Discovery", path: "/schema-discovery", icon: Database },
  { label: "PII Classification", path: "/pii-classification", icon: Shield },
  { label: "Subsetting Engine", path: "/subsetting", icon: Scissors },
  { label: "Masking Engine", path: "/masking", icon: Eye },
  { label: "Synthetic Data Factory", path: "/synthetic-data", icon: Factory },
  { label: "Workflow Orchestrator", path: "/workflows", icon: GitBranch },
  { label: "Dataset Catalog", path: "/datasets", icon: BookOpen },
  { label: "Environment Provisioning", path: "/environments", icon: Server },
  { label: "Governance & Lineage", path: "/governance", icon: Network },
  { label: "Audit Logs", path: "/audit-logs", icon: FileText },
  { label: "Settings", path: "/settings", icon: Settings },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      setOpen((prev) => !prev);
    }
    if (e.key === "Escape") setOpen(false);
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const select = (path: string) => {
    navigate(path);
    setOpen(false);
    setQuery("");
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="command-overlay flex items-start justify-center pt-[20vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={() => setOpen(false)}
        >
          <motion.div
            className="glass-card w-full max-w-lg p-2 border-primary/20"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-3 py-2 border-b border-border/50">
              <Search className="w-4 h-4 text-muted-foreground" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search commands..."
                className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              <kbd className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">ESC</kbd>
            </div>
            <div className="py-2 max-h-72 overflow-y-auto">
              {filtered.map((cmd) => (
                <button
                  key={cmd.path}
                  onClick={() => select(cmd.path)}
                  className="flex items-center gap-3 w-full px-3 py-2.5 text-sm text-foreground/80 hover:text-foreground hover:bg-primary/5 rounded-lg transition-colors group"
                >
                  <cmd.icon className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  <span className="flex-1 text-left">{cmd.label}</span>
                  <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 text-primary transition-opacity" />
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-6">No results found</p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function SearchBar() {
  const [, setOpen] = useState(false);

  const handleClick = () => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  };

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground bg-muted/50 border border-border/50 rounded-lg hover:border-primary/30 hover:text-foreground transition-all w-64"
    >
      <Search className="w-3.5 h-3.5" />
      <span className="flex-1 text-left text-xs">Search...</span>
      <div className="flex items-center gap-0.5">
        <kbd className="text-[10px] font-mono bg-muted px-1 py-0.5 rounded">⌘</kbd>
        <kbd className="text-[10px] font-mono bg-muted px-1 py-0.5 rounded">K</kbd>
      </div>
    </button>
  );
}
