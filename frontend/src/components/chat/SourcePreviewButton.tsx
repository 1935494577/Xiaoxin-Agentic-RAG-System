import { useState } from "react";
import { Dialog } from "../ui/Dialog";
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
        className="text-brand hover:underline cursor-pointer break-all text-left"
      >
        {label}
      </button>
      <Dialog open={open} onClose={() => setOpen(false)} title="引用原文" confirmLabel="关闭">
        <div className="space-y-3 text-sm max-h-[60vh] overflow-y-auto">
          {loading ? (
            <p className="text-text-muted">加载中…</p>
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
