---
name: Jnao 劲脑 · Enterprise RAG
description: 脑科教育内部知识库与对话平台 — 可信蓝 + 暖色入口
colors:
  brand-primary: "#1565c0"
  brand-primary-dark: "#0d47a1"
  brand-primary-light: "#e8f2fc"
  accent-gold: "#f5b800"
  auth-coral: "#ff8a65"
  surface-default: "#ffffff"
  surface-muted: "#f4f6f9"
  surface-warm: "#faf8f5"
  surface-warm-deep: "#f3f0ea"
  ink-default: "#1a1d21"
  ink-muted: "#5f6b7a"
  border-default: "#e4e8ef"
  border-warm: "#ebe6df"
  error: "#c62828"
  error-bg: "#ffebee"
  success: "#2e7d32"
  success-bg: "#e8f5e9"
  warning: "#e65100"
  warning-bg: "#fff3e0"
typography:
  display:
    fontFamily: "Outfit, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "clamp(3rem, 12vw, 9.5rem)"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "{typography.body.fontFamily}"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "0.375rem"
  md: "0.75rem"
  lg: "0.75rem"
  full: "9999px"
spacing:
  sidebar-width: "240px"
  page-padding: "24px"
  nav-item-y: "8px"
components:
  button-primary:
    backgroundColor: "{colors.brand-primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.brand-primary-dark}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  nav-item-active:
    backgroundColor: "{colors.brand-primary-light}"
    textColor: "{colors.brand-primary}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
  input-default:
    backgroundColor: "{colors.surface-default}"
    textColor: "{colors.ink-default}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
---

# Design System: Jnao 劲脑 · Enterprise RAG

## Overview

**Creative North Star: "Warm Precision"**

对内知识工具的视觉语言：Admin 与 Chat 以 **清晰、可扫描、低密度装饰** 为主；Welcome/Login 允许 **暖色与玻璃质感** 作为品牌入口，但不污染工作区。整体拒绝 generic AI slop，采用已提交的 token（`frontend/src/index.css`）而非临时硬编码。

**Key Characteristics:**

- 主色 **可信蓝** `#1565c0` 贯穿链接、主按钮、Sidebar 激活态
- **暖灰表面**（`surface-warm`）仅用于认证入口背景
- **240px 固定 Sidebar** + 内容区滚动；Chat 与 Admin 共用 AppShell 家族
- shadcn 语义变量（`--primary`, `--radius`）与 Tailwind `@theme` 并存，新组件优先引用 token
- 玻璃按钮（`.glass-button`）**仅**用于 Welcome CTA，不用于 Admin 表单

## Colors

### Primary

- **Trusted Blue** (`#1565c0`): 主操作、品牌字标、链接、focus ring、流式光标
- **Deep Blue** (`#0d47a1`): hover / 强调深色态
- **Blue Mist** (`#e8f2fc`): Sidebar 激活背景、轻量强调底

### Secondary

- **Training Gold** (`#f5b800`): 图表 accent、次要强调（chart-2），少量使用

### Tertiary

- **Auth Coral** (`#ff8a65`): Welcome 标题首字母「J」与暖光晕，**不**用于 Admin 主色

### Neutral

- **Ink** (`#1a1d21`): 正文与标题
- **Ink Muted** (`#5f6b7a`): 次要说明；在彩色底上需加深以满足对比度
- **Surface / Muted** (`#ffffff` / `#f4f6f9`): 页面与卡片背景
- **Warm Surface** (`#faf8f5`, `#f3f0ea`): 认证页背景与渐变层
- **Border** (`#e4e8ef`, `#ebe6df`): 分割线与输入框描边

### Named Rules

**The One Accent Rule.** 工作区内屏幕级 accent 以 brand blue 为主；gold 与 coral 不在同一 Admin 视图并列抢戏。

**The Status Trio Rule.** 成功/警告/错误使用 `--color-success|warning|error` 及对应 `-bg`，不单靠颜色区分。

## Typography

**Display Font:** Outfit（Google Fonts，已 link 于 `frontend/index.html`）  
**Body Font:** 系统栈 + PingFang SC / Microsoft YaHei（`index.css` body）  
**Character:** 中文可读性优先；Display 用于 Welcome 大标题，产品内以 14–16px 工具字号为主。

### Hierarchy

- **Display** (600, clamp 3rem–9.5rem, lh 1): Welcome「Jnao」品牌字标
- **Title** (600, text-base–lg): Sidebar 品牌、区块标题
- **Body** (400, 16px, lh 1.5): 表单、Chat 回答、Admin 正文；段落建议 ≤75ch
- **Label** (500, 14px): 表单标签、导航项

### Named Rules

**The Outfit Gate Rule.** Outfit 用于营销型 display；Admin 列表与表格不强制 Outfit，保持系统字体以减少加载与渲染差异。

## Elevation

产品区以 **扁平 + 边框分割** 为主（Sidebar `border-r`, 卡片 `border`）。深度通过 surface 层级（default / muted / warm）表达，而非重阴影。

### Shadow Vocabulary

- **Glass button stack**（`.glass-button`）: inset highlight + 轻外阴影 + `backdrop-filter: blur(10px)` — **仅认证 CTA**
- **Auth warm glow**: 径向渐变光晕（CSS 伪元素），非 box-shadow

**The Flat Admin Rule.** Admin 卡片默认无 float shadow；hover 用背景色变化（`bg-brand-light`）而非抬起阴影。

## Components

**Character:** 实用组件 + 少量 shadcn 原语；入口页单独一套 glass CTA。

### Button

- **Primary** (`Button`, shadcn): `{colors.brand-primary}` 填充，白字，`rounded-md`
- **Glass** (`GlassButton`): 全圆角 pill，blur 玻璃；仅 Welcome「登录」等入口场景
- **Ghost / link**: 登录页返回、次要操作

### Input & Form

- `Input`, `Select`, `Label`: 边框 `{colors.border-default}`，`rounded-md`，focus ring `{colors.brand-primary}`
- 错误态配合 toast（sonner）与 inline 文案

### Navigation

- **Sidebar** (240px): `surface-muted` 底，NavLink 激活 `bg-brand-light text-brand font-semibold`
- **AuthEntryLayout**: 全屏居中，暖色背景层 + 可选浮动装饰

### Chat

- 用户/助手消息分区；`.markdown-body` 排版；流式 `.stream-cursor` 品牌色光标
- 工具栏：人设、新话题、混合专家 — 信息密度中等

### Admin Shell

- `AdminLayout` + 与 Sidebar 一致的 nav id（ingest, processing, vector_store, …）
- 表格与表单页：白底内容区，padding 一致，避免嵌套 card-in-card

## Do's and Don'ts

**Do**

- 新页面从 `index.css` `@theme` 与 `:root` 变量取色
- Admin 新功能对齐 `departmentAccess.ts` 与 Sidebar nav id
- 认证页动效提供 `prefers-reduced-motion` 降级路径
- 保持中文 UI 与足够 contrast 的 muted 文本

**Don't**

- 在 Admin 表单或数据表上使用 glass-button
- 引入第二套互斥主色（如全页 purple gradient）
- 假 dashboard 截图或 div 拼的「产品预览」
- 忽视部门 403 / AccessDenied 的空态与文案
- 在 token 已存在时硬编码 `#1565c0` 的新副本（应复用 `--color-brand` / `text-brand`）
