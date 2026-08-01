import { apiFetchBlob, apiGet, apiRequest } from "../api/client";

export type ExamCollection = {
  id: string;
  tenant_id: string;
  name: string;
  subject: string;
  grade: string;
  region: string;
  description: string;
  visibility?: string;
  owner_user_id?: string;
  created_at: string;
  updated_at: string;
};

export type ExamQuestion = {
  id: string;
  collection_id: string;
  qtype: string;
  difficulty: number;
  difficulty_coef?: number;
  cognitive_level?: string;
  discrimination?: number;
  textbook_version?: string;
  stem: string;
  options: string[];
  answer: string;
  analysis: string;
  knowledge_tags: string[];
  region: string;
  year: string;
  chapter?: string;
  quality_status: string;
  source_paper_id?: string;
  question_no?: string;
  media_ingest_id?: string;
  incomplete?: boolean;
  incomplete_reasons?: string[];
};

export type ExamIngestItem = {
  question_no: string;
  qtype: string;
  label?: string;
  stem: string;
  options: string[];
  answer: string;
  analysis: string;
  knowledge_tags?: string[];
  chapter?: string;
  year?: string;
  difficulty?: number;
  selected: boolean;
};

export type ExamSourcePaper = {
  id: string;
  collection_id: string;
  title: string;
  source_filename: string;
  raw_text: string;
  answer_text: string;
  question_ids: string[];
  media_ingest_id?: string;
  created_at: string;
  updated_at: string;
};

export type ExamSubjectMeta = {
  id: string;
  label: string;
  grades: string[];
  qtypes: { id: string; label: string }[];
};

export type ExamExportFormat = "markdown" | "docx" | "pdf";

export type ExamMeta = {
  available: boolean;
  qtypes: string[];
  qtype_labels?: Record<string, string>;
  scene_presets: string[];
  export_formats?: ExamExportFormat[];
  stage?: string;
  stages?: { id: string; label: string }[];
  subjects?: ExamSubjectMeta[];
  common_regions?: string[];
  difficulty_bands?: { id: string; label: string; difficulty_min: number; difficulty_max: number }[];
  llm?: {
    model: string;
    chat_model: string;
    api_base: string;
    source: string;
    key_configured: boolean;
  };
};

export type ExamInventory = {
  collection_id: string;
  total: number;
  total_all?: number;
  filter_applied?: boolean;
  by_qtype: Record<string, number>;
  by_difficulty_band: Record<string, number>;
  by_qtype_labeled?: { id: string; label: string; count: number }[];
  by_tag?: { tag: string; count: number }[];
  by_chapter?: { chapter: string; count: number }[];
  regions?: string[];
  years?: string[];
  custom_qtypes: string[];
};

export type ExamAssembleResult = {
  ok: boolean;
  paper_id: string;
  title: string;
  question_ids: string[];
  questions?: ExamQuestion[];
  counts: Record<string, number>;
  markdown: string;
};

export function fetchExamMeta(opts?: { stage?: string; grade?: string }) {
  const q = new URLSearchParams();
  if (opts?.stage) q.set("stage", opts.stage);
  if (opts?.grade) q.set("grade", opts.grade);
  const qs = q.toString();
  return apiGet<ExamMeta>(`/api/exam/meta${qs ? `?${qs}` : ""}`);
}

export function fetchExamLlmStatus() {
  return apiGet<{
    ok: boolean;
    configured: boolean;
    model: string;
    source: string;
    api_base: string;
    message: string;
  }>("/api/exam/llm-status");
}

export function fetchExamCollections(opts?: {
  subject?: string;
  grade?: string;
  region?: string;
}) {
  const q = new URLSearchParams();
  if (opts?.subject) q.set("subject", opts.subject);
  if (opts?.grade) q.set("grade", opts.grade);
  if (opts?.region) q.set("region", opts.region);
  const qs = q.toString();
  return apiGet<{ items: ExamCollection[]; total: number }>(
    `/api/exam/collections${qs ? `?${qs}` : ""}`,
  );
}

