import { useState } from "react";
import { FileText } from "lucide-react";
import { Dialog } from "../ui/Dialog";
import { Skeleton } from "../ui/Skeleton";
import { fetchSourcePreview } from "../../api/client";

type Props = {
  parentId: string;
  label: string;
  department: string;
};

export function SourcePreviewButton({ parentId, label, department }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [text, setText] = useState("");
  const [meta, setMeta] = useState("");

  const openPreview = async () => {
    setOpen(true);
    setLoading(true);
    setText("");
    setMeta("");
    try {
      const row = await fetchSourcePreview(parentId, department);
      setText(row.text || "（无正文）");
      setMeta(`${row.source} · ${row.department} · ${row.permission_label}`);
    } catch {
      setText("无法加载原文，可能无权限或片段已删除。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={openPreview}
        className="inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-1 text-left text-xs text-text transition-all hover:border-brand/40 hover:bg-brand-light/60 hover:text-brand"
      >
        <FileText className="h-3.5 w-3.5 shrink-0 text-text-muted" aria-hidden />
        <span className="truncate">{label}</span>
      </button>
      <Dialog open={open} onClose={() => setOpen(false)} title="引用原文" confirmLabel="关闭">
        <div className="space-y-3 text-sm max-h-[60vh] overflow-y-auto">
          {loading ? (
            <div className="space-y-2 py-1" role="status" aria-label="加载中">
              <Skeleton className="h-3 w-2/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ) : (
            <>
              {meta ? <p className="text-xs text-text-muted break-all">{meta}</p> : null}
              <pre className="whitespace-pre-wrap font-sans text-text bg-surface-muted rounded-lg p-3 text-sm leading-relaxed">
                {text}
              </pre>
            </>
          )}
        </div>
      </Dialog>
    </>
  );
}
