/**
 * ThemeToggle — P2 深色模式切换按钮。
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { ThemeToggle } from "../src/components/ui/ThemeToggle";
import { THEME_STORAGE_KEY } from "../src/hooks/useTheme";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("renders with switch-to-dark label in light mode", () => {
    render(React.createElement(ThemeToggle));
    expect(screen.getByRole("button", { name: "切换到深色模式" })).toBeTruthy();
  });

  it("click toggles dark class and aria label", () => {
    render(React.createElement(ThemeToggle));
    fireEvent.click(screen.getByRole("button", { name: "切换到深色模式" }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(screen.getByRole("button", { name: "切换到浅色模式" })).toBeTruthy();
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });
});
