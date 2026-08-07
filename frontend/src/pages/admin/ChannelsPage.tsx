import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  connectChannelProvider,
  disconnectChannelProvider,
  fetchChannelProviders,
  fetchChannelStatus,
  saveChannelRuntimeConfig,
  type ChannelConnectResponse,
  type ChannelProvider,
} from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { Button } from "../../components/ui/Button";
import { Dialog } from "../../components/ui/Dialog";
import { toast } from "sonner";

const AUTH_MODE_LABEL: Record<string, string> = {
  deep_link: "Deep Link 绑定",
  binding_code: "绑定码",
};

function statusBadge(provider: ChannelProvider) {
  if (provider.connection_status === "connected") {
    return <Badge variant="success">已连接</Badge>;
  }
  if (provider.configured) {
    return <Badge variant="warning">已配置</Badge>;
  }
  return <Badge variant="default">未配置</Badge>;
}

function providerCanConnect(provider: ChannelProvider, workerRunning: boolean): boolean {
  return (
    provider.configured &&
    workerRunning &&
    provider.auth_mode === "binding_code" &&
    provider.connection_status !== "connected"
  );
}

export default function ChannelsPage() {
  const queryClient = useQueryClient();
  const [configureTarget, setConfigureTarget] = useState<ChannelProvider | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [disconnectTarget, setDisconnectTarget] = useState<ChannelProvider | null>(null);
  const [bindInfo, setBindInfo] = useState<ChannelConnectResponse | null>(null);

  const providersQuery = useQuery({
    queryKey: ["admin-channel-providers"],
    queryFn: fetchChannelProviders,
    refetchInterval: 30_000,
  });

  const statusQuery = useQuery({
    queryKey: ["admin-channels-status"],
    queryFn: fetchChannelStatus,
    refetchInterval: 30_000,
  });

  const providers = providersQuery.data?.providers ?? [];
  const connectionsEnabled = providersQuery.data?.enabled ?? false;

  const openConfigure = (provider: ChannelProvider) => {
    const initial: Record<string, string> = {};
    for (const field of provider.credential_fields) {
      const saved = provider.credential_values[field.name];
      initial[field.name] = saved && field.type !== "password" ? saved : "";
    }
    setFormValues(initial);
    setConfigureTarget(provider);
  };

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!configureTarget) throw new Error("未选择渠道");
      const values: Record<string, string> = {};
      for (const field of configureTarget.credential_fields) {
        const raw = formValues[field.name] ?? "";
        if (field.type === "password" && !raw.trim()) {
          const masked = configureTarget.credential_values[field.name];
          if (masked) {
            values[field.name] = masked;
            continue;
          }
        }
        values[field.name] = raw;
      }
      return saveChannelRuntimeConfig(configureTarget.provider, values);
    },
    onSuccess: async (saved) => {
      toast.success(`已保存 ${saved.display_name} 凭证`);
      setConfigureTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin-channel-providers"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-channels-status"] }),
      ]);
      const status = await statusQuery.refetch();
      if (saved.auth_mode === "binding_code" && status.data?.service_running) {
        try {
          const bind = await connectChannelProvider(saved.provider);
          setBindInfo(bind);
        } catch (e) {
          toast.error(e instanceof Error ? e.message : "获取绑定码失败");
        }
      }
    },
    onError: (e: Error) => toast.error(e.message || "保存失败"),
  });

  const connectMut = useMutation({
    mutationFn: (provider: ChannelProvider) => connectChannelProvider(provider.provider),
    onSuccess: (result) => {
      setBindInfo(result);
      queryClient.invalidateQueries({ queryKey: ["admin-channel-providers"] });
    },
    onError: (e: Error) => toast.error(e.message || "获取绑定码失败"),
  });

  const disconnectMut = useMutation({
    mutationFn: (provider: ChannelProvider) => disconnectChannelProvider(provider.provider),
    onSuccess: (saved) => {
      toast.success(`已断开 ${saved.display_name}`);
      setDisconnectTarget(null);
      queryClient.invalidateQueries({ queryKey: ["admin-channel-providers"] });
      queryClient.invalidateQueries({ queryKey: ["admin-channels-status"] });
    },
    onError: (e: Error) => toast.error(e.message || "断开失败"),
  });

  const runtimeHint = useMemo(() => {
    if (!statusQuery.data?.service_running) {
      return "渠道 Worker 未运行：凭证会写入 runtime-config.json；启动 harness API 后会自动加载。";
    }
    return null;
  }, [statusQuery.data?.service_running]);

  const loading = providersQuery.isLoading || statusQuery.isLoading;
  const error = providersQuery.error || statusQuery.error;
  const workerRunning = Boolean(statusQuery.data?.service_running);

  const copyBindCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(`/connect ${code}`);
      toast.success("已复制绑定命令");
    } catch {
      toast.error("复制失败，请手动复制");
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <PageHeader
        title="IM 渠道"
        description="配置 Telegram / 飞书 / 企微等 IM 机器人凭证（对齐 DeerFlow channel_connections 运行时配置）。"
      >
        <Button
          variant="default"
          size="sm"
          onClick={() => {
            providersQuery.refetch();
            statusQuery.refetch();
          }}
        >
          刷新
        </Button>
      </PageHeader>

      {loading ? <SkeletonCard rows={3} /> : null}
      {error ? (
        <p className="text-sm text-red-600">
          {error instanceof Error ? error.message : "无法加载渠道配置"}
        </p>
      ) : null}

      {!connectionsEnabled ? (
        <div className="rounded-xl border border-warning/40 bg-warning-bg px-4 py-3 text-sm text-warning">
          渠道连接总开关已关闭（connections.json enabled=false）。请在 data/channels/connections.json 中启用。
        </div>
      ) : null}

      <div className="rounded-xl border border-border bg-surface p-4 text-sm">
        <p>
          渠道 Worker：
          <span className={statusQuery.data?.service_running ? "text-green-700" : "text-text-muted"}>
            {statusQuery.data?.service_running ? "运行中" : "未运行"}
          </span>
        </p>
        {runtimeHint ? <p className="mt-2 text-xs text-text-muted">{runtimeHint}</p> : null}
        <p className="mt-2 text-xs text-text-muted">
          渠道 Worker 运行在 Harness Gateway（默认 <code className="text-xs">8011</code>）。
          使用 <code className="text-xs">.\scripts\run-dev-harness.ps1</code> 启动完整开发栈。
        </p>
      </div>

      {providers.length === 0 ? (
        <p className="text-sm text-text-muted">暂无可用渠道提供商（请在 connections.json 中启用）。</p>
      ) : (
        <ul className="space-y-3">
          {providers.map((provider) => (
            <li
              key={provider.provider}
              className="rounded-xl border border-border bg-surface p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-text">{provider.display_name}</p>
                    {statusBadge(provider)}
                    <Badge variant="info">
                      {AUTH_MODE_LABEL[provider.auth_mode] ?? provider.auth_mode}
                    </Badge>
                  </div>
                  {provider.unavailable_reason ? (
                    <p className="mt-1 text-xs text-text-muted">{provider.unavailable_reason}</p>
                  ) : null}
                </div>
                <div className="flex shrink-0 gap-2">
                  {providerCanConnect(provider, workerRunning) ? (
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={connectMut.isPending}
                      onClick={() => connectMut.mutate(provider)}
                    >
                      获取绑定码
                    </Button>
                  ) : null}
                  <Button variant="default" size="sm" onClick={() => openConfigure(provider)}>
                    {provider.configured ? "更新凭证" : "配置"}
                  </Button>
                  {provider.configured ? (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => setDisconnectTarget(provider)}
                    >
                      断开
                    </Button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {configureTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="fixed inset-0 bg-black/40"
            onClick={() => !saveMut.isPending && setConfigureTarget(null)}
          />
          <div className="relative z-10 mx-4 w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-text">
              配置 {configureTarget.display_name}
            </h3>
            <p className="mt-1 text-xs text-text-muted">
              凭证保存在 data/channels/runtime-config.json（与登录账号无关），不会写入 git。
            </p>
            <form
              key={configureTarget.provider}
              className="mt-4 space-y-3"
              autoComplete="off"
              onSubmit={(e) => {
                e.preventDefault();
                saveMut.mutate();
              }}
            >
              {configureTarget.credential_fields.map((field) => (
                <label key={field.name} className="block text-sm">
                  <span className="mb-1 block text-text-muted">{field.label}</span>
                  <input
                    type={field.type === "password" ? "password" : "text"}
                    name={`channel-${configureTarget.provider}-${field.name}`}
                    id={`channel-${configureTarget.provider}-${field.name}`}
                    autoComplete={field.type === "password" ? "new-password" : "off"}
                    data-lpignore="true"
                    data-1p-ignore="true"
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                    value={formValues[field.name] ?? ""}
                    placeholder={
                      field.type === "password" && configureTarget.credential_values[field.name]
                        ? "留空则保留已保存的密钥"
                        : undefined
                    }
                    onChange={(e) =>
                      setFormValues((prev) => ({ ...prev, [field.name]: e.target.value }))
                    }
                  />
                </label>
              ))}
              <div className="mt-6 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  disabled={saveMut.isPending}
                  onClick={() => setConfigureTarget(null)}
                >
                  取消
                </Button>
                <Button type="submit" variant="primary" size="sm" disabled={saveMut.isPending}>
                  {saveMut.isPending ? "保存中…" : "保存并连接"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {bindInfo ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="fixed inset-0 bg-black/40"
            onClick={() => setBindInfo(null)}
          />
          <div className="relative z-10 mx-4 w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-text">绑定账号</h3>
            <p className="mt-2 text-sm text-text-muted">{bindInfo.instruction}</p>
            <div className="mt-4 rounded-lg border border-border bg-surface-muted px-3 py-2 font-mono text-sm">
              /connect {bindInfo.code}
            </div>
            <p className="mt-2 text-xs text-text-muted">
              绑定码约 {Math.round(bindInfo.expires_in / 60)} 分钟内有效。发送后刷新本页查看「已连接」状态。
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="default" size="sm" onClick={() => copyBindCode(bindInfo.code)}>
                复制命令
              </Button>
              <Button variant="primary" size="sm" onClick={() => setBindInfo(null)}>
                知道了
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <Dialog
        open={Boolean(disconnectTarget)}
        onClose={() => !disconnectMut.isPending && setDisconnectTarget(null)}
        title={disconnectTarget ? `断开 ${disconnectTarget.display_name}` : "断开渠道"}
        confirmLabel="确认断开"
        variant="destructive"
        loading={disconnectMut.isPending}
        onConfirm={() => disconnectTarget && disconnectMut.mutate(disconnectTarget)}
      >
        将清除已保存的运行时凭证，渠道机器人会停止接收消息。
      </Dialog>
    </div>
  );
}
