import { useState, useRef, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchUiConfig, uploadDocument } from "../../api/client";
import { DEPT_OPTIONS, DEPT_LABELS, PERM_OPTIONS, PERM_LABELS } from "../../lib/constants";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Tabs } from "../../components/ui/Tabs";
import { IngestedSourcesTab } from "../../components/admin/IngestedSourcesTab";
import { Badge } from "../../components/ui/Badge";
import { Select } from "../../components/ui/Select";
import { toast } from "sonner";

export function resolveIngestChannel(raw: string | null): "kb" | "exam" {
  return raw === "exam" ? "exam" : "kb";
}

export default function IngestPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const channel = resolveIngestChannel(searchParams.get("channel"));

  const [dept, setDept] = useState("技术部");
  const [perm, setPerm] = useState("internal");
  const [selectedPresets, setSelectedPresets] = useState<string[]>([]);
  const [customTags, setCustomTags] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [batchProgress, setBatchProgress] = useState<{ done: number; total: number } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: ui } = useQuery({
    queryKey: ["uiConfig"],
    queryFn: fetchUiConfig,
    staleTime: 300_000,
  });

  const presets: string[] = (ui?.ingest_tag_presets as string[]) ?? [];
  const exts = ui?.supported_upload_extensions ?? ["txt", "md", "pdf", "docx", "html"];
  const extLabel = exts.map((e) => e.toUpperCase()).join(" · ");
  const acceptExts = exts.map((e) => `.${e}`).join(",");

  const customTagList = customTags
    .replace(/，/g, ",")
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const allTags = (() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const t of [...selectedPresets, ...customTagList]) {
      const key = t.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        out.push(t);
      }
    }
    return out;
  })();

  const uploadMut = useMutation({
    mutationFn: async ({ ingestMode }: { ingestMode: string }) => {
      if (!files.length) throw new Error("请先选择文件");
      const opts = {
        department: dept,
        permission: perm,
        mode: ingestMode,
        tags: allTags,
      };
      const results: { name: string; ok: boolean; message: string }[] = [];
      setBatchProgress({ done: 0, total: files.length });
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        try {
          const data = await uploadDocument(f, opts);
          results.push({ name: f.name, ok: true, message: data?.message || "入库成功" });
        } catch (e) {
          results.push({
            name: f.name,
            ok: false,
            message: e instanceof Error ? e.message : "入库失败",
          });
        }
        setBatchProgress({ done: i + 1, total: files.length });
      }
      setBatchProgress(null);
      return results;
    },
    onSuccess: (results) => {
      const ok = results.filter((r) => r.ok).length;
      const fail = results.length - ok;
      if (fail === 0) {
        toast.success(`全部 ${ok} 个文件入库成功`);
      } else if (ok === 0) {
        toast.error(`全部 ${fail} 个文件入库失败`);
      } else {
        toast.message(`入库完成：成功 ${ok}，失败 ${fail}`);
      }
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["uiConfig"] });
    },
    onError: (e: Error) => {
      setBatchProgress(null);
      toast.error(e.message || "入库失败");
    },
  });

  const togglePreset = (tag: string) => {
    setSelectedPresets((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const setChannel = (id: string) => {
    const next = resolveIngestChannel(id);
    const sp = new URLSearchParams(searchParams);
    if (next === "kb") sp.delete("channel");
    else sp.set("channel", next);
    setSearchParams(sp, { replace: true });
  };

  const renderUploadArea = (ingestMode: string) => {
    const isPre = ingestMode === "pre_cleaned";
    return (
      <div className="space-y-3">
        <p className="text-sm text-text-muted">
          {isPre
            ? "数据已完成清洗，仅解析并入库，不再执行脱敏、去水印等步骤。"
            : "原始未处理数据，将自动调用清洗工具链（解析 → 规范化 → 去水印 → 脱敏）后入库。"}
        </p>

        <div className="flex flex-col gap-2">
          <input
            ref={fileRef}
            type="file"
            multiple
            accept={acceptExts}
            title="选择上传文件（可多选）"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="text-sm text-text file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border file:border-border file:bg-surface file:text-sm file:text-text cursor-pointer"
          />
          {files.length > 0 && (
            <ul className="text-sm text-text-muted space-y-0.5">
              {files.map((f) => (
                <li key={`${f.name}-${f.size}`}>· {f.name}</li>
              ))}
            </ul>
          )}
        </div>

        <Button
          variant="primary"
          disabled={!files.length || uploadMut.isPending}
          onClick={() => uploadMut.mutate({ ingestMode })}
        >
          {uploadMut.isPending
            ? batchProgress
              ? `入库中 ${batchProgress.done}/${batchProgress.total}…`
              : "入库中..."
            : files.length > 1
              ? `确认入库（${files.length} 个文件）`
              : "确认入库"}
        </Button>
      </div>
    );
  };

  const kbPanel = useMemo(
    () => (
      <div className="mt-2">
        <p className="text-xs text-text-muted mb-3">
          制度、手册、FAQ 等进<strong>向量知识库</strong>，用于 Chat 检索问答；
          <strong>不可</strong>在对话中「开始答题」。试卷请切换到「试卷题库」通道。
        </p>
        <Tabs
          defaultTab="upload"
          tabs={[
            {
              id: "upload",
              label: "上传入库",
              content: (
                <div className="admin-panel space-y-6 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <label className="block">
                      <span className="text-sm text-text">归属部门</span>
                      <Select value={dept} onChange={(e) => setDept(e.target.value)} className="mt-1">
                        {DEPT_OPTIONS.map((d) => (
                          <option key={d} value={d}>
                            {DEPT_LABELS[d]}
                          </option>
                        ))}
                      </Select>
                    </label>
                    <label className="block">
                      <span className="text-sm text-text">可见范围</span>
                      <Select value={perm} onChange={(e) => setPerm(e.target.value)} className="mt-1">
                        {PERM_OPTIONS.map((p) => (
                          <option key={p} value={p}>
                            {PERM_LABELS[p]}
                          </option>
                        ))}
                      </Select>
                    </label>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-text mb-1">入库标签（可选）</h3>
                    <p className="text-xs text-text-muted mb-3">
                      标签仅用于检索与分类，不控制权限。内部文档仅本部门可见；公开文档所有部门可见。
                    </p>

                    {presets.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-3">
                        {presets.map((tag) => {
                          const active = selectedPresets.includes(tag);
                          return (
                            <button
                              key={tag}
                              type="button"
                              onClick={() => togglePreset(tag)}
                              className={`px-3 py-1 text-xs rounded-full border cursor-pointer transition-colors ${
                                active
                                  ? "bg-brand text-white border-brand"
                                  : "bg-surface text-text-muted border-border hover:border-brand hover:text-text"
                              }`}
                            >
                              {tag}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    <input
                      type="text"
                      value={customTags}
                      onChange={(e) => setCustomTags(e.target.value)}
                      placeholder="自定义标签（逗号分隔），例如：2024春季, 销售手册"
                      className="flex h-10 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
                    />

                    {allTags.length > 0 && (
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs text-text-muted">将写入标签：</span>
                        {allTags.map((t) => (
                          <Badge key={t} variant="default">
                            {t}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  <Tabs
                    tabs={[
                      { id: "clean", label: "已清洗数据", content: renderUploadArea("pre_cleaned") },
                      { id: "raw", label: "未清洗数据", content: renderUploadArea("uncleaned") },
                    ]}
                    defaultTab="clean"
                  />
                </div>
              ),
            },
            {
              id: "manage",
              label: "已入库文档",
              content: (
                <div className="admin-panel p-4 mt-4">
                  <IngestedSourcesTab />
                </div>
              ),
            },
          ]}
        />
      </div>
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- upload helpers close over latest state
    [dept, perm, presets, selectedPresets, customTags, allTags, files, uploadMut.isPending, batchProgress, acceptExts],
  );

  const examPanel = (
    <div className="admin-panel space-y-4 mt-4 p-5" data-testid="exam-ingest-channel">
      <h3 className="text-sm font-semibold text-text">试卷题库入库（与知识库隔离）</h3>
      <p className="text-sm text-text-muted leading-relaxed">
        高考卷 / 练习卷请走本题库通道：DOCX 公式抽取、清洗拆题、答案关联，写入
        <code className="text-xs mx-1 px-1 rounded bg-surface-muted">exam_bank</code>
        ，供 Chat「开始答题」与组卷使用。
        <strong className="text-text"> 请勿</strong>
        将整卷丢进上方「知识文档」通道——向量切块无法形成可交互标准卷面。
      </p>
      <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
        <li>支持 PDF / Word；扫描件可用 OCR 入库</li>
        <li>入库后得到 <code className="text-xs">source_paper_id</code>，对话可检索并出卷</li>
        <li>数据与 Chat 主向量索引隔离</li>
      </ul>
      <div className="flex flex-wrap gap-2 pt-1">
        <Link
          to="/admin/exam-bank/ingest?step=1"
          className="inline-flex items-center justify-center rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark"
          data-testid="exam-ingest-cta"
        >
          前往题库入库向导
        </Link>
        <Link
          to="/admin/exam-bank/manage"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text hover:border-brand"
        >
          题库管理
        </Link>
        <Link
          to="/admin/exam-bank/assemble"
          className="inline-flex items-center justify-center rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text hover:border-brand"
        >
          智能组卷
        </Link>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="数据入库"
        description={
          channel === "exam"
            ? "试卷进题库（切题 / 公式 / 答题），与知识库向量隔离。"
            : `知识文档支持 ${extLabel}；可选标签、部门与可见范围。`
        }
      />

      <Tabs
        activeTab={channel}
        onTabChange={setChannel}
        tabs={[
          { id: "kb", label: "知识文档", content: kbPanel },
          { id: "exam", label: "试卷题库", content: examPanel },
        ]}
      />
    </div>
  );
}
