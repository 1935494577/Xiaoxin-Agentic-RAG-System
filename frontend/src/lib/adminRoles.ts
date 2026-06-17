import { FULL_ACCESS_DEPARTMENT } from "./departmentAccess";

export type AdminRole = "viewer" | "operator" | "admin";

export function resolveAdminRole(department: string): AdminRole {
  const dept = department.trim();
  if (dept === FULL_ACCESS_DEPARTMENT) return "admin";
  if (dept) return "operator";
  return "admin";
}

export function roleAllows(actual: AdminRole, required: AdminRole): boolean {
  const rank: Record<AdminRole, number> = { viewer: 0, operator: 1, admin: 2 };
  return rank[actual] >= rank[required];
}

export function canPerformAdminAction(
  role: AdminRole,
  action: "read" | "triage" | "config"
): boolean {
  if (action === "read") return roleAllows(role, "viewer");
  if (action === "triage") return roleAllows(role, "operator");
  return roleAllows(role, "admin");
}