export function fetchExamInventory(
  collectionId: string,
  opts?: { tags?: string[]; chapters?: string[]; regions?: string[]; years?: string[] },
) {
  const q = new URLSearchParams({ collection_id: collectionId });
  for (const t of opts?.tags || []) {
    if (t.trim()) q.append("tag", t.trim());
  }
  for (const c of opts?.chapters || []) {
    if (c.trim()) q.append("chapter", c.trim());
  }
  for (const r of opts?.regions || []) {
    if (r.trim()) q.append("region", r.trim());
  }
  for (const y of opts?.years || []) {
    if (y.trim()) q.append("year", y.trim());
  }
  return apiGet<ExamInventory>(`/api/exam/inventory?${q}`);
}

export function detectExamSections(body: {
  text: string;
  subject?: string;
  grade?: string;
  use_llm?: boolean;
}) {
  return apiRequest<{
    sections: { heading: string; qtype: string; label: string; start_line: number; approx_count?: number }[];
    router: string;
    note: string;
    subject?: string;
    grade?: string;
    stage?: string;
    suggested_qtypes?: { id: string; label: string }[];
    confidence?: number;
    model?: string;
    llm_source?: string;
    api_base?: string;
  }>("/api/exam/analyze-paper", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_llm: true, ...body }),
  });
}

