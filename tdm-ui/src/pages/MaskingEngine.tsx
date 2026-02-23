import { motion } from "framer-motion";
import { Eye, ArrowRight, Shield, Layers, Fingerprint, Lock, Hash, Ban } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const transformers = [
  { name: "Format Preserving Encryption", icon: Lock, id: "mask.fpe_pan", desc: "Maintains format, encrypted output", tags: ["Reversible", "FK-safe"] },
  { name: "Tokenization", icon: Hash, id: "mask.hash", desc: "Replace with hash", tags: ["Irreversible"] },
  { name: "Deterministic Email", icon: Fingerprint, id: "mask.email_deterministic", desc: "Consistent email masking", tags: ["Deterministic", "FK-safe"] },
  { name: "Phone Masking", icon: Shield, id: "mask.redact", desc: "Redact sensitive", tags: ["Reversible"] },
  { name: "Pseudonymization", icon: Layers, id: "mask.hash", desc: "Replace with hash", tags: ["Irreversible"] },
  { name: "Redaction", icon: Ban, id: "mask.redact", desc: "Complete value removal", tags: ["Irreversible"] },
];

const MaskingEngine = () => {
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [rules, setRules] = useState<Record<string, string>>({});
  const queryClient = useQueryClient();

  const { data: datasets = [] } = useQuery({ queryKey: ["datasets"], queryFn: () => api.listDatasets() });
  const sourceDatasets = datasets.filter((d) => d.source_type !== "masked");
  const maskMutation = useMutation({
    mutationFn: () => api.mask({ dataset_version_id: selectedDatasetId!, rules }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      toast.success("Mask job started. Check Jobs or Datasets.");
    },
    onError: (err) => toast.error(err?.message ?? "Mask failed"),
  });

  const preview = Object.entries(rules).slice(0, 5).map(([field, rule]) => ({
    field,
    before: "••••••••",
    after: rule,
  }));

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Masking Engine</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure and apply data masking transformations</p>
      </motion.div>

      <motion.div variants={item}>
        <h2 className="text-sm font-semibold text-foreground mb-3">Transformer Library</h2>
        <div className="grid grid-cols-3 gap-3">
          {transformers.map((t) => (
            <div key={t.name} className="glass-card-hover p-4 cursor-pointer group">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg bg-primary/5 flex items-center justify-center">
                  <t.icon className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{t.name}</p>
                  <p className="text-[11px] text-muted-foreground">{t.desc}</p>
                </div>
              </div>
              <div className="flex gap-1.5 mt-2">
                {t.tags.map((tag) => (
                  <span key={tag} className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      <div className="grid grid-cols-3 gap-6">
        <motion.div variants={item} className="col-span-2 glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Apply masking</h2>
          <div className="space-y-4 mb-4">
            <label className="text-xs text-muted-foreground block">Dataset</label>
            <select value={selectedDatasetId} onChange={(e) => setSelectedDatasetId(e.target.value)} className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm">
              <option value="">Select dataset</option>
              {sourceDatasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name || d.id.slice(0, 8)} ({d.source_type})</option>
              ))}
            </select>
            {sourceDatasets.length === 0 && <p className="text-xs text-muted-foreground mt-1">No subset or synthetic datasets. Create one first.</p>}
            <label className="text-xs text-muted-foreground block">Rules (table.column → rule type)</label>
            <textarea
              placeholder='{"public.users.email": "mask.email_deterministic", "public.users.phone": "mask.redact"}'
              value={JSON.stringify(rules, null, 2)}
              onChange={(e) => { try { setRules(JSON.parse(e.target.value || "{}")); } catch {} }}
              className="w-full h-32 px-3 py-2 rounded-lg bg-muted/50 border border-border font-mono text-xs"
            />
          </div>
          <div className="space-y-2">
            {preview.map((p) => (
              <div key={p.field} className="flex items-center gap-4 p-3 rounded-lg bg-muted/20">
                <span className="text-xs font-mono text-primary w-24">{p.field}</span>
                <span className="text-sm font-mono text-destructive/70 flex-1">{p.before}</span>
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-mono text-success flex-1">{p.after}</span>
              </div>
            ))}
          </div>
          <button
            onClick={() => maskMutation.mutate()}
            disabled={!selectedDatasetId || Object.keys(rules).length === 0 || maskMutation.isPending}
            className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            <Eye className="w-4 h-4" /> Apply Mask
          </button>
        </motion.div>

        <motion.div variants={item} className="glass-card p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4">Industry Templates</h2>
          <div className="space-y-2">
            {["Banking", "Healthcare", "eCommerce", "Telecom"].map((name) => (
              <button key={name} className="w-full flex items-center gap-3 p-3 rounded-lg bg-muted/20 hover:bg-muted/40 transition-colors text-left group">
                <div className="w-2 h-2 rounded-full bg-primary" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-primary">{name}</p>
                  <p className="text-[11px] text-muted-foreground">PII, Payment, Address</p>
                </div>
                <ArrowRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default MaskingEngine;
