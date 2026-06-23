import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchScenarioCatalog } from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";
import { useUserProfile } from "../../context/UserProfileContext";
import { hasFullDepartmentAccess } from "../../lib/departmentAccess";
import { ChevronDown, ChevronRight, Code2, Layers } from "lucide-react";

export default function ScenariosPage() {
  const { department } = useUserProfile();
  const isDev = hasFullDepartmentAccess(department);
  const [showTech, setShowTech] = useState(isDev);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["scenarioCatalog", department, showTech],
    queryFn: () =>
      fetchScenarioCatalog({
        department,
        includeTech: showTech && isDev,
      }),
    staleTime: 300_000,
  });

  const deptSummary = data?.department_info?.summary;
  const preset = data?.department_info?.default_scene_preset;

  const techCount = useMemo(
    () => data?.scenarios.filter((s) => s.tech && Object.keys(s.tech).length > 0).length ?? 0,
    [data]
  );

  return (
    <div className="p-6 max-w-[960px]">
      <PageHeader
        title="业务场景与功能"
        description={
          deptSummary ||
          "按部门查看可用业务场景、操作步骤；技术部可切换开发视图查看 API 与代码路径。"
        }
      >
        {isDev ? (
          <button
            type="button"
            onClick={() => setShowTech((v) => !v)}
            className={
              "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors " +
              (showTech
                ? "border-brand bg-brand-light text-brand"
                : "border-border bg-white text-text-muted hover:border-brand/40")
            }
          >
            <Code2 size={16} />
            {showTech ? "开发视图" : "业务视图"}
          </button>
        ) : null}
      </PageHeader>

      {data?.chat_note ? (
        <div className="mb-5 rounded-xl border border-brand/30 bg-brand-light/50 px-4 py-3 text-sm text-text">
          {data.chat_note}
        </div>
      ) : preset ? (
        <div className="mb-5 rounded-xl border border-border bg-surface-muted/60 px-4 py-3 text-sm text-text-muted">
          推荐对话预设：
          <strong className="font-medium text-text"> {preset} </strong>
          — 在「对话设置 → 业务场景预设」一键应用（仅技术部可操作）。
        </div>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-text-muted">加载场景目录…</p>
      ) : error ? (
        <p className="text-sm text-error">加载失败，请刷新或联系技术部。</p>
      ) : (
        <>
          {isDev && showTech ? (
            <p className="mb-4 text-xs text-text-muted">
              开发视图：共 {data?.scenarios.length ?? 0} 个场景，{techCount} 个含 tech 字段。配置文件：
              <code className="mx-1 rounded bg-surface-muted px-1">enterprise_rag/data/config/scenario_catalog.json</code>
            </p>
          ) : null}

          <div className="space-y-4">
            {(data?.scenarios ?? []).map((scenario) => {
              const open = expandedId === scenario.id;
              return (
                <article
                  key={scenario.id}
                  className="rounded-xl border border-border bg-white shadow-sm overflow-hidden"
                >
                  <button
                    type="button"
                    className="flex w-full items-start gap-3 px-4 py-4 text-left hover:bg-surface-muted/40 transition-colors"
                    onClick={() => setExpandedId(open ? null : scenario.id)}
                  >
                    {open ? (
                      <ChevronDown className="mt-0.5 shrink-0 text-text-muted" size={18} />
                    ) : (
                      <ChevronRight className="mt-0.5 shrink-0 text-text-muted" size={18} />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-text">{scenario.label}</h3>
                        {scenario.channel_label && scenario.channel_label !== "—" ? (
                          <span className="rounded-full bg-brand-light px-2 py-0.5 text-xs text-brand">
                            {scenario.channel_label}
                          </span>
                        ) : null}
                        {scenario.scene_preset ? (
                          <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs text-text-muted">
                            {scenario.scene_preset}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-text-muted">{scenario.user_goal}</p>
                    </div>
                  </button>

                  {open ? (
                    <div className="border-t border-border px-4 pb-4 pt-2 space-y-4">
                      <section>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted mb-2">
                          操作步骤
                        </h4>
                        <ol className="list-decimal list-inside space-y-1.5 text-sm text-text">
                          {scenario.steps.map((step, i) => (
                            <li key={i} className="text-pretty leading-relaxed">
                              {step}
                            </li>
                          ))}
                        </ol>
                      </section>

                      {(scenario.tools.length > 0 ||
                        scenario.clarify_option_id ||
                        scenario.output_schema_id) && (
                        <section className="flex flex-wrap gap-2 text-xs">
                          {scenario.tools.map((t) => (
                            <span
                              key={t}
                              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-text-muted"
                            >
                              <Layers size={12} />
                              {t}
                            </span>
                          ))}
                          {scenario.clarify_option_id ? (
                            <span className="rounded-md bg-surface-muted px-2 py-1 text-text-muted">
                              引导: {scenario.clarify_option_id}
                            </span>
                          ) : null}
                          {scenario.output_schema_id ? (
                            <span className="rounded-md bg-surface-muted px-2 py-1 text-text-muted">
                              模板: {scenario.output_schema_id}
                            </span>
                          ) : null}
                        </section>
                      )}

                      {showTech && isDev && scenario.tech_setup ? (
                        <section className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                          <strong>技术部说明：</strong> {scenario.tech_setup}
                        </section>
                      ) : null}

                      {showTech && isDev && scenario.tech ? (
                        <section className="rounded-lg bg-[#0f172a] p-3 text-xs text-slate-200 overflow-x-auto">
                          <pre className="whitespace-pre-wrap font-mono leading-relaxed">
                            {JSON.stringify(scenario.tech, null, 2)}
                          </pre>
                        </section>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>

          {data?.departments && isDev ? (
            <section className="mt-8 border-t border-border pt-6">
              <h3 className="text-sm font-semibold text-text mb-3">各部门职责摘要（开发对照）</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {Object.entries(data.departments).map(([id, row]) => (
                  <div key={id} className="rounded-lg border border-border px-3 py-2 text-sm">
                    <div className="font-medium text-text">{row.label || id}</div>
                    <p className="mt-1 text-text-muted text-xs leading-relaxed">{row.summary}</p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
