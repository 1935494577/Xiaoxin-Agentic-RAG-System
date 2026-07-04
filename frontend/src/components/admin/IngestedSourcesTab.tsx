import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteIngestedSource,
  listIngestedSources,
} from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { toast } from "sonner";

export function IngestedSourcesTab() {
  const qc = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["ingestedSources"],
    queryFn: listIngestedSources,
    staleTime: 30_000,
  });

  const deleteMut = useMutation({
    mutationFn: (source: string) => deleteIngestedSource(source),
    onSuccess: () => {
      setDeleteTarget(null);
      toast.success("已从知识库移除");
      qc.invalidateQueries({ queryKey: ["ingestedSources"] });
    },
    onError: (e: Error) => toast.error(e.message || "删除失败"),
  });

  if (isLoading) {
    return <p className="text-sm text-text-muted">加载中…</p>;
  }
  if (error) {
    return <p className="text-sm text-error">无法加载已入库文档列表</p>;
  }

  const rows = data ?? [];

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-muted">
        删除后将从向量库、全文索引与文档注册表中移除，对话中将不再检索到该文档。
      </p>

      {rows.length === 0 ? (
        <p className="text-sm text-text-muted">暂无已入库文档</p>
      ) : (
        <div className="admin-panel overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-muted/50 text-left">
                <th className="px-4 py-2 font-medium">文档</th>
                <th className="px-4 py-2 font-medium">父块</th>
                <th className="px-4 py-2 font-medium">子块</th>
                <th className="px-4 py-2 font-medium w-20" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.source} className="border-b border-border-light">
                  <td className="px-4 py-2 font-mono text-xs break-all">{row.source}</td>
                  <td className="px-4 py-2">{row.parent_count}</td>
                  <td className="px-4 py-2">{row.child_count}</td>
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      className="text-xs text-error hover:underline cursor-pointer"
                      onClick={() => setDeleteTarget(row.source)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="删除已入库文档"
        confirmLabel="删除"
        variant="destructive"
        loading={deleteMut.isPending}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget)}
      >
        确定从知识库删除「{deleteTarget}」？向量与索引数据将一并清除，不可撤销。
      </Dialog>
    </div>
  );
}
