import { ReactNode } from "react";
import { AppSidebar } from "@/components/AppSidebar";
import { CommandPalette, SearchBar } from "@/components/CommandPalette";
import { Bell } from "lucide-react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <AppSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-border/50 flex-shrink-0 bg-background/80 backdrop-blur-sm">
          <SearchBar />
          <div className="flex items-center gap-3">
            <button className="relative p-2 text-muted-foreground hover:text-foreground transition-colors">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-primary" />
            </button>
            <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-semibold text-primary">
              TF
            </div>
          </div>
        </header>
        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
