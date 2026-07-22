export type AssistantMode = "knowledge" | "task" | "auto";

export type AssistantModeOption = {
  id: AssistantMode;
  label: string;
  description: string;
};

export const ASSISTANT_MODE_STORAGE_KEY = "jnao_assistant_mode";

export const ASSISTANT_MODE_OPTIONS: AssistantModeOption[] = [
  {
    id: "knowledge",
    label: "知识",
    description: "优先知识库检索，回答带引用",
  },
  {
    id: "task",
    label: "任务",
    description: "多步推理与工具，帮你完成事项",
  },
  {
    id: "auto",
    label: "自动",
    description: "按问题与配置自动选择",
  },
];

export function normalizeAssistantMode(raw: string | null | undefined): AssistantMode {
  const key = (raw || "knowledge").trim().toLowerCase();
  if (key === "knowledge" || key === "task" || key === "auto") return key;
  return "knowledge";
}

export function loadStoredAssistantMode(): AssistantMode | null {
  try {
    const raw = localStorage.getItem(ASSISTANT_MODE_STORAGE_KEY);
    if (!raw) return null;
    return normalizeAssistantMode(raw);
  } catch {
    return null;
  }
}

export function saveStoredAssistantMode(mode: AssistantMode): void {
  try {
    localStorage.setItem(ASSISTANT_MODE_STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function resolveDefaultAssistantMode(
  uiDefault?: string | null,
  stored?: AssistantMode | null
): AssistantMode {
  if (stored != null) return stored;
  return normalizeAssistantMode(uiDefault ?? "knowledge");
}

export function placeholderForMode(mode: AssistantMode): string {
  if (mode === "task") {
    return "描述要完成的任务，助手会检索知识库并使用工具分步完成";
  }
  if (mode === "knowledge") {
    return "输入问题，助手将基于知识库内容回答";
  }
  return "输入问题；助手将按配置自动选择知识库或任务模式";
}

export function labelForMode(mode: AssistantMode): string {
  return ASSISTANT_MODE_OPTIONS.find((o) => o.id === mode)?.label ?? "自动";
}
