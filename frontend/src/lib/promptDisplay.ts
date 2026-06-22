/** 提示词层的中文展示名（隐藏内部英文 id，便于运营理解） */

export const PROMPT_SLOT_LABELS: Record<string, string> = {
  persona: "角色人设",
  kb_policy: "知识库 · 行为边界",
  kb_task: "知识库 · 完整检索任务",
  kb_task_fast: "知识库 · 快速检索任务",
  general_tools_policy: "通用回答 · 工具调用规则",
  general_task: "通用回答 · 作答策略",
  output_style: "输出排版与详略",
};

export const PROMPT_CATEGORY_LABELS: Record<string, string> = {
  persona: "① 角色人设",
  policy: "② 行为约束",
  task: "③ 任务指令",
  output: "④ 输出格式",
  custom: "⑤ 自定义扩展",
};

export const PREVIEW_MODE_LABELS: Record<string, string> = {
  kb: "知识库回答",
  general: "通用回答",
};

export function displaySlotLabel(slot: { id: string; label?: string }): string {
  const id = slot.id || "";
  if (slot.label && slot.label !== id) return slot.label;
  return PROMPT_SLOT_LABELS[id] || slot.label || id;
}

export function displayCategoryLabel(cat: string, fallback?: Record<string, string>): string {
  return PROMPT_CATEGORY_LABELS[cat] || fallback?.[cat] || cat;
}
