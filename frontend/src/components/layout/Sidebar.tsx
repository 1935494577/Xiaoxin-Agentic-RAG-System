import { NavLink, useLocation } from "react-router-dom";
import {
  ALL_NAV_ITEMS,
  getVisibleNavGroups,
  getVisibleNavItems,
  type NavItem,
} from "@/lib/departmentAccess";
import { cn } from "@/lib/utils";
import { useUserProfile } from "../../context/UserProfileContext";
import { SidebarUserProfile } from "./SidebarUserProfile";

function NavItemLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.href}
      end={item.href === "/chat"}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "app-nav-link group",
          isActive && "app-nav-link-active",
          item.primary && !isActive && "font-medium text-text"
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0 opacity-80 group-[.app-nav-link-active]:opacity-100" aria-hidden />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { department } = useUserProfile();
  const location = useLocation();
  const visible = getVisibleNavItems(department);
  const navGroups = getVisibleNavGroups(department);
  const chatItem = visible.find((item) => item.id === "chat");
  const onAdminRoute = location.pathname.startsWith("/admin");

  return (
    <aside className="app-sidebar flex w-[240px] shrink-0 flex-col border-r border-border bg-surface-muted">
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center">
          <img src="/company_logo.png" alt="JNAO 劲脑" className="h-8 w-auto" />
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-4 overflow-y-auto p-2 pt-3" aria-label="主导航">
        {chatItem ? (
          <div>
            <p className="app-nav-section-label">工作区</p>
            <div className="mt-1 flex flex-col gap-0.5">
              <NavItemLink item={chatItem} onNavigate={onNavigate} />
            </div>
          </div>
        ) : null}

        {navGroups.map((group) => (
          <div key={group.id}>
            <p className="app-nav-section-label">{group.label}</p>
            <div className="mt-1 flex flex-col gap-0.5">
              {group.items.map((item) => (
                <NavItemLink key={item.id} item={item} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      <SidebarUserProfile />

      <div className="border-t border-border px-4 py-2 text-center text-[10px] text-text-muted/75">
        {onAdminRoute ? "管理后台" : "Enterprise RAG"}
      </div>
    </aside>
  );
}

/** Resolve current admin page label for chrome header */
export function resolveAdminPageLabel(pathname: string): string {
  const match = ALL_NAV_ITEMS.find((item) => {
    if (item.id === "chat") return false;
    return pathname === item.href || pathname.startsWith(`${item.href}/`);
  });
  if (pathname === "/admin" || pathname === "/admin/") {
    return ALL_NAV_ITEMS.find((i) => i.id === "ingest")?.label ?? "数据入库";
  }
  return match?.label ?? "管理";
}
