import { motion } from "framer-motion";
import { Settings as SettingsIcon, Key, Server, Users, Shield, Database, Globe, Bell } from "lucide-react";
import { useState } from "react";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const tabs = ["API Keys", "Environment", "Access", "Notifications"];
const tabIcons = [Key, Server, Users, Bell];

const apiKeys = [
  { name: "Production API Key", key: "tdm_prod_****...a3f2", created: "2024-01-15", lastUsed: "2h ago" },
  { name: "Staging API Key", key: "tdm_stg_****...b7e1", created: "2024-02-20", lastUsed: "1d ago" },
  { name: "CI/CD Token", key: "tdm_ci_****...c9d4", created: "2024-03-10", lastUsed: "30m ago" },
];

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Platform configuration and access management</p>
      </motion.div>

      <motion.div variants={item} className="glass-card p-1 flex gap-1">
        {tabs.map((tab, i) => {
          const Icon = tabIcons[i];
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(i)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                i === activeTab ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {tab}
            </button>
          );
        })}
      </motion.div>

      {activeTab === 0 && (
        <motion.div variants={item} className="glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-foreground">API Keys</h2>
            <button className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors">
              + New Key
            </button>
          </div>
          <div className="space-y-2">
            {apiKeys.map((k) => (
              <div key={k.name} className="flex items-center gap-4 p-4 rounded-lg bg-muted/20 hover:bg-muted/30 transition-colors">
                <Key className="w-4 h-4 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-foreground">{k.name}</p>
                  <p className="text-xs font-mono text-muted-foreground mt-0.5">{k.key}</p>
                </div>
                <div className="text-right">
                  <p className="text-[11px] text-muted-foreground">Last used: {k.lastUsed}</p>
                  <p className="text-[11px] text-muted-foreground">Created: {k.created}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {activeTab === 1 && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Environment Configuration</h2>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Default Source DB", value: "production_pg" },
              { label: "Masking Strategy", value: "Deterministic" },
              { label: "Subset Max Rows", value: "10,000,000" },
              { label: "Auto-provision", value: "Enabled" },
              { label: "Retention Policy", value: "30 days" },
              { label: "Parallel Workers", value: "8" },
            ].map((c) => (
              <div key={c.label} className="p-3 rounded-lg bg-muted/20">
                <p className="text-xs text-muted-foreground">{c.label}</p>
                <p className="text-sm font-medium text-foreground mt-1">{c.value}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {activeTab === 2 && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Access (Single User)</h2>
          <p className="text-sm text-muted-foreground">Single user mode — no RBAC. All features are available without roles or permissions. No login required for testing.</p>
        </motion.div>
      )}

      {activeTab === 3 && (
        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Notification Preferences</h2>
          <p className="text-sm text-muted-foreground">Configure alerts for job completions, failures, and governance events.</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default SettingsPage;
