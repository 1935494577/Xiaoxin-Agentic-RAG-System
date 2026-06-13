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

  return (
    <div className="p-6 max-w-[820px]">
      <PageHeader title="使用操作教程" />

      <div className="prose prose-sm max-w-none text-text space-y-6">
        {/* 服务入口 */}
        <section>
          <h3 className="text-base font-semibold mb-2">服务入口</h3>
          <p className="text-sm text-text-muted mb-3">
            系统为前后端一体架构，前端 SPA 统一入口在 <strong>端口 8502</strong>，后端 API 在 <strong>端口 8010</strong>。
            启动后浏览器打开对应地址即可。
          </p>
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
                <td className="py-2 font-semibold">前端 SPA</td>
                <td className="py-2 text-brand">http://127.0.0.1:8502</td>
                <td className="py-2">Jnao Chat + 管理后台统一入口</td>
              </tr>
              <tr className="border-b border-border-light">
                <td className="py-2 font-semibold">后端 API</td>
                <td className="py-2 text-brand">http://127.0.0.1:8010</td>
                <td className="py-2">FastAPI，提供 /chat /config /ingest 等接口</td>
              </tr>
              <tr>
                <td className="py-2 font-semibold">API 文档</td>
                <td className="py-2 text-brand">http://127.0.0.1:8010/docs</td>
                <td className="py-2">Swagger UI，在线调试 API</td>
              </tr>
            </tbody>
          </table>
          <p className="text-text-muted text-xs mt-1">左侧导航栏可在 Jnao Chat 与管理后台各页面之间切换，无需切换端口。</p>
        </section>

        <hr className="border-border-light" />

        {/* Steps */}
        <section>
          <h3 className="text-base font-semibold mb-2">1. 配置大模型</h3>
          <p className="text-sm text-text-muted">左侧导航进入 <strong>模型</strong> 页，填写 OpenAI 兼容 API 地址与密钥，测试通过后保存并设为默认。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">2. 上传文档入库</h3>
          <p className="text-sm text-text-muted mb-1">左侧导航进入 <strong>数据入库</strong> 页：</p>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-0.5">
            <li>支持格式：<strong>{fmt}</strong></li>
            <li>可选<strong>入库标签</strong>（预设 + 自定义，逗号分隔）</li>
            <li><strong>已清洗数据</strong> / <strong>未清洗数据</strong> 两种模式；未清洗将走<strong>工具</strong>页配置的解析清洗链</li>
            <li>侧边栏设置<strong>归属部门</strong>与可见范围后上传</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">3. 向量库（可选）</h3>
          <p className="text-sm text-text-muted"><strong>向量库</strong>页可管理 Milvus Lite / NumPy 等存储实例，支持创建与切换激活库。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">4. Jnao Chat 对话</h3>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-0.5">
            <li>默认<strong>仅知识库检索</strong>；输入框上方可开<strong>混合专家模式</strong>（知识库优先，未命中时补充通用回答）</li>
            <li>侧栏选<strong>部门权限</strong>，与入库部门一致时检索效果更好</li>
            <li>支持多会话管理：新建、切换、删除会话，历史消息自动持久化</li>
            <li>发送后 AI 头像立即出现并显示"…"思考提示，收到 token 后流式输出</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">5. 对话设置（管理员）</h3>
          <p className="text-sm text-text-muted">
            <strong>对话设置</strong>页按标签分组：<strong>基础</strong>（记忆轮数、混合专家默认、推荐问题）、
            <strong>检索与 KB</strong>（阈值与 LLM 判断）、<strong>多轮上下文</strong>（condense / 剪枝 / 滚动摘要）、
            <strong>性能路由</strong>（fast / balanced / quality）。预处理模型在 <strong>模型</strong> 页配置。
          </p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">6. 提示词（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>提示词</strong>页：按 Prompt 工程分层配置 System Prompt（角色人设 → 约束 → 任务 → 输出），每层可独立启用/自定义。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">7. 工具（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>工具</strong>页：入库清洗工具（Presidio 脱敏、语种检测等）开关、大模型选工具路由。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">8. 链路 Trace（管理员）</h3>
          <p className="text-sm text-text-muted">查看 LangSmith 云端 / 本地 JSONL 链路追踪状态与文件位置。</p>
        </section>

        <hr className="border-border-light" />

        {/* FAQ */}
        <section>
          <h3 className="text-base font-semibold mb-2">常见问题</h3>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
            <li><strong>搜不到文档</strong>：对话部门与入库部门需一致（默认「技术」），切换侧栏部门重试。</li>
            <li><strong>切换页面后会话丢失</strong>：消息已自动持久化到后端，切回 Jnao Chat 即恢复。</li>
            <li><strong>模型无回复</strong>：检查<strong>模型</strong>页连接状态与 API Key 是否正确。</li>
            <li><strong>输入框多行不换行</strong>：Shift+Enter 换行，Enter 直接发送。</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
