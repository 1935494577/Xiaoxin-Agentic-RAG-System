import { Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  canAccessAdminPath,
  shouldEnforceDepartmentAccess,
} from "../../lib/departmentAccess";
import { useAuth } from "../../hooks/useAuth";
import { useUserProfile } from "../../context/UserProfileContext";
import AccessDeniedPage from "../../pages/admin/AccessDeniedPage";
import { ThemeToggle } from "../ui/ThemeToggle";
import { resolveAdminPageLabel } from "./Sidebar";

export default function AdminLayout() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const { department, displayName } = useUserProfile();
  const location = useLocation();
  const pageLabel = resolveAdminPageLabel(location.pathname);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  if (
    shouldEnforceDepartmentAccess(department) &&
    !canAccessAdminPath(department, location.pathname)
  ) {
    return <AccessDeniedPage department={department} />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface-muted/35">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border bg-surface px-6 py-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">
            管理后台
          </p>
          <h1 className="truncate text-base font-semibold text-text">{pageLabel}</h1>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-sm">
          {username ? (
            <span className="hidden text-text-muted sm:inline">
              {displayName?.trim() || username}
            </span>
          ) : null}
          <ThemeToggle />
          <button
            type="button"
            onClick={handleLogout}
            className="cursor-pointer font-medium text-brand transition-colors hover:text-brand-dark"
          >
            退出
          </button>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
