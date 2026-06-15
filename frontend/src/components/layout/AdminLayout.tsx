import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

const DEV_AUTH_BYPASS = import.meta.env.DEV;

/**
 * Wraps all /admin/* pages.
 * - Visually marks admin area
 * - Auth guard: redirect to /login when not authenticated (prod only)
 */
export default function AdminLayout() {
  const { isAuthenticated, username, logout } = useAuth();
  const location = useLocation();

  if (!DEV_AUTH_BYPASS && !isAuthenticated) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-1.5 bg-surface-muted border-b border-border text-xs text-text-muted flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-warning" />
          管理后台
          {isAuthenticated && username ? (
            <span className="text-text-muted/80">· {username}</span>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          {!isAuthenticated && DEV_AUTH_BYPASS ? (
            <Link to="/login" className="text-brand hover:text-brand-dark">
              登录
            </Link>
          ) : null}
          {isAuthenticated ? (
            <button
              type="button"
              onClick={logout}
              className="text-brand hover:text-brand-dark cursor-pointer"
            >
              退出
            </button>
          ) : null}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
