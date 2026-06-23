import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom/vitest";
import React from "react";

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    userId: "u_test",
    username: "tech1",
    department: "技术部",
    logout: vi.fn(),
  }),
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

vi.mock("../src/api/client", () => ({
  authChangePassword: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { SidebarUserProfile } from "../src/components/layout/SidebarUserProfile";

function renderProfile() {
  return render(
    <MemoryRouter>
      <SidebarUserProfile />
    </MemoryRouter>
  );
}

describe("SidebarUserProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSave.mockResolvedValue({
      user_id: "u_test",
      display_name: "新名字",
      avatar_url: "",
      department: "技术部",
    });
  });

  it("shows display name in sidebar footer", () => {
    renderProfile();
    expect(screen.getByText("风停看雨画")).toBeTruthy();
  });

  it("opens settings dialog and saves profile without department picker", async () => {
    renderProfile();
    fireEvent.click(screen.getByText("风停看雨画"));
    expect(screen.getByText("用户设置")).toBeTruthy();
    expect(screen.getByText("技术部")).toBeTruthy();
    expect(screen.queryByLabelText("部门权限")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("昵称"), { target: { value: "新名字" } });
    fireEvent.click(screen.getByText("保存"));

    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: "新名字",
        })
      );
    });
  });
});
