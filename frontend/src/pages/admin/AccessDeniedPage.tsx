import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { getDefaultAdminPath, getVisibleNavItems } from "@/lib/departmentAccess";

type AccessDeniedPageProps = {
  department: string;
};

export default function AccessDeniedPage({ department }: AccessDeniedPageProps) {
  const allowed = getVisibleNavItems(department).filter((item) => item.id !== "chat");

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="admin-panel max-w-md p-8 text-center">
        <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-warning-bg text-warning">
          <ShieldAlert className="h-6 w-6" aria-hidden />
        </div>
        <h1 className="text-xl font-semibold text-text">暂无访问权限</h1>
        <p className="mt-2 text-sm leading-relaxed text-text-muted">
          您当前所属部门为<strong className="font-medium text-text"> {department} </strong>
          ，该页面仅对技术部开放，或不在本部门可用功能范围内。
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          <Link
            to="/chat"
            className="inline-flex items-center rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-muted"
          >
            返回 Chat
          </Link>
          <Link
            to={getDefaultAdminPath(department)}
            className="inline-flex items-center rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-dark"
          >
            前往数据入库
          </Link>
        </div>
        {allowed.length > 0 ? (
          <p className="mt-5 text-xs text-text-muted">
            本部门可用：{allowed.map((item) => item.label).join("、")}
          </p>
        ) : null}
      </div>
    </div>
  );
}
