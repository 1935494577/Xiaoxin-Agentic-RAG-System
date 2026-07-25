import { useEffect, useState } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import { readAuthHeaders } from "../../../api/client";

type ExamMathTextProps = {
  text: string;
  className?: string;
  /** When set, ``[[EQ:n]]`` loads formula images with auth (not bare <img>). */
  mediaIngestId?: string;
};

type Seg =
  | { kind: "text"; value: string }
  | { kind: "eq"; id: string };

function splitEqSegments(raw: string): Seg[] {
  const s = raw || "";
  const re = /\[\[EQ:(\d+)\]\]/g;
  const out: Seg[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push({ kind: "text", value: s.slice(last, m.index) });
    out.push({ kind: "eq", id: m[1] });
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push({ kind: "text", value: s.slice(last) });
  return out.length ? out : [{ kind: "text", value: s }];
}

/** Fetch EQ image with session Authorization — bare <img src> would 401. */
function ExamEqImage({ ingestId, eqId }: { ingestId: string; eqId: string }) {
  const [url, setUrl] = useState<string>("");
  const [err, setErr] = useState(false);

  useEffect(() => {
    let revoked = "";
    let cancelled = false;
    const path = `/api/exam/ingest/media/${encodeURIComponent(ingestId)}/eq/${encodeURIComponent(eqId)}`;
    void (async () => {
      try {
        const res = await fetch(path, { headers: { ...readAuthHeaders() } });
        if (!res.ok) throw new Error(String(res.status));
        const blob = await res.blob();
        // OLE .bin etc. — browser cannot paint
        if (!blob.type.startsWith("image/") && blob.size > 0) {
          const head = new Uint8Array(await blob.slice(0, 8).arrayBuffer());
          // PNG / JPEG / GIF magic
          const isPng = head[0] === 0x89 && head[1] === 0x50;
          const isJpg = head[0] === 0xff && head[1] === 0xd8;
          const isGif = head[0] === 0x47 && head[1] === 0x49;
          if (!isPng && !isJpg && !isGif) {
            if (!cancelled) setErr(true);
            return;
          }
        }
        const u = URL.createObjectURL(blob);
        revoked = u;
        if (!cancelled) setUrl(u);
      } catch {
        if (!cancelled) setErr(true);
      }
    })();
    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [ingestId, eqId]);

  if (err) {
    return (
      <span
        className="inline-flex items-center rounded border border-dashed border-warning/50 px-1 text-[10px] text-warning align-middle"
        title={`公式 ${eqId} 暂无可用图片（多为 MathType OLE，需优先抽取预览图）`}
      >
        [公式{eqId}]
      </span>
    );
  }
  if (!url) {
    return <span className="inline-block w-8 h-4 bg-surface-muted/60 align-middle animate-pulse rounded" />;
  }
  return (
    <img
      src={url}
      alt={`公式${eqId}`}
      className="exam-eq-img inline-block max-h-10 max-w-[min(100%,280px)] align-middle mx-0.5"
    />
  );
}

function KatexChunk({ text }: { text: string }) {
  const html = renderKatexHtml(text || "");
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function collapseSpacedCjk(raw: string): string {
  // Mirror backend paper_clean.collapse_spaced_cjk for already-loaded cards
  const cjk =
    /([\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff01-\uff60\uffe0-\uffe6])\s+([\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff01-\uff60\uffe0-\uffe6])/g;
  const parts = (raw || "").split(/(\[\[EQ:\d+\]\])/);
  return parts
    .map((part) => {
      if (part.startsWith("[[EQ:")) return part;
      let cur = part;
      let prev = "";
      while (prev !== cur) {
        prev = cur;
        cur = cur.replace(cjk, "$1$2");
      }
      return cur.replace(/[^\S\n]{2,}/g, " ");
    })
    .join("");
}

export { collapseSpacedCjk };

/** Render stem/options with KaTeX and authenticated [[EQ:n]] images. */
export function ExamMathText({ text, className, mediaIngestId }: ExamMathTextProps) {
  const mid = (mediaIngestId || "").trim();
  const normalized = collapseSpacedCjk(text || "");
  const segs = splitEqSegments(normalized);

  const missingFig =
    !mid &&
    !/\[\[EQ:\d+\]\]/.test(normalized) &&
    (normalized.match(/\n{3,}/g) || []).length > 0;

  return (
    <span className={className}>
      {missingFig ? (
        <span className="mb-1 block rounded border border-dashed border-warning/40 bg-warning/5 px-2 py-1 text-[11px] text-warning">
          几何图/插图未随 PDF 纯文本入库；请用 Word 卷或 Structure 公式识别重入库。
        </span>
      ) : null}
      {segs.map((seg, i) => {
        if (seg.kind === "eq") {
          if (!mid) {
            return (
              <span key={i} className="text-warning text-xs">
                [[EQ:{seg.id}]]
              </span>
            );
          }
          return <ExamEqImage key={`${seg.id}-${i}`} ingestId={mid} eqId={seg.id} />;
        }
        return <KatexChunk key={i} text={seg.value} />;
      })}
    </span>
  );
}

export function renderExamMath(raw: string, _mediaIngestId?: string): string {
  // Kept for non-React callers; EQ placeholders stay literal without auth fetch.
  return renderKatexHtml(raw || "");
}

function renderKatexHtml(s: string): string {
  if (!/[\\$]/.test(s) && !s.includes("\\(")) {
    return escapeHtml(s).replace(/\n/g, "<br/>");
  }
  try {
    let out = s;
    out = out.replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) =>
      katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false }),
    );
    out = out.replace(/\\\(([\s\S]+?)\\\)/g, (_, tex) =>
      katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false }),
    );
    out = out.replace(/\$([^$\n]+?)\$/g, (_, tex) =>
      katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false }),
    );
    if (!out.includes("katex")) {
      return escapeHtml(s).replace(/\n/g, "<br/>");
    }
    return out.replace(/\n/g, "<br/>");
  } catch {
    return escapeHtml(s).replace(/\n/g, "<br/>");
  }
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
