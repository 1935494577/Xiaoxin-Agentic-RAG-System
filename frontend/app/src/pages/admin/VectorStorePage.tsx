import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchVectorStores,
  createVectorStore,
  activateVectorStore,
  deleteVectorStore,
} from "../../api/client";
import type { VectorStore } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Dialog } from "../../components/ui/Dialog";
import { Select } from "../../components/ui/Select";
import { toast } from "sonner";

type StoreInfo = VectorStore & {
  compatible?: boolean;
  backend_label?: string;
  vector_count?: number;
  bm25_docs?: number;
  embedding_dim?: number;
  current_embedding_dim?: number;
  embedding_model?: string;
  current_embedding_model?: string;
};

export default function VectorStorePage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newBackend, setNewBackend] = useState("milvus_lite");
  const [deleteTarget, setDeleteTarget] = useState<StoreInfo | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["vectorStores"],
    queryFn: fetchVectorStores,
    staleTime: 30_000,
  });

  const stores: StoreInfo[] = (data as Record<string, unknown>)?.stores as StoreInfo[] ?? [];
  const active = (data as Record<string, unknown>)?.active as StoreInfo | null;
  const backends: { id: string; label: string; available: boolean }[] =
    ((data as Record<string, unknown>)?.available_backends as []) ?? [];

  const createMut = useMutation({
    mutationFn: () => createVectorStore(newName.trim(), newBackend),
    onSuccess: () => {
      toast.success("已创建。若需使用，请点击「切换」并重新入库。");
      setShowCreate(false);
      setNewName("");
      queryClient.invalidateQueries({ queryKey: ["vectorStores"] });
    },
    onError: (e: Error) => toast.error(e.message || "创建失败"),
  });

  const activateMut = useMutation({
    mutationFn: (id: string) => activateVectorStore(id),
    onSuccess: () => {
      toast.success("已切换");
      queryClient.invalidateQueries({ queryKey: ["vectorStores"] });
    },
    onError: () => toast.error("切换失败"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteVectorStore(id),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["vectorStores"] });
    },
    onError: (e: Error) => toast.warning(e.message || "删除失败"),
  });

  const availableBackends = backends.length
    ? backends.filter((b) => b.available)
    : [{ id: "numpy", label: "NumPy 文件", available: true }];

  const curModel = active?.current_embedding_model || "当前嵌入模型";
  const curDim = active?.current_embedding_dim || "?";
  const defaultName = `${String(curModel).split("/").pop()}-${curDim}维`;

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader title="向量库设置" />
        <p className="text-error text-sm">无法加载向量库配置，请确认 API 已启动。</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[860px]">
      <PageHeader
        title="向量库设置"
        description="切换或新建向量库，使索引维度与当前嵌入模型一致。更换嵌入模型后建议新建向量库并重新入库。"
      />

      <div className="space-y-6">
        {/* Active store info */}
        {active && (
          <div className="p-4 rounded-xl bg-surface-muted text-sm text-text space-y-1">
            <p>
              <strong>当前使用：</strong>
              {active.name} · {active.backend_label} · {active.vector_count ?? 0} 条向量 · 索引{" "}
              {active.embedding_dim ?? "—"} 维 / 模型 {active.current_embedding_dim ?? "—"} 维
              {active.compatible !== false ? " · ✅ 兼容" : " · ⚠️ 维度不匹配，请新建库并重新入库"}
            </p>
          </div>
        )}

        {/* Existing stores */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">已有向量库</h3>
          {stores.length === 0 ? (
            <p className="text-sm text-text-muted">暂无向量库，请下方新建。</p>
          ) : (
            <div className="space-y-3">
              {stores.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between p-4 rounded-xl border border-border bg-white"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-text">{s.name}</span>
                      {s.active && <Badge variant="info">当前</Badge>}
                      {s.compatible !== false ? (
                        <Badge variant="success">兼容</Badge>
                      ) : (
                        <Badge variant="warning">不匹配</Badge>
                      )}
                    </div>
                    <p className="text-xs text-text-muted">
                      {s.backend_label} · 模型 {s.embedding_model} · {s.vector_count ?? 0} 向量
                      {s.bm25_docs ? ` / ${s.bm25_docs} BM25` : ""}
                    </p>
                    <p className="text-xs text-text-muted">
                      索引维度：{s.embedding_dim ?? "—"} · 当前模型：{s.current_embedding_dim ?? "—"} 维
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {!s.active && (
                      <>
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => activateMut.mutate(s.id)}
                          disabled={activateMut.isPending}
                        >
                          切换
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDeleteTarget(s)}
                        >
                          删除
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create new store */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">新建向量库</h3>
          {!showCreate ? (
            <Button variant="default" onClick={() => setShowCreate(true)}>
              新建向量库
            </Button>
          ) : (
            <div className="p-4 rounded-xl border border-border bg-surface-muted space-y-3">
              <label className="block">
                <span className="text-sm text-text">名称</span>
                <input
                  type="text"
                  maxLength={64}
                  value={newName || defaultName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder={defaultName}
                  className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
                />
              </label>
              <label className="block">
                <span className="text-sm text-text">存储类型</span>
                <Select
                  value={newBackend}
                  onChange={(e) => setNewBackend(e.target.value)}
                  className="mt-1"
                >
                  {availableBackends.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.label}
                    </option>
                  ))}
                </Select>
              </label>
              <p className="text-xs text-text-muted">
                将按当前嵌入模型 {curModel}（{curDim} 维）创建空库；创建后请切换到此库并重新入库。
              </p>
              <div className="flex gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={createMut.isPending}
                  onClick={() => createMut.mutate()}
                >
                  {createMut.isPending ? "创建中..." : "确认创建"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreate(false)}
                >
                  取消
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="删除向量库"
        confirmLabel="删除"
        variant="destructive"
        loading={deleteMut.isPending}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
      >
        确定要删除「{deleteTarget?.name}」？此操作不可撤销，向量数据将丢失。
      </Dialog>
    </div>
  );
}
