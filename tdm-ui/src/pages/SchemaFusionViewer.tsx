import { motion } from "framer-motion";
import { Layers, Database, Globe, FileText, Code, Zap } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const SchemaFusionViewer = () => {
  const [domainPack, setDomainPack] = useState("ecommerce");
  const [testCaseEntities, setTestCaseEntities] = useState('{"user": {"fields": {"email": {"type": "email"}, "firstname": {"type": "string"}}}}');
  const [fuseResult, setFuseResult] = useState<{ unified_schema?: unknown; tables_count?: number } | null>(null);

  const fuseMutation = useMutation({
    mutationFn: () => {
      let entities: Record<string, unknown> | undefined;
      try {
        entities = JSON.parse(testCaseEntities || "{}");
      } catch {
        entities = undefined;
      }
      return api.fuseSchemas({
        domain_pack: domainPack,
        test_case_entities: entities,
      });
    },
    onSuccess: (data) => setFuseResult(data),
  });

  const sources = [
    { name: "DB Schema", icon: Database, priority: 1, color: "text-primary" },
    { name: "API Schema", icon: Code, priority: 2, color: "text-accent" },
    { name: "UI Schema", icon: Globe, priority: 3, color: "text-success" },
    { name: "Test Case Entities", icon: FileText, priority: 4, color: "text-warning" },
    { name: "Domain Pack", icon: Layers, priority: 5, color: "text-muted-foreground" },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Schema Fusion Viewer</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hybrid schema fusion: UI + API + DB + Test Case + Domain Packs
        </p>
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Run Schema Fusion</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Domain Pack</label>
            <select
              value={domainPack}
              onChange={(e) => setDomainPack(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm"
              aria-label="Select domain pack for schema fusion"
            >
              <option value="ecommerce">E-commerce</option>
              <option value="banking">Banking</option>
              <option value="generic">Generic</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Test Case Entities (JSON)</label>
            <textarea
              value={testCaseEntities}
              onChange={(e) => setTestCaseEntities(e.target.value)}
              className="w-full min-h-[80px] px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm font-mono"
              placeholder='{"user": {"fields": {"email": {"type": "email"}}}}'
            />
          </div>
        </div>
        <Button
          className="mt-4"
          onClick={() => fuseMutation.mutate()}
          disabled={fuseMutation.isPending}
        >
          {fuseMutation.isPending ? "Fusing..." : (
            <>
              <Zap className="w-4 h-4 mr-2" />
              Fuse Schemas
            </>
          )}
        </Button>
        {fuseResult && (
          <div className="mt-4 p-4 rounded-lg bg-success/10 border border-success/20">
            <p className="text-sm font-medium">Fused: {fuseResult.tables_count} tables</p>
            <pre className="text-xs mt-2 overflow-auto max-h-48 bg-muted/30 p-2 rounded">
              {JSON.stringify(fuseResult.unified_schema, null, 2)}
            </pre>
          </div>
        )}
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Fusion Priority</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sources.map((s) => (
            <div key={s.name} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 border">
              <div className={`w-10 h-10 rounded-lg bg-muted flex items-center justify-center ${s.color}`}>
                <s.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-medium">{s.name}</p>
                <p className="text-xs text-muted-foreground">Priority {s.priority}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <h2 className="text-sm font-semibold text-foreground mb-4">Fusion Flow</h2>
        <div className="flex items-center gap-2 overflow-x-auto pb-2 flex-wrap">
          {sources.map((s, i) => (
            <div key={s.name} className="flex items-center gap-2">
              <div className={`px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2 ${
                i === 0 ? "bg-primary/10 text-primary border border-primary/20" :
                i === sources.length - 1 ? "bg-success/10 text-success border border-success/20" :
                "bg-muted text-foreground/70 border border-border/50"
              }`}>
                <s.icon className="w-3 h-3" />
                {s.name}
              </div>
              {i < sources.length - 1 && (
                <span className="text-muted-foreground">→</span>
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-3">
          Unified Schema → SDV Generator → Generated Data → Provisioning → tdm_target
        </p>
      </motion.div>
    </motion.div>
  );
};

export default SchemaFusionViewer;
