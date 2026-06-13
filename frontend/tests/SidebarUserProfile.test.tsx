import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({ userId: "u_test" }),
}));

const mockSave = vi.fn();
vi.mock("../src/context/UserProfileContext", () => ({
  useUserProfile: () => ({
    profile: {
      user_id: "u_test",
      display_name: "风停看雨画",
      avatar_url: "",
      department: "技术部",
      ai_display_name: "",
      ai_avatar_url: "",
    },
    loading: false,
    department: "技术部",
    displayName: "风停看雨画",
    avatarUrl: "",
    aiDisplayName: "",
    aiAvatarUrl: "",
    saveProfile: mockSave,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { SidebarUserProfile } from "../src/components/layout/SidebarUserProfile";

describe("SidebarUserProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSave.mockResolvedValue({
      user_id: "u_test",
      display_name: "新名字",
      avatar_url: "",
      department: "运营部",
    });
  });

  it("shows display name in sidebar footer", () => {
    render(<SidebarUserProfile />);
    expect(screen.getByText("风停看雨画")).toBeTruthy();
  });

  it("opens settings dialog and saves profile", async () => {
    render(<SidebarUserProfile />);
    fireEvent.click(screen.getByText("风停看雨画"));
    expect(screen.getByText("用户设置")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "新名字" } });
    fireEvent.change(screen.getByLabelText("部门权限"), { target: { value: "运营部" } });
    fireEvent.click(screen.getByText("保存"));

    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: "新名字",
          department: "运营部",
        })
      );
    });
  });
});
