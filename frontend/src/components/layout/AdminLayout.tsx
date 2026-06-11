import { Outlet } from "react-router-dom";

/**
 * Wraps all /admin/* pages.
 * - Visually marks admin area
 * - Future: auth guard (check role/token, redirect if unauthorized)
 */
export default function AdminLayout() {
  return (
    <div className="flex flex-col h-full">
      {/* Future auth guard placeholder */}
      <div className="px-5 py-1.5 bg-surface-muted border-b border-border text-xs text-text-muted flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-warning" />
        管理后台
      </div>
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
