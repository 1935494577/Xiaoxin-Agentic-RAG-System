import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchModelProfiles,
  createModelProfile,
  updateModelProfile,
  testModelConnection,
  testNewModelConnection,
  setDefaultModelProfile,
  deleteModelProfile,
} from "../../api/client";
import type { ModelProfile } from "../../api/types";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { Dialog } from "../../components/ui/Dialog";
import { toast } from "sonner";

const VENDOR_OPTIONS = [
  { id: "custom", label: "自定义 / 其它" },
  { id: "deepseek", label: "DeepSeek" },
  { id: "qwen", label: "阿里云通义千问" },
  { id: "openai", label: "OpenAI" },
  { id: "moonshot", label: "Moonshot (Kimi)" },
  { id: "zhipu", label: "智谱 GLM" },
];

const EMPTY_FORM = {
  name: "",
  vendor: "custom",
  api_base: "",
  api_path: "",
  default_model: "",
  api_key: "",
};

export default function ModelPage() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    msg: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["modelProfiles"],
    queryFn: fetchModelProfiles,
    staleTime: 30_000,
  });

  const profiles = data?.profiles ?? [];
  const defaultId = data?.default_profile_id;

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const loadProfile = (p: ModelProfile) => {
    setEditingId(p.id);
    setForm({
      name: p.name ?? "",
      vendor: p.vendor ?? "custom",
      api_base: p.api_base ?? "",
      api_path: p.api_path ?? "",
      default_model: p.default_model ?? "",
      api_key: "",
    });
    setTestResult(null);
  };

  const clearForm = () => {
    setEditingId("");
    setForm({ ...EMPTY_FORM });
    setTestResult(null);
  };

  const buildBody = () => ({
    name: form.name.trim(),
    vendor: form.vendor,
    api_base: form.api_base.trim(),
    api_path: form.api_path.trim() || undefined,
    default_model: form.default_model.trim(),
    ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
  });

  const saveMut = useMutation({
    mutationFn: async () => {
      const body = buildBody();
      if (!editingId) return createModelProfile(body);
      return updateModelProfile(editingId, body);
    },
    onSuccess: (saved) => {
      toast.success(
        `已${editingId ? "更新" : "保存"}「${(saved as ModelProfile)?.name ?? ""}」。请回到 Jnao Chat 侧栏选择该接入方式。`
      );
      clearForm();
      queryClient.invalidateQueries({ queryKey: ["modelProfiles"] });
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const testMut = useMutation({
    mutationFn: async () => {
      if (editingId && !form.api_key.trim()) {
        return testModelConnection(editingId);
      }
      return testNewModelConnection(buildBody());
    },
    onSuccess: (res) => {
      setTestResult({
        ok: Boolean(res.connected),
        msg: (res as Record<string, unknown>)?.message as string ?? (res.connected ? "连接成功" : "连接失败"),
      });
    },
    onError: (e: Error) => toast.error(e.message || "测试失败"),
  });

  const setDefaultMut = useMutation({
    mutationFn: (id: string) => setDefaultModelProfile(id),
    onSuccess: () => {
      toast.success("已设为默认");
      queryClient.invalidateQueries({ queryKey: ["modelProfiles"] });
    },
    onError: (e: Error) => toast.error(e.message || "操作失败"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteModelProfile(id),
    onSuccess: () => {
      if (editingId === deleteTarget) clearForm();
      setDeleteTarget(null);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["modelProfiles"] });
    },
    onError: (e: Error) => toast.error(e.message || "删除失败"),
  });

  const handleSave = () => {
    if (!form.name.trim() || !form.api_base.trim()) {
      toast.error("请填写显示名称和服务网址。");
      return;
    }
    if (!form.default_model.trim()) {
      toast.error("请填写模型名称。");
      return;
    }
    if (!editingId && !form.api_key.trim()) {
      toast.error("新建配置时请填写 API Key。");
      return;
    }
    saveMut.mutate();
  };

  const handleTest = () => {
    if (!form.api_base.trim() || !form.default_model.trim()) {
      toast.error("请填写服务网址和模型名称后再测试。");
      return;
    }
    if (!editingId && !form.api_key.trim()) {
      toast.error("新建配置时请填写 API Key 后再测试。");
      return;
    }
    testMut.mutate();
  };

  if (isLoading) {
    return <div className="p-6 text-text-muted text-sm">加载中...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader title="模型设置" />
        <p className="text-error text-sm">无法加载模型配置，请确认 API 已启动。</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[860px]">
      <PageHeader
        title="模型设置"
        description="配置大模型接入；保存前可用「测试连接」验证。"
      />

      <div className="space-y-6">
        {/* Vendor hint */}
        <details className="text-sm">
          <summary className="text-text-muted cursor-pointer hover:text-text">
            各厂商地址怎么填？（点击展开）
          </summary>
          <ul className="mt-2 p-3 bg-surface-muted rounded-lg text-xs text-text-muted space-y-1 list-disc pl-5">
            <li><strong>DeepSeek</strong>：api_base 填 https://api.deepseek.com，路径留空（会自动拼 /v1），模型如 deepseek-chat。</li>
            <li><strong>通义千问 OpenAI 兼容</strong>：api_base 填 https://dashscope.aliyuncs.com，api_path 填 /compatible-mode/v1，模型如 qwen-plus。</li>
            <li><strong>OpenAI</strong>：https://api.openai.com，路径留空。</li>
            <li>其它兼容 OpenAI Chat Completions 的网关同理填写 Base URL；路径仅在厂商要求时填写。</li>
          </ul>
        </details>

        {/* Form */}
        <div>
          {editingId ? (
            <p className="text-sm text-brand bg-brand-light rounded-lg px-3 py-2 mb-4">
              正在编辑配置 <code className="text-xs">{editingId}</code>。留空「API Key」则保留原密钥；点「取消编辑」可新建。
            </p>
          ) : (
            <h3 className="text-sm font-semibold text-text mb-3">新建配置</h3>
          )}

          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-sm text-text">显示名称</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="例如：公司用的通义千问"
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>
            <label className="block">
              <span className="text-sm text-text">厂商</span>
              <select
                value={form.vendor}
                onChange={(e) => set("vendor", e.target.value)}
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              >
                {VENDOR_OPTIONS.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm text-text">服务网址（Base）</span>
              <input
                type="text"
                value={form.api_base}
                onChange={(e) => set("api_base", e.target.value)}
                placeholder="https://api.deepseek.com"
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>
            <label className="block">
              <span className="text-sm text-text">路径后缀（多数情况可留空）</span>
              <input
                type="text"
                value={form.api_path}
                onChange={(e) => set("api_path", e.target.value)}
                placeholder="通义千问兼容模式填 /compatible-mode/v1"
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>
            <label className="block">
              <span className="text-sm text-text">模型名称</span>
              <input
                type="text"
                value={form.default_model}
                onChange={(e) => set("default_model", e.target.value)}
                placeholder="如 deepseek-chat、qwen-plus"
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>
            <label className="block">
              <span className="text-sm text-text">
                API Key（密钥）
              </span>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => set("api_key", e.target.value)}
                placeholder={editingId ? "留空则保留原密钥" : "必填"}
                className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
              />
            </label>
          </div>

          {testResult && (
            <div
              className={`mt-3 text-sm px-3 py-2 rounded-lg ${
                testResult.ok
                  ? "text-success bg-success-bg"
                  : "text-error bg-error-bg"
              }`}
            >
              {testResult.ok ? "连接成功" : "连接失败"}
              {testResult.msg ? `：${testResult.msg}` : ""}
            </div>
          )}

          <div className="flex items-center gap-2 mt-4">
            <Button variant="primary" onClick={handleSave} disabled={saveMut.isPending}>
              {saveMut.isPending ? "保存中..." : "保存到服务器"}
            </Button>
            {editingId && (
              <Button variant="ghost" onClick={clearForm}>
                取消编辑
              </Button>
            )}
            <Button
              variant="default"
              onClick={handleTest}
              disabled={testMut.isPending}
            >
              {testMut.isPending ? "测试中..." : "测试连接"}
            </Button>
          </div>
        </div>

        {/* Saved profiles */}
        <div>
          <h3 className="text-sm font-semibold text-text mb-3">已保存的配置</h3>
          {profiles.length === 0 ? (
            <p className="text-sm text-text-muted">暂无配置，请在上方新建。</p>
          ) : (
            <div className="space-y-3">
              {profiles.map((p) => {
                const isEditing = p.id === editingId;
                const isDefault = p.id === defaultId;
                return (
                  <div
                    key={p.id}
                    className={`p-4 rounded-xl border bg-white ${
                      isEditing ? "border-brand" : "border-border"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-text">{p.name}</span>
                      <span className="text-xs text-text-muted">· {p.vendor} · 模型 {p.default_model}</span>
                      {isEditing && <Badge variant="info">编辑中</Badge>}
                      {isDefault && <Badge variant="warning">当前默认</Badge>}
                    </div>
                    <p className="text-xs text-text-muted mb-1">
                      配置编号：<code>{p.id}</code>
                    </p>
                    <p className="text-xs text-text-muted mb-1">
                      Base: {p.api_base}{p.api_path ? ` → ${p.api_path}` : ""}
                    </p>
                    <p className="text-xs text-text-muted mb-3">
                      密钥: {p.has_api_key ? "已配置" : "未配置"}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="default"
                        disabled={isEditing}
                        onClick={() => loadProfile(p)}
                      >
                        编辑
                      </Button>
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() =>
                          testModelConnection(p.id).then((res) => {
                            toast.success(res.connected ? "连接成功" : "连接失败");
                          }).catch((e) => toast.error(String(e)))
                        }
                      >
                        测试
                      </Button>
                      {!isDefault && (
                        <>
                          <Button
                            size="sm"
                            variant="default"
                            onClick={() => setDefaultMut.mutate(p.id)}
                            disabled={setDefaultMut.isPending}
                          >
                            设为默认
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setDeleteTarget(p.id)}
                          >
                            删除
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Delete confirmation */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="删除模型配置"
        confirmLabel="删除"
        variant="destructive"
        loading={deleteMut.isPending}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget)}
      >
        确定要删除此配置？此操作不可撤销。
      </Dialog>
    </div>
  );
}
