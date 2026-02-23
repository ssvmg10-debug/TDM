import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Index from "./pages/Index";
import WorkflowOrchestrator from "./pages/WorkflowOrchestrator";
import DatasetCatalog from "./pages/DatasetCatalog";
import EnvironmentProvisioning from "./pages/EnvironmentProvisioning";
import GovernanceLineage from "./pages/GovernanceLineage";
import AuditLogs from "./pages/AuditLogs";
import SettingsPage from "./pages/SettingsPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/workflows" element={<WorkflowOrchestrator />} />
            <Route path="/datasets" element={<DatasetCatalog />} />
            <Route path="/environments" element={<EnvironmentProvisioning />} />
            <Route path="/governance" element={<GovernanceLineage />} />
            <Route path="/audit-logs" element={<AuditLogs />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
