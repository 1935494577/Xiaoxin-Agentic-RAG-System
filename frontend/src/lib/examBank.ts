import { apiGet, apiRequest } from "../api/client";

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
  stem: string;
  options: string[];
  answer: string;
  analysis: string;
  knowledge_tags: string[];
  region: string;
  year: string;
  quality_status: string;
};

export type ExamSubjectMeta = {
  id: string;
  label: string;
  grades: string[];
  qtypes: { id: string; label: string }[];
};

export type ExamMeta = {
  available: boolean;
  qtypes: string[];
  qtype_labels?: Record<string, string>;
  scene_presets: string[];
  stage?: string;
  stages?: { id: string; label: string }[];
  subjects?: ExamSubjectMeta[];
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
  by_qtype: Record<string, number>;
  by_difficulty_band: Record<string, number>;
  by_qtype_labeled?: { id: string; label: string; count: number }[];
  custom_qtypes: string[];
};

export type ExamAssembleResult = {
  ok: boolean;
  paper_id: string;
  title: string;
  question_ids: string[];
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

export function fetchExamCollections(opts?: {
  tenantId?: string;
  subject?: string;
  grade?: string;
  readerUserId?: string;
}) {
  const q = new URLSearchParams();
  q.set("tenant_id", opts?.tenantId || "internal");
  if (opts?.subject) q.set("subject", opts.subject);
  if (opts?.grade) q.set("grade", opts.grade);
  if (opts?.readerUserId) q.set("reader_user_id", opts.readerUserId);
  return apiGet<{ items: ExamCollection[]; total: number }>(`/api/exam/collections?${q}`);
}

export function fetchExamInventory(collectionId: string) {
  return apiGet<ExamInventory>(
    `/api/exam/inventory?collection_id=${encodeURIComponent(collectionId)}`,
  );
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
  owner_user_id?: string;
}) {
  return apiRequest<ExamCollection>("/api/exam/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function fetchExamQuestions(collectionId: string, status = "published") {
  const q = new URLSearchParams({
    collection_id: collectionId,
    status,
    limit: "100",
  });
  return apiGet<{ items: ExamQuestion[]; total: number }>(`/api/exam/questions?${q}`);
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
}) {
  return apiRequest<ExamQuestion>("/api/exam/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function assembleExamPaper(body: {
  collection_id: string;
  title: string;
  include_answers?: boolean;
  spec: {
    by_qtype: Record<string, number>;
    by_difficulty_band?: Record<string, number>;
    difficulty_min?: number;
    difficulty_max?: number;
    seed?: number;
  };
}) {
  return apiRequest<ExamAssembleResult>("/api/exam/papers/assemble", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** Parse FastAPI 400 detail for assemble errors. */
export function formatExamApiError(raw: string): string {
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    const d = j.detail;
    if (d && typeof d === "object" && !Array.isArray(d)) {
      const obj = d as { detail?: { message?: string }; message?: string; error?: string };
      const inner = obj.detail;
      if (inner && typeof inner === "object" && inner.message) return String(inner.message);
      if (obj.message) return String(obj.message);
      if (typeof (d as { detail?: unknown }).detail === "object") {
        const nested = (d as { detail: { message?: string } }).detail;
        if (nested?.message) return nested.message;
      }
    }
    if (typeof d === "object" && d && "message" in (d as object)) {
      return String((d as { message: string }).message);
    }
  } catch {
    /* plain text */
  }
  return raw;
}