export function createExamCollection(body: {
  name: string;
  subject: string;
  grade: string;
  region: string;
  description?: string;
  visibility?: string;
}) {
  return apiRequest<ExamCollection>("/api/exam/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteExamCollection(id: string) {
  return apiRequest<{ ok: boolean; id: string }>(`/api/exam/collections/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function purgeExamBank() {
  return apiRequest<{ ok: boolean; deleted?: Record<string, number> }>("/api/exam/admin/purge", {
    method: "POST",
  });
}

export function fetchExamSourcePaper(id: string) {
  return apiGet<ExamSourcePaper>(`/api/exam/source-papers/${encodeURIComponent(id)}`);
}

export function fetchExamQuestions(
  collectionId: string,
  opts?: {
    status?: string;
    q?: string;
    limit?: number;
    completeness?: "incomplete" | "complete" | "";
  },
) {
  const q = new URLSearchParams({
    collection_id: collectionId,
    status: opts?.status ?? "all",
    limit: String(opts?.limit ?? 200),
  });
  if (opts?.q?.trim()) q.set("q", opts.q.trim());
  if (opts?.completeness) q.set("completeness", opts.completeness);
  return apiGet<{ items: ExamQuestion[]; total: number }>(`/api/exam/questions?${q}`);
}

export function llmCompleteExamQuestion(id: string) {
  return apiRequest<{
    ok: boolean;
    skipped?: boolean;
    updated_fields?: string[];
    model?: string;
    question: ExamQuestion;
  }>(`/api/exam/questions/${encodeURIComponent(id)}/llm-complete`, {
    method: "POST",
  });
}

export function llmCompleteExamCollectionIncomplete(
  collectionId: string,
  opts?: { limit?: number },
) {
  const q = new URLSearchParams({
    limit: String(opts?.limit ?? 10),
  });
  return apiRequest<{
    ok: boolean;
    attempted: number;
    updated: number;
    failed: number;
    errors: string[];
  }>(
    `/api/exam/collections/${encodeURIComponent(collectionId)}/llm-complete-incomplete?${q}`,
    { method: "POST" },
  );
}

export function generateExamLesson(paperId: string) {
  return apiRequest<{
    ok: boolean;
    paper_id: string;
    title: string;
    markdown: string;
    question_count: number;
  }>(`/api/exam/papers/${encodeURIComponent(paperId)}/lesson`, {
    method: "POST",
  });
}

export function createExamQuestion(body: {
  collection_id: string;
  qtype: string;
  difficulty: number;
  stem: string;
  options?: string[];
  answer?: string;
  analysis?: string;
  knowledge_tags?: string[];
  quality_status?: string;
  question_no?: string;
}) {
  return apiRequest<ExamQuestion>("/api/exam/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function updateExamQuestion(
  id: string,
  body: Partial<{
    qtype: string;
    difficulty: number;
    stem: string;
    options: string[];
    answer: string;
    analysis: string;
    knowledge_tags: string[];
    quality_status: string;
    question_no: string;
  }>,
) {
  return apiRequest<ExamQuestion>(`/api/exam/questions/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteExamQuestion(id: string) {
  return apiRequest<{ ok: boolean; id: string }>(`/api/exam/questions/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function parseExamIngest(body: {
  text: string;
  subject?: string;
  grade?: string;
  region?: string;
  stage?: string;
  use_llm?: boolean;
  clean?: boolean;
}) {
  return apiRequest<{
    items: ExamIngestItem[];
    item_count: number;
    answers_embedded?: boolean;
    skipped_non_questions?: number;
    paper_label?: string;
    sections?: { heading: string; qtype: string; label: string }[];
    raw_text?: string;
    cleaned_text?: string;
    clean_applied?: boolean;
    clean_warnings?: string[];
    removed_sections?: string[];
    media?: { eq_id: string; filename?: string; ingest_id?: string; url?: string }[];
    eq_count?: number;
    router?: string;
    model?: string;
    error?: string;
    message?: string;
  }>("/api/exam/ingest/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ use_llm: true, clean: true, ...body }),
    // 整卷拆题常 >60s；与 upload 对齐，避免 Chat 能用但拆题被前端 abort
    timeoutMs: 180_000,
  });
}

export function cleanExamIngest(text: string) {
  return apiRequest<{
    cleaned: string;
    removed_sections: string[];
    warnings: string[];
    stats: Record<string, number>;
  }>("/api/exam/ingest/clean", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function uploadExamIngest(
  file: File,
  opts?: {
    subject?: string;
    grade?: string;
    region?: string;
    stage?: string;
    use_llm?: boolean;
    clean?: boolean;
  },
) {
  const form = new FormData();
  form.append("file", file);
  form.append("subject", opts?.subject || "");
  form.append("grade", opts?.grade || "");
  form.append("region", opts?.region || "");
  form.append("stage", opts?.stage || "");
  form.append("use_llm", String(opts?.use_llm ?? true));
  form.append("clean", String(opts?.clean ?? true));
  return apiRequest<{
    items: ExamIngestItem[];
    item_count: number;
    answers_embedded?: boolean;
    skipped_non_questions?: number;
    paper_label?: string;
    source_filename?: string;
    raw_text?: string;
    cleaned_text?: string;
    clean_applied?: boolean;
    clean_warnings?: string[];
    removed_sections?: string[];
    media?: { eq_id: string; filename?: string; ingest_id?: string; url?: string }[];
    eq_count?: number;
    extract_warnings?: string[];
    ingest_id?: string;
    sections?: { heading: string; qtype: string; label: string }[];
    router?: string;
    model?: string;
    error?: string;
    message?: string;
  }>("/api/exam/ingest/upload", { method: "POST", body: form, timeoutMs: 180_000 });
}

export function fetchExamOcrStatus() {
  return apiGet<{
    available: boolean;
    missing: string[];
    engines: string[];
    hint: string;
    supported_suffixes: string[];
    pdf_render_ready: boolean;
  }>("/api/exam/ingest/ocr/status");
}

export async function uploadExamOcrIngest(
  file: File,
  opts?: {
    subject?: string;
    grade?: string;
    region?: string;
    stage?: string;
    use_llm?: boolean;
    clean?: boolean;
    maxPages?: number;
  },
) {
  const form = new FormData();
  form.append("file", file);
  form.append("subject", opts?.subject || "");
  form.append("grade", opts?.grade || "");
  form.append("region", opts?.region || "");
  form.append("stage", opts?.stage || "");
  form.append("use_llm", String(opts?.use_llm ?? true));
  form.append("clean", String(opts?.clean ?? true));
  form.append("max_pages", String(opts?.maxPages ?? 40));
  return apiRequest<{
    items: ExamIngestItem[];
    item_count: number;
    answers_embedded?: boolean;
    source_filename?: string;
    raw_text?: string;
    cleaned_text?: string;
    clean_applied?: boolean;
    clean_warnings?: string[];
    ocr_applied?: boolean;
    ocr_engine?: string;
    ocr_page_count?: number;
    ocr_warnings?: string[];
    sections?: { heading: string; qtype: string; label: string }[];
    router?: string;
    error?: string;
    message?: string;
  }>("/api/exam/ingest/ocr", { method: "POST", body: form, timeoutMs: 600_000 });
}

export function commitExamIngest(body: {
  collection_id: string;
  title?: string;
  source_filename?: string;
  raw_text?: string;
  region?: string;
  year?: string;
  quality_status?: string;
  media_ingest_id?: string;
  items: ExamIngestItem[];
}) {
  return apiRequest<{
    source_paper: ExamSourcePaper;
    questions: ExamQuestion[];
    total: number;
  }>("/api/exam/ingest/commit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function applyExamAnswers(body: { source_paper_id: string; answer_text: string }) {
  return apiRequest<{
    ok: boolean;
    updated: number;
    unmatched: string[];
    source_paper: ExamSourcePaper;
  }>("/api/exam/ingest/apply-answers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchExamSourcePapers(collectionId: string) {
  const q = new URLSearchParams({ collection_id: collectionId });
  return apiGet<{ items: ExamSourcePaper[]; total: number }>(`/api/exam/source-papers?${q}`);
}

export function assembleExamPaper(body: {
  collection_id: string;
  title: string;
  include_answers?: boolean;
  spec: {
    by_qtype: Record<string, number>;
    by_difficulty_band?: Record<string, number>;
    by_qtype_band?: Record<string, Record<string, number>>;
    difficulty_min?: number;
    difficulty_max?: number;
    knowledge_tags_any?: string[];
    chapters_any?: string[];
    regions_any?: string[];
    years_any?: string[];
    soft_fallback?: boolean;
    require_complete?: boolean;
    difficulty_target_coef?: number;
    seed?: number;
  };
}) {
  return apiRequest<ExamAssembleResult>("/api/exam/papers/assemble", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** 11.txt：智能组卷（默认 soft_fallback） */
export function autoGenerateExamPaper(body: {
  collection_id: string;
  title: string;
  include_answers?: boolean;
  spec: Parameters<typeof assembleExamPaper>[0]["spec"];
}) {
  return apiRequest<
    ExamAssembleResult & { fallback_applied?: boolean; fallback_notes?: string[] }
  >("/api/exam/papers/auto-generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function assembleExamPaperNl(body: {
  collection_id: string;
  text: string;
  title?: string;
  include_answers?: boolean;
}) {
  return apiRequest<
    ExamAssembleResult & {
      parsed_spec?: Record<string, unknown>;
      nl_summary?: string;
      nl_message?: string;
    }
  >("/api/exam/papers/assemble-nl", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function finalizeExamBasket(body: {
  collection_id: string;
  title: string;
  question_ids: string[];
  include_answers?: boolean;
}) {
  return apiRequest<ExamAssembleResult>("/api/exam/papers/from-questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function swapExamQuestion(body: {
  collection_id: string;
  question_id: string;
  exclude_ids?: string[];
  limit?: number;
  soft_fallback?: boolean;
}) {
  return apiRequest<{
    ok: boolean;
    candidates: ExamQuestion[];
    fallback_applied?: boolean;
    fallback_notes?: string[];
  }>("/api/exam/questions/swap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const EXAM_EXPORT_FORMAT_OPTIONS: { id: ExamExportFormat; label: string }[] = [
  { id: "docx", label: "Word（推荐，公式可编辑）" },
  { id: "pdf", label: "PDF（预览/打印）" },
  { id: "markdown", label: "Markdown (.md)" },
];

/** Preferred default — GB Word preserves formulas better than PDF rasterization. */
export const DEFAULT_EXAM_EXPORT_FORMAT: ExamExportFormat = "docx";

/** Download assembled paper as markdown / docx / pdf via Content-Disposition. */
export async function downloadExamPaperExport(
  paperId: string,
  format: ExamExportFormat,
  opts?: { includeAnswers?: boolean; fallbackFilename?: string },
) {
  const q = new URLSearchParams({
    format,
    include_answers: String(opts?.includeAnswers ?? true),
  });
  const { blob, filename } = await apiFetchBlob(
    `/api/exam/papers/${encodeURIComponent(paperId)}/export?${q}`,
  );
  const name =
    filename ||
    opts?.fallbackFilename ||
    `试卷.${format === "markdown" ? "md" : format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Parse FastAPI 400 detail for assemble errors. */
export function formatExamApiError(raw: string): string {
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    const d = j.detail;
    if (d && typeof d === "object" && !Array.isArray(d)) {
      const obj = d as {
        detail?: { message?: string } | string;
        message?: string;
        error?: string;
      };
      const inner = obj.detail;
      if (inner && typeof inner === "object" && inner.message) return String(inner.message);
      if (typeof inner === "string" && inner.trim()) return inner;
      if (obj.message) return String(obj.message);
      if (obj.error) {
        const code = String(obj.error);
        if (code === "insufficient_difficulty") {
          return "题库难度档题量不足，已尽量组卷仍失败；请减少题量或换「全部难度」";
        }
        if (code === "insufficient_qtype") {
          return "题库该题型数量不足，请减少需求题量或换库";
        }
        return code;
      }
    }
    if (typeof d === "string") return d;
    if (typeof d === "object" && d && "message" in (d as object)) {
      return String((d as { message: string }).message);
    }
  } catch {
    /* plain text */
  }
  return raw;
}

// ===== Chat 标准卷面 / 答题 =====

export type ChatPaperItem = {
  id: string;
  no: string;
  qtype: string;
  qtype_label?: string;
  score?: number;
  stem: string;
  options: string[];
  media_ingest_id?: string;
  answer?: string;
  analysis?: string;
};

export type ChatPaperSection = {
  heading: string;
  qtype: string;
  items: ChatPaperItem[];
};

export type ChatExamPaper = {
  ok?: boolean;
  type: "exam_paper";
  paper_id: string;
  source_paper_id?: string;
  collection_id?: string;
  title: string;
  source_filename?: string;
  media_ingest_id?: string;
  meta: {
    total_score: number;
    question_count: number;
    duration_min?: number;
  };
  sections: ChatPaperSection[];
  mode: "preview" | "review" | string;
};

export type ChatAttemptStart = {
  ok: boolean;
  attempt_id: string;
  status: string;
  paper: ChatExamPaper;
  started_at?: string;
};

export type ChatAttemptSubmit = {
  ok: boolean;
  attempt_id: string;
  status: string;
  correct_count: number;
  graded_count: number;
  score: number;
  max_score: number;
  results: Array<{
    question_id: string;
    qtype: string;
    user_answer: string;
    answer: string;
    analysis: string;
    correct: boolean | null;
    scored: boolean;
  }>;
};

export type ChatExplainResult = {
  ok: boolean;
  question_id: string;
  explanation: string;
  is_correct?: boolean | null;
  score_hint?: string;
  key_points?: string[];
  reference_answer?: string;
  reference_analysis?: string;
  model?: string;
  error?: string;
  message?: string;
};

export function fetchChatExamPaper(sourcePaperId: string, includeAnswers = false) {
  const q = new URLSearchParams({ include_answers: String(includeAnswers) });
  return apiGet<ChatExamPaper>(
    `/api/exam/chat/papers/${encodeURIComponent(sourcePaperId)}?${q}`,
  );
}

export function searchChatExamPapers(query: string, limit = 10) {
  const q = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<{
    ok: boolean;
    q: string;
    items: Array<{
      id: string;
      title: string;
      source_filename: string;
      collection_id: string;
      question_count: number;
      created_at: string;
    }>;
    total: number;
  }>(`/api/exam/chat/papers/search?${q}`);
}

export function startChatExamAttempt(sourcePaperId: string) {
  return apiRequest<ChatAttemptStart>("/api/exam/chat/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_paper_id: sourcePaperId }),
  });
}

export function submitChatExamAttempt(attemptId: string, answers: Record<string, string>) {
  return apiRequest<ChatAttemptSubmit>(
    `/api/exam/chat/attempts/${encodeURIComponent(attemptId)}/submit`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    },
  );
}

export function explainChatExamQuestion(questionId: string, userAnswer = "") {
  return apiRequest<ChatExplainResult>(
    `/api/exam/chat/questions/${encodeURIComponent(questionId)}/explain`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_answer: userAnswer }),
    },
  );
}
