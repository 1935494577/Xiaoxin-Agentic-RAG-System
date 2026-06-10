# Changelog

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
