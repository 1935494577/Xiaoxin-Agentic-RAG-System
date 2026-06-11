import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchUiConfig, uploadDocument } from "../../api/client";
import { DEPT_OPTIONS, DEPT_LABELS, PERM_OPTIONS, PERM_LABELS } from "../../lib/constants";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { Tabs } from "../../components/ui/Tabs";
import { Badge } from "../../components/ui/Badge";
import { Select } from "../../components/ui/Select";
import { toast } from "sonner";

export default function IngestPage() {
  const queryClient = useQueryClient();
  const [dept, setDept] = useState("技术部");
  const [perm, setPerm] = useState("internal");
  const [selectedPresets, setSelectedPresets] = useState<string[]>([]);
  const [customTags, setCustomTags] = useState("");
  const [file, setFile] = useState<File | null>(null);
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
    mutationFn: async ({
      ingestMode,
    }: {
      ingestMode: string;
    }) => {
      if (!file) throw new Error("请先选择文件");
      return uploadDocument(file, {
        department: dept,
        permission: perm,
        mode: ingestMode,
        tags: allTags,
      });
    },
    onSuccess: (data) => {
      toast.success(data?.message || "入库成功");
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["uiConfig"] });
    },
    onError: (e: Error) => toast.error(e.message || "入库失败"),
  });

  const togglePreset = (tag: string) => {
    setSelectedPresets((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
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

        <div className="flex items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept={acceptExts}
            title="选择上传文件"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-text file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border file:border-border file:bg-white file:text-sm file:text-text cursor-pointer"
          />
          {file && <span className="text-sm text-text-muted">已选择：{file.name}</span>}
        </div>

        <Button
          variant="primary"
          disabled={!file || uploadMut.isPending}
          onClick={() => uploadMut.mutate({ ingestMode })}
        >
          {uploadMut.isPending ? "入库中..." : "确认入库"}
        </Button>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-[780px]">
      <PageHeader
        title="数据入库"
        description={`支持 ${extLabel} 格式；可选标签、部门与可见范围。`}
      />

      <div className="space-y-6">
        {/* Department & Permission */}
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

        {/* Tag picker */}
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
                        : "bg-white text-text-muted border-border hover:border-brand hover:text-text"
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
            className="flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
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

        {/* Tabs */}
        <Tabs
          tabs={[
            { id: "clean", label: "已清洗数据", content: renderUploadArea("pre_cleaned") },
            { id: "raw", label: "未清洗数据", content: renderUploadArea("uncleaned") },
          ]}
          defaultTab="clean"
        />
      </div>
    </div>
  );
}
