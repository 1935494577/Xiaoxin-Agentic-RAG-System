# Changelog

## 2026-06-16 — DeerFlow 严格对齐规范

### 文档

- **`docs/deerflow-integration.md`**（新建）— 以 `D:\bytedance flow\deer-flow` 为唯一实现依据；Harness/App 分层、禁止自研清单、DF-0~DF-7 步骤
- **`docs/assistant-fusion-plan.md`** — 重写 Phase B/C 为 DeerFlow 模块对照；移除自研 TurnMiddleware / token store / channel_gateway 方案
- **`docs/目标.md`** — Sprint G 改为 DeerFlow 验收项
- **`README.md`** — 规划行指向 `deerflow-integration.md`

### 说明

- 既有 `routing.py` 扩展为 **knowledge 快路径过渡**，task/auto 主编排须迁移至 `make_lead_agent`
- 代码实现尚未开始 harness 引入；下一步 **DF-0**

---

## 2026-06-16 — Assistant 融合计划：工具 / Skill / Token / 渠道

### 文档

- **`docs/assistant-fusion-plan.md`** — 新增 §0 前后端分工、§2.1 编排北极星；Phase B 拆为 B1 工具层、B2 Skill 层、B3 Token（含 Chat/Admin UI）、B4 澄清/Todo UI；Phase C 渠道补充 Admin 必显字段；§8.1 DeerFlow 能力对照
- **`docs/目标.md`** — 新增 **Sprint G**（对话编排与 Agent 能力）及总验收项
- **`README.md`** — 目录与「规划中（Sprint G）」一行

### 代码（routing，未单独发版）

- `agent/tools/runtime/routing.py` — 行业趋势 / 实时类问题走 `web_search` 路径（如「2025年AI发展」）

---

## 2026-06-10 — 前端性能优化、目录重组、路径修复

### 前端目录重组

- `frontend/` → `frontend/admin/`（Streamlit 管理后台）
- `web/chat/` → `frontend/chat/`（React Chat SPA）
- 去除空 `web/` 目录，所有前端统一收纳在 `frontend/` 下
- 全部启动脚本、Makefile、测试文件、README 中的路径引用已同步更新

### Chat SPA（React + Vite）性能优化

- **`App.tsx`** — 初始化 API 调用并行化：`fetchNav()`、`fetchUiConfig()`、`refreshSessions()` 由串行改为 `Promise.all` 并行发起
- **`App.tsx`** — 消息列表 key 从数组索引 `i` 改为 `message.id || i`，避免列表重排时不必要的 DOM 重建
- **`App.tsx`** — 添加 `useRef` 初始化守卫，消除 `sessionId` 变更触发的重复 `Promise.all` 调用
- **`App.tsx`** — 简化 `displayMessages` 流式显示逻辑，移除冗余内层条件判断
- **`MessageBubble.tsx`** — 使用 `React.memo` 包裹组件，流式输出期间仅最后一条重新渲染
- **`vite.config.ts`** — `manualChunks` 改为函数模式：React → `vendor`，markdown → `markdown`，其余 → `libs`，新增依赖自动分组

### Streamlit 管理后台优化

- **`_bootstrap.py`** — `load_streamlit_common()` 增加 mtime 检测，源文件未变更时直接复用 `sys.modules` 中的缓存模块，避免每次页面导航重新 import
- **`page_init.py`** — `init_app_page()` 改为分两轮：Round 1 并行执行 ui_config、nav、model-profiles 三个 API 调用（`ThreadPoolExecutor`），Round 2 在模型解析后检查连接状态

### 路径 Bug 修复

- **`streamlit_common.py`** — `_api_src_on_path()` 和 `_env_api_base()` 的 `Path.parents[1]` 修正为 `parents[2]`（目录从 `frontend/` 移至 `frontend/admin/` 后深度 +1）
- **`nav_links.py`** — 后端降级导入路径同上修正
- **`tests/test_nav_sync.py`** — Streamlit 页面和 TS 客户端路径引用同步更新
- **`enterprise_rag/src/api/nav_config.py`** — 注释中的路径引用同步更新

### Git 管理

- `.gitignore` 新增 `enterprise_rag/data/raw/*` 排除规则，保留 `.gitkeep` 和 `sample.txt` 例外
- 已跟踪的用户文档（`1-3.txt`、`1-3(1).txt`）从 Git 历史中移除
