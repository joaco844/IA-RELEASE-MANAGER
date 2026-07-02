import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { CircleDot, GitBranch, LayoutDashboard, LogOut, Rocket, Settings } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/repositories", label: "Repositories", icon: GitBranch, end: false },
  { to: "/issues", label: "Issues", icon: CircleDot, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r bg-card">
        <div className="flex h-14 items-center gap-2.5 border-b px-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/15">
            <Rocket className="h-4 w-4 text-primary" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold">AI Release Manager</p>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Internal tools
            </p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t p-3">
          <p className="px-3 text-[10px] uppercase tracking-widest text-muted-foreground">
            GitLab → AI → Slack
          </p>
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-end gap-3 border-b bg-background/80 px-6 backdrop-blur">
          {user && (
            <div className="text-right leading-tight">
              <p className="text-sm font-medium">{user.full_name}</p>
              <p className="text-xs text-muted-foreground">{user.email}</p>
            </div>
          )}
          <Button variant="ghost" size="sm" onClick={logout} title="Log out">
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
