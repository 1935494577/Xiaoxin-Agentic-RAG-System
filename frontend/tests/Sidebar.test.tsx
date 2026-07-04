import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "../src/components/layout/Sidebar";
import { getVisibleNavGroups } from "../src/lib/departmentAccess";

vi.mock("../src/context/UserProfileContext", () => ({
  useUserProfile: () => ({
    loading: false,
    displayName: "测试用户",
    avatarUrl: "",
    aiDisplayName: "",
    aiAvatarUrl: "",
    department: "运营部",
    saveProfile: vi.fn(),
  }),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    department: "运营部",
    username: "测试用户",
    role: "operator",
    logout: vi.fn(),
  }),
}));

vi.mock("../src/components/layout/SidebarUserProfile", () => ({
  SidebarUserProfile: () => <div data-testid="sidebar-profile">profile</div>,
}));

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows only department-allowed admin nav for 运营部", () => {
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("Jnao Chat")).toBeInTheDocument();
    expect(screen.getByText("数据入库")).toBeInTheDocument();
    expect(screen.getByText("提示词")).toBeInTheDocument();
    expect(screen.getByText("模型")).toBeInTheDocument();

    expect(screen.queryByText("向量库")).not.toBeInTheDocument();
    expect(screen.queryByText("用户反馈")).not.toBeInTheDocument();
  });

  it("renders grouped nav sections", () => {
    render(
      <MemoryRouter initialEntries={["/admin/ingest"]}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("工作区")).toBeInTheDocument();
    expect(screen.getByText("日常运营")).toBeInTheDocument();
    expect(screen.getByText("系统配置")).toBeInTheDocument();
    expect(screen.queryByText("质量闭环")).not.toBeInTheDocument();
    expect(screen.getByText("管理后台")).toBeInTheDocument();
  });

  it("getVisibleNavGroups returns quality loop and admin for 技术部", () => {
    const groups = getVisibleNavGroups("技术部");
    const labels = groups.map((g) => g.label);
    expect(labels).toContain("日常运营");
    expect(labels).toContain("质量闭环");
    expect(labels).toContain("系统配置");
    expect(labels).toContain("系统管理");
  });
});
