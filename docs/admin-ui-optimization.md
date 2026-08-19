# 管理后台 UI 优化方案（日常运营 / 质量闭环 / 系统配置 / 系统管理）

> 目标：解决 Admin 页面在宽屏下贴左、卡片/选项框风格不统一、按钮与字体层级混乱、Tabs 拥挤等问题。

## 问题诊断

| 问题 | 根因 |
|------|------|
| 文字/内容偏屏幕左侧 | 各页面 `p-6 max-w-[780~1100px]` 但**无 `mx-auto`**；`AdminLayout` 仅滚动，不居中 |
| 页面宽度 token 混乱 | 780 / 860 / 900 / 960 / 1100 / max-w-4xl / 1680 混用 |
| 卡片风格不统一 | `Card` 有 `shadow-card`，`.admin-panel` 无阴影，列表页混用 `shadow-sm` / `border-2` |
| Tabs 拥挤 | `flex border-b border-border mb-4`，标签贴左无间隙 |
| 按钮/字体层级不统一 | 页面标题 `text-xl sm:text-2xl` 与 `text-lg` 混用；按钮变体分散 |
| 加载/错误态布局跳动 | loading/error 返回无 max-width 容器 |

## 优化方案

### 1. 页面排版与居中

- **统一容器**：`AdminLayout` 的 `<Outlet>` 外包一层  
  `mx-auto w-full max-w-6xl px-6 py-6 space-y-6`
- **宽度统一**：
  - 默认：`max-w-6xl`（1152px）
  - 宽表页（Token/反馈/评测）：`max-w-7xl`
  - 组卷向导：保留 `max-w-[1680px]`
- **页面壳组件**：`AdminPageShell` 包裹 loading / error / 正常态，消除布局跳动

### 2. 卡片与选项框

- 统一内容卡片：`rounded-xl border border-border bg-surface shadow-card`
- `.admin-panel` 补充相同阴影
- 列表行 hover：`transition-colors hover:bg-surface-muted/60`
- 题库/反馈等可点卡片：`hover:border-border/80 hover:bg-surface-muted/40`

### 3. Tabs（标签页）

- 容器：`flex gap-1 border-b border-border mb-5 px-1`
- 活动项：`bg-surface-muted/50 rounded-t-lg border-b-2 border-brand text-brand`
- 非活动项：`text-text-muted hover:text-text`
- 点击区域：`py-2.5`

### 4. 按钮与字体

- 主按钮：`rounded-lg bg-brand text-on-brand shadow-sm hover:shadow-md transition-shadow`
- 卡片内操作：`size="sm"`
- 页面标题：`text-xl font-semibold tracking-tight`
- 卡片标题：`text-sm font-semibold`
- 正文/说明：`text-sm text-text-muted`

### 5. 页面边距与间距

- 页面根间距：`space-y-6`
- 卡片内：`space-y-3`
- 主区域 padding 由 Layout 统一，页面不再各自 `p-6`

### 6. 实施清单

| 步骤 | 文件/改动 | 影响范围 |
|------|----------|----------|
| 1 | `AdminLayout`：Outlet 外包统一容器 | 全部 Admin 页面 |
| 2 | 各页面删除根 `p-6 max-w-*`，保留 `space-y-6` | 入库/提示词/模型/向量库/工具/Token/记忆/用户/评测/反馈/Trace/渠道/题库 |
| 3 | `Tabs.tsx`：加 `gap-1 px-1`，活动 tab 背景 | 工具/模型/对话设置等 |
| 4 | `index.css` `.admin-panel` 加 `shadow-card`；清理 `shadow-sm`/`border-2` | 反馈/评测/渠道/题库 |
| 5 | 新建 `AdminPageShell`，统一 loading/error | 消除布局跳动 |

### 7. 预期效果

- 所有 Admin 页面在宽屏下**居中展示**，不再贴左
- 卡片、选项框、按钮风格统一，有适度阴影与圆角
- Tabs 不再拥挤，阅读与操作区层次分明
- 后续新增页面使用统一壳组件即可，无需重复调样式

## 实施记录

- [x] 方案整理与文档化（docs/admin-ui-optimization.md）
- [x] AdminLayout 统一居中容器：`mx-auto w-full max-w-6xl px-6 py-6 space-y-6`
- [x] 14 个 Admin 页面根容器统一为 `space-y-6`（移除冗余 `p-6 max-w-*`）
- [x] Tabs 组件：gap-1、活动项背景、更大点击区域
- [x] `.admin-panel` 统一 `shadow-card`；Button primary 加 shadow-sm/hover:shadow-md
- [x] 前端测试全绿（46 文件 / 226 用例）

### 第二轮视觉打磨（2026-08-12）

| 组件 | 改进 |
|------|------|
| Sidebar `.app-nav-link` | hover 右移 2px、图标放大变色；active 项图标品牌色 |
| Card / MetricCard / `.admin-panel` | hover 提升 `shadow-raised`，统一阴影层级 |
| Button | `transition-all`、default/secondary 边框 hover、primary/destructive `active:scale-[0.98]` |
| Tabs | 活动项背景 + 底部品牌色下划线动画（居中展开） |
| 页面切换 | `view-fade-in` 0.3s cubic-bezier(0.16, 1, 0.3, 1)，位移 8px |
| EmptyState | 图标 h-12 w-12 + 阴影，更醒目 |

- [x] 第二轮测试：46 文件 / 226 用例全绿

## 验证方式

```powershell
cd D:\11\frontend
npx tsc --noEmit
npm test -- --run
```

重启 `.\scripts\run-dev-harness.ps1` 后访问 Admin 各页面查看效果。