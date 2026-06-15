/**
 * WelcomePage — intro before login.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import "@testing-library/jest-dom/vitest";
import WelcomePage from "../src/pages/WelcomePage";

function renderWelcome() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("WelcomePage", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders Jnao title with 劲脑", () => {
    renderWelcome();
    expect(screen.getByText("J")).toBeInTheDocument();
    expect(screen.getByText("nao")).toBeInTheDocument();
    expect(screen.getByText("劲脑")).toBeInTheDocument();
  });

  it("shows login button after stream reveal animation", async () => {
    renderWelcome();
    expect(screen.queryByRole("button", { name: /登录/ })).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(2700);
    });

    const btn = screen.getByRole("button", { name: /登录/ });
    expect(btn).toBeVisible();
  });

  it("navigates to login when button clicked", async () => {
    renderWelcome();

    await act(async () => {
      vi.advanceTimersByTime(2700);
    });

    fireEvent.click(screen.getByRole("button", { name: /登录/ }));

    await act(async () => {
      vi.advanceTimersByTime(700);
    });

    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });
});
