import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import {
  canAccessAdminPath,
  shouldEnforceDepartmentAccess,
} from "../../lib/departmentAccess";
import { useAuth } from "../../hooks/useAuth";
import { useUserProfile } from "../../context/UserProfileContext";
import AccessDeniedPage from "../../pages/admin/AccessDeniedPage";
import { resolveAdminPageLabel } from "./Sidebar";

const DEV_AUTH_BYPASS = import.meta.env.DEV;

export default function AdminLayout() {
  const { isAuthenticated, username, logout } = useAuth();
  const { department } = useUserProfile();
  const location = useLocation();
  const pageLabel = resolveAdminPageLabel(location.pathname);

  if (!DEV_AUTH_BYPASS && !isAuthenticated) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }

  if (
    shouldEnforceDepartmentAccess(department) &&
    !canAccessAdminPath(department, location.pathname)
  ) {
    return <AccessDeniedPage department={department} />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface-muted/35">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border bg-white px-6 py-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">
            管理后台
          </p>
          <h1 className="truncate text-base font-semibold text-text">{pageLabel}</h1>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-sm">
          {isAuthenticated && username ? (
            <span className="hidden text-text-muted sm:inline">{username}</span>
          ) : null}
          {!isAuthenticated && DEV_AUTH_BYPASS ? (
            <Link
              to="/login"
              className="font-medium text-brand transition-colors hover:text-brand-dark"
            >
              登录
            </Link>
          ) : null}
          {isAuthenticated ? (
            <button
              type="button"
              onClick={logout}
              className="cursor-pointer font-medium text-brand transition-colors hover:text-brand-dark"
            >
              退出
            </button>
          ) : null}
        </div>
      </header>
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
