export const DEPT_OPTIONS = ["general", "技术", "市场", "人事", "财务"] as const;
export type Department = (typeof DEPT_OPTIONS)[number];

export const DEPT_LABELS: Record<Department, string> = {
  general: "通用",
  "技术": "技术",
  "市场": "市场",
  "人事": "人事",
  "财务": "财务",
};

export const PERM_OPTIONS = ["public", "internal", "confidential"] as const;
export type Permission = (typeof PERM_OPTIONS)[number];

export const PERM_LABELS: Record<Permission, string> = {
  public: "公开",
  internal: "内部",
  confidential: "机密",
};

export const HYBRID_MODE_KEY = "jnao_hybrid_expert_mode";
export const USER_ID_KEY = "rag_chat_user_id";
