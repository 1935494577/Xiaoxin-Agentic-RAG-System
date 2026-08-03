/**
 * UI primitives (Card / Skeleton / EmptyState / Table) — P0 admin skeleton unification.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { Inbox } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../src/components/ui/Card";
import { Skeleton, SkeletonCard } from "../src/components/ui/Skeleton";
import { EmptyState } from "../src/components/ui/EmptyState";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../src/components/ui/Table";

describe("Card", () => {
  it("renders header/title/description/content", () => {
    render(
      React.createElement(
        Card,
        null,
        React.createElement(
          CardHeader,
          null,
          React.createElement(CardTitle, null, "标题"),
          React.createElement(CardDescription, null, "说明文字")
        ),
        React.createElement(CardContent, null, "正文内容")
      )
    );
    expect(screen.getByText("标题")).toBeTruthy();
    expect(screen.getByText("说明文字")).toBeTruthy();
    expect(screen.getByText("正文内容")).toBeTruthy();
  });

  it("applies surface card styling", () => {
    const { container } = render(React.createElement(Card, null, "x"));
    const el = container.firstElementChild as HTMLElement;
    expect(el.className).toContain("rounded-xl");
    expect(el.className).toContain("border");
    expect(el.className).toContain("bg-surface");
  });

  it("merges custom className", () => {
    const { container } = render(React.createElement(Card, { className: "p-9" }, "x"));
    expect((container.firstElementChild as HTMLElement).className).toContain("p-9");
  });
});

describe("Skeleton", () => {
  it("renders pulse block with aria-hidden", () => {
    const { container } = render(React.createElement(Skeleton, { className: "h-4 w-24" }));
    const el = container.firstElementChild as HTMLElement;
    expect(el.className).toContain("animate-pulse");
    expect(el.getAttribute("aria-hidden")).toBe("true");
  });

  it("SkeletonCard renders requested number of rows", () => {
    const { container } = render(React.createElement(SkeletonCard, { rows: 4 }));
    const rows = container.querySelectorAll("[aria-hidden='true']");
    expect(rows.length).toBeGreaterThanOrEqual(4);
  });
});

describe("EmptyState", () => {
  it("renders icon, title and description", () => {
    render(
      React.createElement(EmptyState, {
        icon: Inbox,
        title: "暂无数据",
        description: "入库后在这里查看",
      })
    );
    expect(screen.getByText("暂无数据")).toBeTruthy();
    expect(screen.getByText("入库后在这里查看")).toBeTruthy();
  });

  it("renders optional action and triggers callback", async () => {
    const onClick = vi.fn();
    render(
      React.createElement(EmptyState, {
        icon: Inbox,
        title: "暂无数据",
        actionLabel: "去入库",
        onAction: onClick,
      })
    );
    await userEvent.click(screen.getByText("去入库"));
    expect(onClick).toHaveBeenCalled();
  });
});

describe("Table", () => {
  it("renders semantic table structure", () => {
    render(
      React.createElement(
        Table,
        null,
        React.createElement(
          TableHeader,
          null,
          React.createElement(
            TableRow,
            null,
            React.createElement(TableHead, null, "名称"),
            React.createElement(TableHead, null, "状态")
          )
        ),
        React.createElement(
          TableBody,
          null,
          React.createElement(
            TableRow,
            null,
            React.createElement(TableCell, null, "文档A"),
            React.createElement(TableCell, null, "已入库")
          )
        )
      )
    );
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "名称" })).toBeTruthy();
    expect(screen.getByRole("cell", { name: "已入库" })).toBeTruthy();
  });

  it("wraps table in horizontal scroll container", () => {
    const { container } = render(React.createElement(Table, null));
    const wrap = container.firstElementChild as HTMLElement;
    expect(wrap.className).toContain("overflow-x-auto");
  });
});
