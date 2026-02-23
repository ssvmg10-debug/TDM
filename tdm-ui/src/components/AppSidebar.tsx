import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Database, Shield, Scissors, Eye, Factory,
  GitBranch, BookOpen, Server, Network, FileText, Settings,
  ChevronLeft, ChevronRight, Zap
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const navSections = [
  {
    label: "Core",
    items: [
      { label: "Dashboard", path: "/", icon: LayoutDashboard },
      { label: "Workflows", path: "/workflows", icon: GitBranch },
    ],
  },
  {
    label: "Data Management",
    items: [
      { label: "Dataset Catalog", path: "/datasets", icon: BookOpen },
      { label: "Environments", path: "/environments", icon: Server },
    ],
  },
  {
    label: "Admin",
    items: [
      { label: "Governance", path: "/governance", icon: Network },
      { label: "Audit Logs", path: "/audit-logs", icon: FileText },
      { label: "Settings", path: "/settings", icon: Settings },
    ],
  },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <motion.aside
      className="h-screen flex flex-col border-r border-border/50 bg-sidebar overflow-hidden flex-shrink-0"
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border/50 flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center glow-primary flex-shrink-0">
          <Zap className="w-4 h-4 text-primary" />
        </div>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-display font-bold text-foreground text-sm tracking-tight whitespace-nowrap"
          >
            TestForge
          </motion.span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {navSections.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50 px-2 mb-1.5">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = location.pathname === item.path;
                const linkContent = (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-all duration-200 group relative ${
                      isActive
                        ? "sidebar-active text-primary"
                        : "text-sidebar-foreground hover:text-foreground hover:bg-sidebar-accent"
                    }`}
                  >
                    <item.icon className={`w-4 h-4 flex-shrink-0 transition-colors ${isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`} />
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="whitespace-nowrap"
                      >
                        {item.label}
                      </motion.span>
                    )}
                    {isActive && (
                      <motion.div
                        layoutId="sidebar-indicator"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-primary rounded-r"
                        transition={{ duration: 0.3 }}
                      />
                    )}
                  </NavLink>
                );

                if (collapsed) {
                  return (
                    <Tooltip key={item.path} delayDuration={0}>
                      <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                      <TooltipContent side="right" className="bg-popover border-border">
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  );
                }

                return linkContent;
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Collapse */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-border/50 text-muted-foreground hover:text-foreground transition-colors"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </motion.aside>
  );
}
