/** Session draft for exam-bank ingest wizard. */

export type ExamWizardDraft = {
  stage: string;
  subject: string;
  grade: string;
  region: string;
  /** 试卷优先年份（写入每题 year，组卷可筛） */
  paperYear: string;
  visibility: string;
  collectionName: string;
  collectionId: string;
  useLlm: boolean;
  paperText: string;
  cleanedText: string;
  cleanWarningsJson: string;
  mediaJson: string;
  ingestFilename: string;
  ingestRawText: string;
  draftItemsJson: string;
  sourcePaperId: string;
  answerText: string;
  answersEmbedded: boolean;
  step: number;
};

/** v2：基本信息 + 题库空间合并为第 1 步（共 4 步） */
const KEY_PREFIX = "examWizard:v2:";

export const DEFAULT_WIZARD_DRAFT: ExamWizardDraft = {
  stage: "junior",
  subject: "数学",
  grade: "初二",
  region: "",
  paperYear: "",
  visibility: "private",
  collectionName: "",
  collectionId: "",
  useLlm: true,
  paperText: "",
  cleanedText: "",
  cleanWarningsJson: "[]",
  mediaJson: "[]",
  ingestFilename: "",
  ingestRawText: "",
  draftItemsJson: "[]",
  sourcePaperId: "",
  answerText: "",
  answersEmbedded: false,
  step: 1,
};

export function loadExamWizardDraft(userId: string): ExamWizardDraft {
  try {
    const raw = sessionStorage.getItem(KEY_PREFIX + (userId || "anon"));
    if (!raw) return { ...DEFAULT_WIZARD_DRAFT };
    const parsed = { ...DEFAULT_WIZARD_DRAFT, ...JSON.parse(raw) } as ExamWizardDraft;
    parsed.step = Math.min(INGEST_STEPS.length, Math.max(1, Number(parsed.step) || 1));
    return parsed;
  } catch {
    return { ...DEFAULT_WIZARD_DRAFT };
  }
}

export function saveExamWizardDraft(userId: string, draft: ExamWizardDraft): void {
  try {
    sessionStorage.setItem(KEY_PREFIX + (userId || "anon"), JSON.stringify(draft));
  } catch {
    /* ignore quota */
  }
}

export function clearExamWizardDraft(userId: string): void {
  try {
    sessionStorage.removeItem(KEY_PREFIX + (userId || "anon"));
  } catch {
    /* ignore */
  }
}

export const INGEST_STEPS = [
  { id: 1, label: "题库设置" },
  { id: 2, label: "导入解析" },
  { id: 3, label: "预览编辑" },
  { id: 4, label: "答案关联" },
] as const;
