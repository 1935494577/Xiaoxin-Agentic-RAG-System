import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  BookOpen,
  Brain,
  ClipboardList,
  Coins,
  Cpu,
  Database,
  FileText,
  HardDrive,
  MessageSquare,
  Sparkles,
  ThumbsUp,
  Users,
  Wrench,
  Radio,
} from "lucide-react";
import type { Department } from "./constants";
import { DEPT_OPTIONS } from "./constants";

/** 拥有全部管理功能的部门 */
export const FULL_ACCESS_DEPARTMENT: Department = "技术部";

export const ADMIN_FEATURES = [
  "chat",
  "ingest",
  "processing",
  "vector_store",
  "memory",
  "prompts",
  "models",
  "feedback",
  "eval_reports",
  "trace",
  "token_usage",
  "exam_bank",
  "tutorial",
  "scenarios",
  "channels",
  "users",
] as const;

export type AdminFeature = (typeof ADMIN_FEATURES)[number];

/** 非技术部可使用的管理功能 */
export const STANDARD_DEPARTMENT_FEATURES: ReadonlySet<AdminFeature> = new Set([
  "chat",
  "ingest",
  "prompts",
  "models",
  "tutorial",
  "scenarios",
  "exam_bank",
]);

export type NavGroupId = "daily" | "quality" | "system" | "administration";

export type NavGroup = {
  id: NavGroupId;
  label: string;
  featureIds: AdminFeature[];
};

/** 管理后台侧边栏分组（Chat 单独在「工作区」） */
export const NAV_GROUPS: NavGroup[] = [
  {
    id: "daily",
    label: "日常运营",
    featureIds: ["ingest", "exam_bank", "scenarios", "tutorial"],
  },
  {
    id: "quality",
    label: "质量闭环",
    featureIds: ["feedback", "eval_reports", "trace", "token_usage"],
  },
  {
    id: "system",
    label: "系统配置",
    featureIds: ["memory", "prompts", "models", "processing", "vector_store", "channels"],
  },
  {
    id: "administration",
    label: "系统管理",
    featureIds: ["users"],
  },
];

export type NavItem = {
  id: AdminFeature;
  label: string;
  href: string;
  icon: LucideIcon;
  primary?: boolean;
};

export const ALL_NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "Jnao Chat", href: "/chat", icon: MessageSquare, primary: true },
  { id: "ingest", label: "数据入库", href: "/admin/ingest", icon: Database },
  { id: "exam_bank", label: "题库组卷", href: "/admin/exam-bank", icon: ClipboardList },
  { id: "scenarios", label: "业务场景", href: "/admin/scenarios", icon: Sparkles },
  { id: "processing", label: "工具", href: "/admin/processing", icon: Wrench },
  { id: "vector_store", label: "向量库", href: "/admin/vector-store", icon: HardDrive },
  { id: "memory", label: "对话设置", href: "/admin/memory", icon: Brain },
  { id: "prompts", label: "提示词", href: "/admin/prompts", icon: FileText },
  { id: "models", label: "模型", href: "/admin/models", icon: Cpu },
  { id: "feedback", label: "用户反馈", href: "/admin/feedback", icon: ThumbsUp },
  { id: "eval_reports", label: "评测报告", href: "/admin/eval-reports", icon: BarChart3 },
  { id: "trace", label: "链路 Trace", href: "/admin/trace", icon: Activity },
  { id: "token_usage", label: "Token 用量", href: "/admin/token-usage", icon: Coins },
  { id: "channels", label: "IM 渠道", href: "/admin/channels", icon: Radio },
  { id: "tutorial", label: "教程", href: "/admin/tutorial", icon: BookOpen },
  { id: "users", label: "账号管理", href: "/admin/users", icon: Users },
];

const ADMIN_PATH_FEATURE: Array<{ prefix: string; feature: AdminFeature }> = [
  { prefix: "/admin/ingest", feature: "ingest" },
  { prefix: "/admin/exam-bank", feature: "exam_bank" },
  { prefix: "/admin/processing", feature: "processing" },
  { prefix: "/admin/vector-store", feature: "vector_store" },
  { prefix: "/admin/memory", feature: "memory" },
  { prefix: "/admin/prompts", feature: "prompts" },
  { prefix: "/admin/models", feature: "models" },
  { prefix: "/admin/feedback", feature: "feedback" },
  { prefix: "/admin/eval-reports", feature: "eval_reports" },
  { prefix: "/admin/trace", feature: "trace" },
  { prefix: "/admin/token-usage", feature: "token_usage" },
  { prefix: "/admin/channels", feature: "channels" },
  { prefix: "/admin/tutorial", feature: "tutorial" },
  { prefix: "/admin/scenarios", feature: "scenarios" },
  { prefix: "/admin/users", feature: "users" },
];

function isKnownDepartment(department: string): department is Department {
  return (DEPT_OPTIONS as readonly string[]).includes(department);
}

export function hasFullDepartmentAccess(department: string): boolean {
  return department === FULL_ACCESS_DEPARTMENT;
}

/** 未登录或未选部门时不限制（开发/匿名兼容） */
export function shouldEnforceDepartmentAccess(department: string): boolean {
  return Boolean(department.trim()) && isKnownDepartment(department.trim());
}

/** 登录会话部门优先于服务端 profile，避免登录选「技术部」但 profile 仍是旧部门导致权限丢失。 */
export function resolveEffectiveDepartment(
  authDepartment: string,
  profileDepartment: string,
  isAuthenticated: boolean
): string {
  if (isAuthenticated && authDepartment.trim()) {
    return authDepartment.trim();
  }
  if (profileDepartment.trim()) {
    return profileDepartment.trim();
  }
  return FULL_ACCESS_DEPARTMENT;
}

export function canAccessFeature(department: string, feature: AdminFeature): boolean {
  if (!shouldEnforceDepartmentAccess(department)) return true;
  if (hasFullDepartmentAccess(department)) return true;
  return STANDARD_DEPARTMENT_FEATURES.has(feature);
}

export function resolveAdminFeatureFromPath(pathname: string): AdminFeature | null {
  if (pathname === "/chat" || pathname.startsWith("/chat/")) return "chat";
  if (pathname === "/admin" || pathname === "/admin/") return "ingest";

  for (const { prefix, feature } of ADMIN_PATH_FEATURE) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      return feature;
    }
  }
  return null;
}

export function canAccessAdminPath(department: string, pathname: string): boolean {
  const feature = resolveAdminFeatureFromPath(pathname);
  if (!feature) return true;
  return canAccessFeature(department, feature);
}

export function getVisibleNavItems(department: string): NavItem[] {
  return ALL_NAV_ITEMS.filter((item) => canAccessFeature(department, item.id));
}

export type VisibleNavGroup = NavGroup & { items: NavItem[] };

export function getVisibleNavGroups(department: string): VisibleNavGroup[] {
  const visible = new Set(getVisibleNavItems(department).map((item) => item.id));
  const byId = Object.fromEntries(ALL_NAV_ITEMS.map((item) => [item.id, item])) as Record<
    AdminFeature,
    NavItem
  >;

  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.featureIds.map((id) => byId[id]).filter((item) => item && visible.has(item.id)),
  })).filter((group) => group.items.length > 0);
}

export function getDefaultAdminPath(department: string): string {
  void department;
  return "/admin/ingest";
}
