import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAdminUser,
  fetchAdminUsers,
  resetAdminUserPassword,
  setAdminUserActive,
  type AdminUserRow,
} from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Skeleton } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { DEPT_OPTIONS } from "../../lib/constants";
import { toast } from "sonner";

export default function UsersAdminPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["adminUsers"],
    queryFn: fetchAdminUsers,
  });
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [department, setDepartment] = useState<string>(DEPT_OPTIONS[0]);
  const [resetTarget, setResetTarget] = useState<AdminUserRow | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  const createMut = useMutation({
    mutationFn: createAdminUser,
    onSuccess: () => {
      toast.success("账号已创建");
      setUsername("");
      setDisplayName("");
      setPassword("");
      qc.invalidateQueries({ queryKey: ["adminUsers"] });
    },
    onError: (e: Error) => toast.error(e.message || "创建失败"),
  });

  const activeMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      setAdminUserActive(id, active),
    onSuccess: () => {
      toast.success("状态已更新");
      qc.invalidateQueries({ queryKey: ["adminUsers"] });
    },
    onError: (e: Error) => toast.error(e.message || "更新失败"),
  });

  const resetMut = useMutation({
    mutationFn: ({ id, pw }: { id: string; pw: string }) => resetAdminUserPassword(id, pw),
    onSuccess: () => {
      setResetTarget(null);
      setResetPassword("");
      toast.success("密码已重置");
    },
    onError: (e: Error) => toast.error(e.message || "重置失败"),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="账号管理"
        description="仅技术部可用。可创建账号、停用账号或重置密码；部门由账号绑定。"
      />

      {isLoading ? (
        <div className="admin-panel p-4 space-y-3 mb-6" role="status" aria-label="加载中">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : error ? (
        <p className="text-sm text-error">加载失败</p>
      ) : (
        <div className="admin-panel overflow-hidden mb-6">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-muted/50 text-left">
                <th className="px-4 py-2 font-medium">用户名</th>
                <th className="px-4 py-2 font-medium">显示名</th>
                <th className="px-4 py-2 font-medium">部门</th>
                <th className="px-4 py-2 font-medium">状态</th>
                <th className="px-4 py-2 font-medium w-40">操作</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((u) => (
                <tr key={u.id} className="border-b border-border-light">
                  <td className="px-4 py-2">{u.username}</td>
                  <td className="px-4 py-2">{u.display_name || "—"}</td>
                  <td className="px-4 py-2">{u.department}</td>
                  <td className="px-4 py-2">{u.is_active ? "启用" : "停用"}</td>
                  <td className="px-4 py-2 space-x-2">
                    <button
                      type="button"
                      className="text-xs text-brand hover:underline cursor-pointer"
                      onClick={() =>
                        activeMut.mutate({ id: u.id, active: !u.is_active })
                      }
                      disabled={activeMut.isPending}
                    >
                      {u.is_active ? "停用" : "启用"}
                    </button>
                    <button
                      type="button"
                      className="text-xs text-text-muted hover:underline cursor-pointer"
                      onClick={() => {
                        setResetTarget(u);
                        setResetPassword("");
                      }}
                    >
                      重置密码
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form
        className="admin-panel p-4 space-y-3 max-w-md"
        autoComplete="off"
        onSubmit={(e) => e.preventDefault()}
      >
        <h3 className="text-sm font-semibold text-text">新建账号</h3>
        <input
          className="flex h-10 w-full rounded-lg border border-border px-3 text-sm"
          placeholder="用户名"
          name="admin-new-username"
          autoComplete="off"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="flex h-10 w-full rounded-lg border border-border px-3 text-sm"
          placeholder="显示名（可选，默认同用户名）"
          name="admin-new-display-name"
          autoComplete="off"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <input
          type="password"
          className="flex h-10 w-full rounded-lg border border-border px-3 text-sm"
          placeholder="初始密码（至少 6 位）"
          name="admin-new-password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select
          className="flex h-10 w-full rounded-lg border border-border px-3 text-sm"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
        >
          {DEPT_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <Button
          variant="primary"
          disabled={createMut.isPending}
          onClick={() =>
            createMut.mutate({
              username: username.trim(),
              password,
              department,
              display_name: displayName.trim() || undefined,
            })
          }
        >
          创建
        </Button>
      </form>

      <Dialog
        open={!!resetTarget}
        onClose={() => setResetTarget(null)}
        title={`重置密码：${resetTarget?.username ?? ""}`}
        confirmLabel="确认重置"
        loading={resetMut.isPending}
        onConfirm={() => {
          if (!resetTarget || resetPassword.trim().length < 6) {
            toast.error("新密码至少 6 位");
            return;
          }
          resetMut.mutate({ id: resetTarget.id, pw: resetPassword.trim() });
        }}
      >
        <input
          type="password"
          className="mt-2 flex h-10 w-full rounded-lg border border-border px-3 text-sm"
          placeholder="新密码（至少 6 位）"
          name="admin-reset-password"
          autoComplete="new-password"
          value={resetPassword}
          onChange={(e) => setResetPassword(e.target.value)}
        />
      </Dialog>
    </div>
  );
}
