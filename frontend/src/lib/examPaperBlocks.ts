/**
 * Extract exam_paper / exam_candidates blocks from assistant markdown or meta.
 */

export type ExamPaperUiBlock = {
  type: "exam_paper";
  source_paper_id: string;
  paper_id?: string;
  title?: string;
};

export type ExamCandidateItem = {
  id: string;
  title: string;
  source_filename?: string;
  question_count?: number;
};

export type ExamCandidatesUiBlock = {
  type: "exam_candidates";
  items: ExamCandidateItem[];
};

const PAPER_FENCE_RE = /```exam_paper\s*([\s\S]*?)```/gi;
const CAND_FENCE_RE = /```exam_candidates\s*([\s\S]*?)```/gi;

export function parseExamPaperFences(content: string): ExamPaperUiBlock[] {
  const out: ExamPaperUiBlock[] = [];
  const s = content || "";
  let m: RegExpExecArray | null;
  const re = new RegExp(PAPER_FENCE_RE.source, "gi");
  while ((m = re.exec(s))) {
    const raw = (m[1] || "").trim();
    if (!raw) continue;
    try {
      const j = JSON.parse(raw) as Record<string, unknown>;
      const sid = String(j.source_paper_id || j.paper_id || "").trim();
      if (!sid) continue;
      out.push({
        type: "exam_paper",
        source_paper_id: sid,
        paper_id: String(j.paper_id || sid),
        title: j.title ? String(j.title) : undefined,
      });
    } catch {
      /* ignore bad fence */
    }
  }
  return out;
}

function normalizeCandidateItems(raw: unknown): ExamCandidateItem[] {
  if (!Array.isArray(raw)) return [];
  const out: ExamCandidateItem[] = [];
  for (const it of raw) {
    if (!it || typeof it !== "object") continue;
    const o = it as Record<string, unknown>;
    const id = String(o.id || o.source_paper_id || "").trim();
    if (!id) continue;
    out.push({
      id,
      title: String(o.title || id),
      source_filename: o.source_filename ? String(o.source_filename) : undefined,
      question_count:
        typeof o.question_count === "number"
          ? o.question_count
          : o.question_count != null
            ? Number(o.question_count) || undefined
            : undefined,
    });
  }
  return out;
}

export function parseExamCandidateFences(content: string): ExamCandidatesUiBlock[] {
  const out: ExamCandidatesUiBlock[] = [];
  const s = content || "";
  let m: RegExpExecArray | null;
  const re = new RegExp(CAND_FENCE_RE.source, "gi");
  while ((m = re.exec(s))) {
    const raw = (m[1] || "").trim();
    if (!raw) continue;
    try {
      const j = JSON.parse(raw) as Record<string, unknown>;
      const items = normalizeCandidateItems(j.items);
      if (!items.length) continue;
      out.push({ type: "exam_candidates", items });
    } catch {
      /* ignore */
    }
  }
  return out;
}

/** Strip exam fences so Markdown does not show raw JSON. */
export function stripExamPaperFences(content: string): string {
  return (content || "")
    .replace(PAPER_FENCE_RE, "")
    .replace(CAND_FENCE_RE, "")
    .trim();
}

export function collectExamPaperBlocks(
  content: string,
  metaBlocks?: Array<{ type?: string; source_paper_id?: string; paper_id?: string; title?: string }>,
): ExamPaperUiBlock[] {
  const fromMeta: ExamPaperUiBlock[] = [];
  for (const b of metaBlocks || []) {
    if (b?.type !== "exam_paper") continue;
    const sid = String(b.source_paper_id || b.paper_id || "").trim();
    if (!sid) continue;
    fromMeta.push({
      type: "exam_paper",
      source_paper_id: sid,
      paper_id: b.paper_id,
      title: b.title,
    });
  }
  const fromFence = parseExamPaperFences(content);
  const seen = new Set<string>();
  const merged: ExamPaperUiBlock[] = [];
  for (const b of [...fromMeta, ...fromFence]) {
    if (seen.has(b.source_paper_id)) continue;
    seen.add(b.source_paper_id);
    merged.push(b);
  }
  return merged;
}

export function collectExamCandidateBlocks(
  content: string,
  metaBlocks?: Array<{
    type?: string;
    items?: Array<{ id?: string; title?: string; source_filename?: string; question_count?: number }>;
  }>,
): ExamCandidatesUiBlock[] {
  const fromMeta: ExamCandidatesUiBlock[] = [];
  for (const b of metaBlocks || []) {
    if (b?.type !== "exam_candidates") continue;
    const items = normalizeCandidateItems(b.items);
    if (items.length) fromMeta.push({ type: "exam_candidates", items });
  }
  const fromFence = parseExamCandidateFences(content);
  // Prefer meta (from tool); merge fence if meta empty
  if (fromMeta.length) return fromMeta;
  return fromFence;
}
