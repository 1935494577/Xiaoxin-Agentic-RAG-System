# 开发进度

> 自主开发循环状态追踪。最后更新：2026-06-16

## 当前阶段

**阶段 1 — 开发完成，运营验收暂停**

> 代码与自动化测试已就绪；需人工/采样的项 **暂不执行**，不影响本地开发使用。

## 已完成

- [x] Sprint A–F（反馈闭环、租户、Admin 鉴权）
- [x] 登录守卫 + 技术部权限同步
- [x] Feedback 故障隔离 + 阶段 1 自动化测试
- [x] 文档：`docs/phase1_acceptance.md`、`deploy_security.md`、`README.md`
- [x] 小功能（无真实密码）：反馈统计面板、对话导出 Markdown、来源预览、侧边栏退出、批量入库、Triage 定时脚本

## 暂停（待你有空再做）

- [ ] 运营：24h Triage 定时任务、30 条有效反馈、4 周内部试用
- [ ] 非功能：P95 延迟 / 内存 baseline 采样
- [ ] 生产：`RAG_API_SECRET` / `RAG_ADMIN_API_SECRET` 等部署清单

详见 [`docs/phase1_acceptance.md`](docs/phase1_acceptance.md) — 需要时按清单逐项勾选即可。

## 现在可以直接用的

- 本地开发：`.\scripts\run-dev.ps1` → Chat `8502` / API `8010`
- 管理后台：登录后按部门使用（技术部全功能）
- 反馈 Inbox / 评测 / 入库 / 对话 — 功能均已实现

## 验证命令（随时可跑）

```powershell
.\scripts\phase1_verify.ps1
```

## 阶段 2

多租户 SaaS — **不启动**，等阶段 1 运营验收完成后再说。
