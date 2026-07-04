/** 管理后台各页「怎么用」文案 — 面向运营/开发，言简意赅 */

export type HelpStep = { title: string; detail: string };

export const PROMPT_PAGE_HELP = {
  summary:
    "控制 AI 的「说话方式」：先选业务角色，再按层级微调文案。下方预览的是实际注入模型的 System Prompt，保存后立即生效。",
  steps: [
    {
      title: "选角色",
      detail: "点「劲脑知识顾问」等预设，自动填入人设层；可再改文案。",
    },
    {
      title: "选预览类型",
      detail: "「知识库回答」= 命中资料时的风格；「通用回答」= 未走 KB 或混合兜底时的风格。",
    },
    {
      title: "改分层文案",
      detail: "每层可单独开关。知识库任务分「完整 / 快速」两版，对应对话设置里的快速流式检索。",
    },
    {
      title: "保存",
      detail: "点「保存全部」写入服务端；「恢复内置默认」会重置为出厂配置。",
    },
  ] satisfies HelpStep[],
  tips: [
    "日常一线 KB 只需改「角色人设」和「输出格式」，不必动任务层。",
    "思考方式（直接 / ReAct）在「对话设置 → 业务场景预设」里配置，纯 KB 默认「直接回答」。",
  ],
};

export const FEEDBACK_PAGE_HELP = {
  summary:
    "用户在 Chat 点 👍/👎 或填写纠错后，记录会进入此收件箱。你的工作是：研判 → 采纳或驳回 → 系统自动改进并可选加入评测集。",
  steps: [
    {
      title: "收集",
      detail: "Chat 每条回答下方可点赞/点踩；点踩可填「期望答案」作为纠错。",
    },
    {
      title: "研判",
      detail: "点「规则研判」自动分类（检索未命中、幻觉等）；复杂 case 用「大模型研判」。",
    },
    {
      title: "采纳 / 驳回",
      detail: "状态为「已分类」时可操作。采纳会执行建议动作（如加入评测集、提议别名）。",
    },
    {
      title: "看结果",
      detail: "采纳后状态变「已执行」；若写入 golden 评测集，后台会自动跑评测 → 到「评测报告」查看指标变化。",
    },
  ] satisfies HelpStep[],
  tips: [
    "优先处理 👎 + 高严重度；「查看链路」可看检索与生成全过程（需开启 Trace）。",
    "导出 JSONL 用于离线分析或备份，不影响线上数据。",
  ],
};

export const EVAL_REPORTS_HELP = {
  summary:
    "用 golden.jsonl（标准问答对）离线测 RAG 质量。报告对比「当前 vs 上一份」指标，判断采纳反馈后是否变好。",
  steps: [
    {
      title: "准备数据",
      detail: "文件位于 enterprise_rag/data/eval/golden.jsonl；也可在反馈页采纳坏例时自动追加。",
    },
    {
      title: "触发评测",
      detail: "点「立即评测」手动跑；或在反馈页采纳写入 golden 后系统自动异步评测。",
    },
    {
      title: "读指标",
      detail: "忠实度 = 答案是否忠于资料；相关性 = 是否答非所问；重叠率为无 RAGAS 时的简易指标。",
    },
    {
      title: "对比 Δ",
      detail: "绿色上升 / 橙色下降表示相对上一份报告的变化，用于验证改动是否有效。",
    },
  ] satisfies HelpStep[],
  tips: [
    "没有 golden 数据时列表为空，先入库文档或在反馈页采纳几条典型坏例。",
    "RAGAS 需配置评测用 LLM；不可用时会自动 Naive 回退。",
  ],
};

export const MEMORY_PAGE_HELP = {
  summary:
    "设置 Chat 的默认行为（非用户单次开关）。建议先用顶部「业务场景预设」一键配置，再在 Tab 里微调。",
  steps: [
    {
      title: "选场景预设",
      detail:
        "一线 KB / 新媒体内容分析 / 内测全功能 / LAN API — 运营与媒体部建议「新媒体 / 内容分析」。",
    },
    {
      title: "基础",
      detail: "记忆轮数、默认助手模式、推荐问题 — 影响 Chat 首次打开时的体验。",
    },
    {
      title: "检索与 KB",
      detail: "阈值与 LLM 判断 — 决定「何时走知识库、何时走通用」。",
    },
    {
      title: "多轮与性能",
      detail: "Condense / 剪枝 / 摘要控制长对话；性能路由选 fast/balanced/quality。",
    },
  ] satisfies HelpStep[],
  tips: ["一线老师用「一线 KB 问答」；运营/媒体/剪辑用「新媒体 / 内容分析」— 详见「业务场景」页。"],
};

export const SCENARIOS_PAGE_HELP = {
  summary:
    "按部门列出可用的卖课 / 内容场景：每个场景含目标、操作步骤；技术部可开「开发视图」看 API 与代码路径。",
  steps: [
    {
      title: "选对部门登录",
      detail: "登录时选运营部 / 媒体部 / 剪辑部，本页只显示该部门相关场景。",
    },
    {
      title: "展开场景卡片",
      detail: "点击卡片查看逐步操作；到 Jnao Chat 按步骤提问即可。",
    },
    {
      title: "技术部开发视图",
      detail: "切换右上角按钮，查看 stream API 参数、content-kit、源码路径；改 catalog JSON 后刷新即生效。",
    },
  ] satisfies HelpStep[],
  tips: [
    "catalog 文件：enterprise_rag/data/config/scenario_catalog.json",
    "新增场景时同步更新 API 与前端无需改代码，除非新增全新能力。",
  ],
};

export const METRIC_LABELS_ZH: Record<string, string> = {
  naive_context_answer_overlap_rate: "资料-答案重叠率",
  faithfulness: "忠实度（不编造）",
  answer_relevancy: "答案相关性",
  rows: "评测样本数",
  mode: "评测模式",
  ragas_error: "RAGAS 错误",
};

export const ACTION_LABELS_ZH: Record<string, string> = {
  add_to_golden: "加入标准评测集",
  propose_reingest: "建议重新入库文档",
  apply_config_patch: "自动调整配置",
  apply_query_alias: "添加口语别名（检索纠错）",
  propose_query_alias: "提议口语别名（待确认）",
};
