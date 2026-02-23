import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { AppSidebar } from "@/components/AppSidebar";
import { CommandPalette, SearchBar } from "@/components/CommandPalette";
import { Bell, User, Settings, LogOut } from "lucide-react";
import { useJobNotifications } from "@/hooks/useJobNotifications";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NOTIFICATIONS_KEY = "tdm-notifications";
export type NotificationPrefs = {
  jobComplete: boolean;
  jobFailed: boolean;
  governanceEvents: boolean;
  unreadCount: number;
};
export function getNotificationPrefs(): NotificationPrefs {
  try {
    const s = localStorage.getItem(NOTIFICATIONS_KEY);
    if (s) return { ...JSON.parse(s), unreadCount: 0 };
  } catch {}
  return { jobComplete: true, jobFailed: true, governanceEvents: false, unreadCount: 0 };
}
export function setNotificationPrefs(p: Partial<NotificationPrefs>) {
  const curr = getNotificationPrefs();
  const next = { ...curr, ...p };
  localStorage.setItem(NOTIFICATIONS_KEY, JSON.stringify(next));
  return next;
}

export function Layout({ children }: { children: ReactNode }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const prefs = getNotificationPrefs();
  useJobNotifications();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <AppSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-6 border-b border-border/50 flex-shrink-0 bg-background/80 backdrop-blur-sm">
          <SearchBar />
          <div className="flex items-center gap-3">
            <DropdownMenu open={notifOpen} onOpenChange={setNotifOpen}>
              <DropdownMenuTrigger asChild>
                <button className="relative p-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted/50">
                  <Bell className="w-4 h-4" />
                  {prefs.unreadCount > 0 && (
                    <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-primary" />
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-72">
                <div className="px-2 py-2 text-sm font-semibold">Notifications</div>
                <DropdownMenuSeparator />
                <div className="px-2 py-2 text-xs text-muted-foreground">
                  Configure in Settings → Notifications
                </div>
                <Link to="/settings" onClick={() => setNotifOpen(false)}>
                  <DropdownMenuItem>
                    <Settings className="w-4 h-4 mr-2" />
                    Open Settings
                  </DropdownMenuItem>
                </Link>
              </DropdownMenuContent>
            </DropdownMenu>
            <DropdownMenu open={profileOpen} onOpenChange={setProfileOpen}>
              <DropdownMenuTrigger asChild>
                <button className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-semibold text-primary hover:bg-primary/30 transition-colors">
                  TF
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem asChild>
                  <Link to="/profile" onClick={() => setProfileOpen(false)}>
                    <User className="w-4 h-4 mr-2" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/settings" onClick={() => setProfileOpen(false)}>
                    <Settings className="w-4 h-4 mr-2" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setProfileOpen(false)}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
