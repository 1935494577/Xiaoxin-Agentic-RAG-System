/**
 * MetricCard — P1 标准化：可选 icon、variant 着色。
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { Coins } from "lucide-react";
import { MetricCard } from "../src/components/admin/MetricCard";

describe("MetricCard", () => {
  it("renders label and value", () => {
    render(React.createElement(MetricCard, { label: "今日调用", value: "128" }));
    expect(screen.getByText("今日调用")).toBeTruthy();
    expect(screen.getByText("128")).toBeTruthy();
  });

  it("applies success variant styles", () => {
    render(
      React.createElement(MetricCard, { label: "状态", value: "已启用", variant: "success" })
    );
    expect(screen.getByText("已启用").className).toContain("text-success");
  });

  it("renders optional icon next to label", () => {
    render(React.createElement(MetricCard, { label: "Token", value: "1.2k", icon: Coins }));
    const label = screen.getByText("Token");
    expect(label.parentElement?.querySelector("svg")).toBeTruthy();
  });
});
