import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu } from "lucide-react";
import { UserProfileProvider } from "../../context/UserProfileContext";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <UserProfileProvider>
      <div className="flex h-screen bg-surface-muted/50">
        <div className="hidden h-full shrink-0 md:block">
          <Sidebar />
        </div>

        {navOpen ? (
          <div
            className="fixed inset-0 z-40 md:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="导航菜单"
          >
            <div
              className="animate-dialog-overlay absolute inset-0 bg-black/40"
              onClick={() => setNavOpen(false)}
            />
            <div className="animate-drawer-in absolute inset-y-0 left-0 shadow-overlay">
              <Sidebar onNavigate={() => setNavOpen(false)} />
            </div>
          </div>
        ) : null}

        <main className="flex min-w-0 flex-1 flex-col bg-surface shadow-[inset_1px_0_0_rgba(0,0,0,0.03)]">
          <div className="flex items-center gap-3 border-b border-border bg-surface px-4 py-2.5 md:hidden">
            <button
              type="button"
              aria-label="打开导航"
              onClick={() => setNavOpen(true)}
              className="inline-flex cursor-pointer items-center justify-center rounded-lg border border-border bg-surface p-2 text-text-muted transition-colors hover:border-brand/40 hover:text-brand"
            >
              <Menu className="h-4 w-4" aria-hidden />
            </button>
            <img src="/company_logo.png" alt="JNAO 劲脑" className="h-7 w-auto" />
          </div>
          <Outlet />
        </main>
      </div>
    </UserProfileProvider>
  );
}
