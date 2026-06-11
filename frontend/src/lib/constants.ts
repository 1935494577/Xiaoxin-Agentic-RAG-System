export const DEPT_OPTIONS = ["技术部", "运营部", "媒体部", "剪辑部"] as const;
export type Department = (typeof DEPT_OPTIONS)[number];

export const DEPT_LABELS: Record<Department, string> = {
  "技术部": "技术部",
  "运营部": "运营部",
  "媒体部": "媒体部",
  "剪辑部": "剪辑部",
};

/** Ingest/chat: internal + public only; confidential reserved for future use. */
export const PERM_OPTIONS = ["public", "internal"] as const;
export type Permission = (typeof PERM_OPTIONS)[number];

export const PERM_LABELS: Record<Permission, string> = {
  public: "公开",
  internal: "内部",
};

export const HYBRID_MODE_KEY = "jnao_hybrid_expert_mode";
export const USER_ID_KEY = "rag_chat_user_id";
export const USER_DEPT_KEY = "rag_chat_user_department";
