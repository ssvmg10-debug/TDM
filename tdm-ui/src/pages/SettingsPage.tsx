import { motion } from "framer-motion";
import { Settings as SettingsIcon, Key, Server, Users, Shield, Database, Globe, Bell } from "lucide-react";
import { useState } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getNotificationPrefs, setNotificationPrefs } from "@/components/Layout";
import { toast } from "sonner";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const tabs = ["API Keys", "Environment", "Access", "Notifications"];
const tabIcons = [Key, Server, Users, Bell];

const API_KEYS_STORAGE = "tdm-api-keys";
function loadApiKeys(): { name: string; key: string; created: string; lastUsed: string }[] {
  try {
    const s = localStorage.getItem(API_KEYS_STORAGE);
    if (s) return JSON.parse(s);
  } catch {}
  return [
    { name: "Production API Key", key: "tdm_prod_****...a3f2", created: "2024-01-15", lastUsed: "2h ago" },
    { name: "Staging API Key", key: "tdm_stg_****...b7e1", created: "2024-02-20", lastUsed: "1d ago" },
    { name: "CI/CD Token", key: "tdm_ci_****...c9d4", created: "2024-03-10", lastUsed: "30m ago" },
  ];
}

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [apiKeys, setApiKeys] = useState(loadApiKeys);
  const [newKeyOpen, setNewKeyOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [prefs, setPrefs] = useState(getNotificationPrefs);

  const saveApiKeys = (keys: typeof apiKeys) => {
    setApiKeys(keys);
    localStorage.setItem(API_KEYS_STORAGE, JSON.stringify(keys));
  };

  const handleNewKey = () => {
    if (!newKeyName.trim()) {
      toast.error("Enter a key name");
      return;
    }
    const key = `tdm_${newKeyName.toLowerCase().replace(/\s/g, "_")}_****...${Math.random().toString(36).slice(-4)}`;
    const created = new Date().toISOString().slice(0, 10);
    const updated = [...apiKeys, { name: newKeyName.trim(), key, created, lastUsed: "just now" }];
    saveApiKeys(updated);
    setNewKeyName("");
    setNewKeyOpen(false);
    toast.success("API key created");
  };

  const updateNotifPref = (k: keyof typeof prefs, v: boolean) => {
    const next = setNotificationPrefs({ [k]: v });
    setPrefs(next);
  };

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
            <button
              onClick={() => setNewKeyOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
            >
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
          <p className="text-sm text-muted-foreground mb-6">Configure alerts for job completions, failures, and governance events.</p>
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/20">
              <div>
                <Label className="text-sm font-medium text-foreground">Job completions</Label>
                <p className="text-xs text-muted-foreground mt-0.5">Notify when a workflow or job completes successfully</p>
              </div>
              <Switch checked={prefs.jobComplete} onCheckedChange={(v) => updateNotifPref("jobComplete", v)} />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/20">
              <div>
                <Label className="text-sm font-medium text-foreground">Job failures</Label>
                <p className="text-xs text-muted-foreground mt-0.5">Notify when a workflow or job fails</p>
              </div>
              <Switch checked={prefs.jobFailed} onCheckedChange={(v) => updateNotifPref("jobFailed", v)} />
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/20">
              <div>
                <Label className="text-sm font-medium text-foreground">Governance events</Label>
                <p className="text-xs text-muted-foreground mt-0.5">Notify on PII changes, schema updates, or policy changes</p>
              </div>
              <Switch checked={prefs.governanceEvents} onCheckedChange={(v) => updateNotifPref("governanceEvents", v)} />
            </div>
          </div>
        </motion.div>
      )}

      <Dialog open={newKeyOpen} onOpenChange={setNewKeyOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Key name</Label>
              <Input
                placeholder="e.g. Production API Key"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="mt-2"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewKeyOpen(false)}>Cancel</Button>
            <Button onClick={handleNewKey}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
};

export default SettingsPage;
