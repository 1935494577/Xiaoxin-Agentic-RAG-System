import { useQuery } from "@tanstack/react-query";
import { fetchUiConfig } from "../../api/client";
import { PageHeader } from "../../components/admin/PageHeader";

export default function TutorialPage() {
  const { data: ui } = useQuery({
    queryKey: ["uiConfig"],
    queryFn: fetchUiConfig,
    staleTime: 300_000,
  });
  const fmt = ui?.supported_upload_label || "TXT · MD · PDF · DOCX · HTML";
  const chatUrl = "http://127.0.0.1:8502";

  return (
    <div className="p-6 max-w-[820px]">
      <PageHeader title="使用操作教程" />

      <div className="prose prose-sm max-w-none text-text space-y-6">
        {/* 服务入口 */}
        <section>
          <h3 className="text-base font-semibold mb-2">服务入口</h3>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 font-medium">服务</th>
                <th className="text-left py-2 font-medium">地址</th>
                <th className="text-left py-2 font-medium">说明</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border-light">
                <td className="py-2 font-semibold">Jnao Chat</td>
                <td className="py-2 text-brand">{chatUrl}</td>
                <td className="py-2">主对话界面（流式 RAG）</td>
              </tr>
              <tr className="border-b border-border-light">
                <td className="py-2 font-semibold">管理后台</td>
                <td className="py-2">8501</td>
                <td className="py-2">入库、配置、模型、提示词等</td>
              </tr>
              <tr>
                <td className="py-2 font-semibold">API</td>
                <td className="py-2">8010</td>
                <td className="py-2">FastAPI，供前后端调用</td>
              </tr>
            </tbody>
          </table>
          <p className="text-text-muted text-xs mt-1">顶部导航可在 Jnao Chat 与管理页之间切换。</p>
        </section>

        <hr className="border-border-light" />

        {/* Steps */}
        <section>
          <h3 className="text-base font-semibold mb-2">1. 配置大模型</h3>
          <p className="text-sm text-text-muted">打开 <strong>模型</strong>，填写 OpenAI 兼容 API 地址与密钥，测试通过后保存并设为默认。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">2. 上传文档入库</h3>
          <p className="text-sm text-text-muted mb-1">打开 <strong>数据入库</strong>（默认首页）：</p>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-0.5">
            <li>支持格式：<strong>{fmt}</strong></li>
            <li>可选<strong>入库标签</strong>（预设 + 自定义，逗号分隔）</li>
            <li><strong>已清洗数据</strong> / <strong>未清洗数据</strong> 两种模式；未清洗将走<strong>工具</strong>页配置的解析清洗链</li>
            <li>侧边栏设置<strong>归属部门</strong>与可见范围后上传</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">3. 向量库（可选）</h3>
          <p className="text-sm text-text-muted"><strong>向量库</strong>页可管理 Milvus Lite / NumPy 等存储实例并切换激活库。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">4. Jnao Chat 对话</h3>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-0.5">
            <li>默认<strong>仅知识库检索</strong>；输入框上方可开<strong>混合专家模式</strong>（知识库优先，未命中时补充通用回答）</li>
            <li>侧栏选<strong>部门权限</strong>，与入库部门一致时检索效果更好</li>
            <li>支持多会话、长期记忆（session_id 自动持久化）</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">5. 对话记忆（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>对话记忆</strong>页：短期/长期记忆参数、检索阈值、混合专家默认开关、Jnao Chat <strong>推荐问题</strong>等。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">6. 提示词（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>提示词</strong>页：按 Prompt 工程分层配置 System Prompt（角色人设 → 约束 → 任务 → 输出），可插拔启用/自定义层。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">7. 工具（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>工具</strong>页：入库清洗工具开关、大模型选工具路由。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">8. 链路 Trace（管理员）</h3>
          <p className="text-sm text-text-muted">查看 LangSmith / 本地 JSONL 链路说明与 trace 状态。</p>
        </section>

        <hr className="border-border-light" />

        {/* FAQ */}
        <section>
          <h3 className="text-base font-semibold mb-2">常见问题</h3>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
            <li><strong>搜不到文档</strong>：对话部门与入库部门需一致（默认「技术」）。</li>
            <li><strong>Page not found</strong>：数据入库请访问管理后台根路径 `/`，勿用 `/ingest`。</li>
            <li><strong>模型无回复</strong>：检查<strong>模型</strong>页连接状态与 API Key。</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
