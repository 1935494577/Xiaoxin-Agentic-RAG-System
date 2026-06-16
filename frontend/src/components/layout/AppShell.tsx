import { Outlet } from "react-router-dom";
import { UserProfileProvider } from "../../context/UserProfileContext";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <UserProfileProvider>
      <div className="flex h-screen bg-surface-muted/50">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col bg-white shadow-[inset_1px_0_0_rgba(0,0,0,0.03)]">
          <Outlet />
        </main>
      </div>
    </UserProfileProvider>
  );
}
