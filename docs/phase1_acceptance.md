# 阶段 1 总验收

> 对应 [`docs/目标.md`](./目标.md) **阶段 1 总验收** 与 **6.4 发布节奏**。  
> Sprint A–F 代码完成后，按本清单逐项勾选再对内推广。

---

## 1. 功能验收（可自动化）

| 项 | 标准 | 验证方式 | 状态 |
|----|------|----------|------|
| 负反馈 → Triage | 点 👎 后运营可规则/LLM 研判，Inbox 见分类 | `pytest tests/test_phase1_acceptance.py::test_negative_feedback_visible_after_triage -q` | 自动化 |
| Golden + 评测 | 采纳后可进 golden、异步评测有报告 | `pytest tests/test_feedback_api_d.py -q` | 已有 |
| Feedback 故障隔离 | Feedback 存储失败时 `/health`、`/chat/sessions` 仍可用 | `pytest tests/test_phase1_acceptance.py::test_chat_unaffected_when_feedback_store_fails -q` | 自动化 |
| 租户 / Admin 鉴权 | E/F Sprint | `pytest tests/test_tenant_*.py tests/test_admin_*.py -q` | 已有 |
| 前端登录守卫 | 退出后须重新登录 | `npm test -- RequireAuth`（frontend） | 已有 |

```powershell
# 仓库根目录
.\scripts\phase1_verify.ps1
```

---

## 2. 运营验收（需人工 / 定时）

| 项 | 标准 | 建议 |
|----|------|------|
| 24h Triage SLA | 用户 👎 后 **24h 内** Admin Inbox 可见分类 | 每日打开 `/admin/feedback`；或 Windows 计划任务调用 `POST /admin/feedback/triage`（`use_llm=false` 规则研判） |
| 30+ 有效反馈 | 内部试用 4 周累计 | 导出 JSONL 统计 `rating=0` 且已 triaged 条数 |
| Inbox 积压 | 无长期 pending | 每 2 周回顾 severity 排序列表 |

**规则 Triage（无需 LLM Key）：**

```http
POST /admin/feedback/triage
Content-Type: application/json
X-Admin-Role: operator

{"limit": 30, "use_llm": false, "rating": 0}
```

---

## 3. 非功能验收（需采样）

| 项 | 标准 | 做法 |
|----|------|------|
| `/chat/stream` P95 | 相对阶段 0 增加 **< 5%** | 对比启用 Feedback Loop 前后同一问题集；记录 TTFB / 首 token（LangSmith 或浏览器 Network） |
| API 常驻内存 | 增加 **< 100MB**（不含模型） | 任务管理器 / `ps` 对比 feedback 模块加载前后 RSS；勿在含嵌入模型的进程上单独算 |
| 索引性能 | 向量/BM25 P95 不明显退化 | `python scripts/bench_index_perf.py`（改检索相关配置后） |

> 若无阶段 0 基线数字，先记录当前值为 **baseline-2026-06**，后续变更与此对比。

---

## 4. 生产与安全清单

见 [`deploy_security.md`](./deploy_security.md) 第 8 节，并确认：

- [ ] `RAG_API_SECRET`（Chat / 通用 API）
- [ ] `RAG_ADMIN_API_SECRET`（管理端 API，可选但与 Chat 分离）
- [ ] 前端 RequireAuth + 部门门控（技术部全功能）
- [ ] `CORS_ALLOW_ORIGINS` 收窄
- [ ] 生产 `DISABLE_OPENAPI_DOCS=true`

---

## 5. 阶段 1 完成定义

**全部满足后**，在 `docs/目标.md` 将「阶段 1 总验收」勾选，并进入 **≥ 4 周内部稳定期**，再规划阶段 2。

- [x] Sprint A–F 代码与测试
- [ ] 本节 2 运营项跑满 1 周无阻塞
- [ ] 本节 3 非功能有 baseline 记录
- [ ] 本节 4 生产清单（若已上预发/生产）

---

## 6. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-06-16 | 初版：阶段 1 总验收清单 + phase1_verify 脚本 |
