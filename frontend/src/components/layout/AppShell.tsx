import { Outlet } from "react-router-dom";
import { UserProfileProvider } from "../../context/UserProfileContext";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <UserProfileProvider>
      <div className="flex h-screen bg-white">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0">
          <Outlet />
        </main>
      </div>
    </UserProfileProvider>
  );
}
