# Product

## Register

product

## Users

劲脑脑科教育内部员工：一线老师、教研与运营、技术管理员。使用场景包括：在 **Jnao Chat** 中检索制度与长文档、获取带引文的回答；在 **管理后台** 中入库文档、配置模型/提示词/向量库、处理用户反馈与评测。用户按部门（技术部、运营部、媒体部、剪辑部）登录，权限影响可见功能与文档 ACL。

## Product Purpose

Enterprise RAG 内部知识平台：将企业制度与长文档清洗、分块、向量化后，通过混合检索与大模型生成可校验、可引用的回答。成功标准：员工能快速找到准确答案；管理员能安全入库与配置；部门权限与文档可见范围在 UI 与检索层一致生效。

## Brand Personality

**可信 · 清晰 · 温厚**

对内工具的专业感优先于营销炫技。语气直接、克制，避免「AI 产品」的浮夸话术。欢迎/登录入口可略具品牌温度（劲脑、脑科训练），进入 Chat 与 Admin 后以任务与信息层级为主。

## Anti-references

- 通用 AI 落地页：紫/青渐变、暗色 mesh hero、三列等宽 feature card
- 全盘 glassmorphism 或 neon glow（仅限入口 CTA，不可蔓延到 Admin）
- 信息密度过低的「空壳 dashboard」或装饰性假数据截图
- 与部门权限模型不一致的「全员可见一切」交互暗示
- 纯英文 UI 或忽视中文排版（PingFang / 微软雅黑可读性）

## Design Principles

1. **任务优先**：Admin 与 Chat 以完成工作流为第一目标；装饰服务于识别与反馈，不抢注意力。
2. **权限可见**：部门与功能边界在导航、403 页、入库/检索结果中可感知，不隐藏 ACL 逻辑。
3. **入口一处，工具一处**：Welcome/Login 承担品牌与信任；进入产品后统一 AppShell / Sidebar 语言。
4. **引文与答案同等重要**：检索结果、来源预览、流式回答的层级应支持「核实再采纳」。
5. **渐进增强动效**：入口页可有 reveal；产品内动效限于状态反馈（加载、提交、切换），尊重 `prefers-reduced-motion`。

## Accessibility & Inclusion

- 目标 **WCAG 2.1 AA**（正文对比度 ≥4.5:1，大文本 ≥3:1）
- 键盘可达：表单、Sidebar 导航、Chat 输入与主要操作具备可见 focus
- 支持 **prefers-reduced-motion**：Welcome 序列动画与 glass 效果需提供静态或可跳过路径
- 中文为主界面语言；数字与表格在 Admin 区使用 tabular-nums  where 适用
- 不依赖单一颜色传达状态（成功/错误/警告配合文案与图标）
