# 优化清单 — 执行状态（2026-07-31）

> **结论**：P0 与 P1（除可选大页拆分）已落地；P2 **上线前项**（实际迁 PG、Prometheus）按设计延期；本地开发继续 SQLite + `DATABASE_URL` 为空。

## 总览

| 优先级 | 范围 | 状态 |
|--------|------|------|
| **P0** | 会话/消息/临时文档/Chat 执行绑定登录身份 | ✅ 完成 |
| **P0** | 租户由服务端 `auth.tenant_id` 决定，禁止信任 `X-Tenant-ID` | ✅ 完成 |
| **P0** | 题库 API 移除客户端 `tenant_id` / `owner_user_id` / `reader_user_id` 控制 | ✅ 完成 |
| **P1** | 前端 build/lint 基线 + GitHub Actions CI | ✅ 完成 |
| **P1** | 拆分 `api/main.py`、`ChatPage.tsx` | ✅ 完成 |
| **P1** | 拆分 `ExamBankAssemblePage.tsx` | ⏸️ 可选延后（~1440 行，无线上压力） |
| **P1** | DeerFlow 主链 vs KB 快路径收敛 | ✅ 完成 |
| **P2** | 身份/会话/ACL **实际**迁 PostgreSQL | ⏸️ **上线前再做**（见 [`data-platform.md`](./data-platform.md) S4–S6） |
| **P2** | PG 连接骨架 + `/health` persistence | ✅ 完成 |
| **P2** | 架构文档 + e2e smoke | ✅ 完成 |
| **P2** | Prometheus / 生产观测 | ⏸️ **上线前再做** |

---

## P0 — 身份与租户边界 ✅

| 项 | 说明 |
|---|---|
| Chat 会话 / 流式 / 临时文档 | `api/chat_identity.py`；前端不再传 `user_id` |
| 租户 | `tenant/context.py` ← `auth.tenant_id` |
| 题库 tenant / ACL | `exam_router._exam_tenant_id`、`_exam_actor_user_id` |
| Chat 答题身份 | attempt / explain 仅服务端用户 |

回归：`tests/test_exam_tenant_authorization.py`、`tests/test_tenant_context.py`、`tests/test_exam_chat_security.py`

## P1 — 工程与结构

| 项 | 说明 |
|---|---|
| 前端 build | `npm run build` 通过 |
| CI | `.github/workflows/ci.yml` |
| Chat 路由拆分 | `api/chat_router.py` + `chat_service.py` + `chat_identity.py` + `upload_utils.py` |
| Chat 流式拆分 | `frontend/src/hooks/useChatTurn.ts` |
| DeerFlow 收敛 | `jnao_harness/availability.resolve_chat_pipeline` + `CHAT_LEAD_AGENT_ENABLED` |
| 题库 Admin 大页 | ⏸️ 可选 |

## P2 — 数据平台与观测

| 项 | 说明 |
|---|---|
| `persistence/database.py` | `uses_postgres()` / `persistence_status()`；**业务 store 仍 SQLite** |
| 实际迁 PG | ⏸️ 见 [`data-platform.md`](./data-platform.md) |
| e2e smoke | `tests/e2e/test_api_smoke.py` |
| Prometheus | ⏸️ 生产部署时补 |

### PostgreSQL 何时才需要？

**当前：保持 `DATABASE_URL` 为空。** 触发条件：正式/预发 RDS、多实例共享会话、正式备份运维。

迁库顺序：auth + chat_sessions → exam 元数据 → feedback（Token 用量可仍 SQLite）

## 相关配置

```env
DATABASE_URL=                    # 空=SQLite
CHAT_LEAD_AGENT_ENABLED=true     # task/auto→DeerFlow；knowledge→KB 快路径
RETRIEVAL_MODE_ROUTER_ENABLED=true
```

## 本地验证

```powershell
cd frontend; npm run build
cd ..; $env:PYTHONPATH="enterprise_rag/src"; python -m pytest tests/test_exam_tenant_authorization.py tests/test_tenant_context.py tests/test_chat_pipeline_routing.py tests/test_persistence_database.py tests/e2e/test_api_smoke.py -q
```
