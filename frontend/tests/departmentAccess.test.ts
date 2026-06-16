/**
 * Department-based admin feature access.
 */
import { describe, it, expect } from "vitest";
import {
  FULL_ACCESS_DEPARTMENT,
  canAccessAdminPath,
  canAccessFeature,
  getDefaultAdminPath,
  getVisibleNavItems,
  resolveAdminFeatureFromPath,
} from "../src/lib/departmentAccess";

describe("departmentAccess", () => {
  it("技术部 has full access", () => {
    expect(canAccessFeature("技术部", "vector_store")).toBe(true);
    expect(canAccessFeature("技术部", "feedback")).toBe(true);
    expect(canAccessAdminPath("技术部", "/admin/trace")).toBe(true);
  });

  it("非技术部 only gets chat, ingest, prompts, models", () => {
    for (const dept of ["运营部", "媒体部", "剪辑部"]) {
      expect(canAccessFeature(dept, "chat")).toBe(true);
      expect(canAccessFeature(dept, "ingest")).toBe(true);
      expect(canAccessFeature(dept, "prompts")).toBe(true);
      expect(canAccessFeature(dept, "models")).toBe(true);

      expect(canAccessFeature(dept, "processing")).toBe(false);
      expect(canAccessFeature(dept, "vector_store")).toBe(false);
      expect(canAccessFeature(dept, "memory")).toBe(false);
      expect(canAccessFeature(dept, "feedback")).toBe(false);
      expect(canAccessFeature(dept, "trace")).toBe(false);
      expect(canAccessFeature(dept, "tutorial")).toBe(false);

      expect(canAccessAdminPath(dept, "/admin/ingest")).toBe(true);
      expect(canAccessAdminPath(dept, "/admin/prompts")).toBe(true);
      expect(canAccessAdminPath(dept, "/admin/models")).toBe(true);
      expect(canAccessAdminPath(dept, "/admin/processing")).toBe(false);
      expect(canAccessAdminPath(dept, "/admin/memory")).toBe(false);
    }
  });

  it("empty department does not restrict (dev / anonymous)", () => {
    expect(canAccessFeature("", "feedback")).toBe(true);
    expect(canAccessAdminPath("", "/admin/trace")).toBe(true);
  });

  it("maps admin paths to features", () => {
    expect(resolveAdminFeatureFromPath("/admin")).toBe("ingest");
    expect(resolveAdminFeatureFromPath("/admin/ingest")).toBe("ingest");
    expect(resolveAdminFeatureFromPath("/admin/eval-reports")).toBe("eval_reports");
    expect(resolveAdminFeatureFromPath("/chat")).toBe("chat");
  });

  it("filters sidebar nav for 运营部", () => {
    const ids = getVisibleNavItems("运营部").map((item) => item.id);
    expect(ids).toEqual(["chat", "ingest", "prompts", "models"]);
  });

  it("shows all nav items for 技术部", () => {
    const techIds = getVisibleNavItems("技术部").map((item) => item.id);
    const allIds = getVisibleNavItems("").map((item) => item.id);
    expect(techIds.length).toBe(allIds.length);
  });

  it("default admin path for restricted dept is ingest", () => {
    expect(getDefaultAdminPath("运营部")).toBe("/admin/ingest");
    expect(getDefaultAdminPath(FULL_ACCESS_DEPARTMENT)).toBe("/admin/ingest");
  });
});
