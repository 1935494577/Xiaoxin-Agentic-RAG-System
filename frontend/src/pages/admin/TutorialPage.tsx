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
    <div className="space-y-6">
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
            <li>
              顶部分通道：<strong>知识文档</strong>（进向量库问答）与{" "}
              <strong>试卷题库</strong>（切题/公式/Chat 答题，勿与知识库混用）
            </li>
            <li>知识文档支持格式：<strong>{fmt}</strong></li>
            <li>可选<strong>入库标签</strong>（预设 + 自定义，逗号分隔）</li>
            <li><strong>已清洗数据</strong> / <strong>未清洗数据</strong> 两种模式；未清洗将走<strong>工具</strong>页配置的解析清洗链</li>
            <li>侧边栏设置<strong>归属部门</strong>与可见范围后上传</li>
            <li>试卷请点「试卷题库」→「前往题库入库向导」，不要走知识文档上传</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">3. 向量库（可选）</h3>
          <p className="text-sm text-text-muted"><strong>向量库</strong>页可管理 Milvus Lite / NumPy 等存储实例，支持创建与切换激活库。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">4. Jnao Chat 对话</h3>
          <ul className="list-disc pl-5 text-sm text-text-muted space-y-0.5">
            <li>
              输入框上方可选<strong>知识 / 任务 / 自动</strong>：知识=仅知识库；任务=多步工具；自动=按服务端配置
            </li>
            <li>侧栏选<strong>部门权限</strong>，与入库部门一致时检索效果更好</li>
            <li>支持多会话管理：新建、切换、删除会话，历史消息自动持久化</li>
            <li>发送后 AI 头像立即出现并显示"…"思考提示，收到 token 后流式输出</li>
          </ul>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">5. 对话设置（管理员）</h3>
          <p className="text-sm text-text-muted">
            <strong>对话设置</strong>页：顶部「业务场景预设」一键配置（一线 KB / 内测全功能 / LAN API），
            Tab 分组为<strong>基础</strong>、<strong>检索与 KB</strong>、<strong>多轮上下文</strong>、<strong>性能路由</strong>。
          </p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">6. 提示词（管理员）</h3>
          <p className="text-sm text-text-muted">
            <strong>提示词</strong>页控制 AI「怎么说」：先选业务角色，再按「角色 → 约束 → 任务 → 输出」四层微调。
            预览类型选「知识库回答」或「通用回答」分别编辑；不必理解英文内部标识。
          </p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">7. 用户反馈 → 评测闭环（管理员）</h3>
          <p className="text-sm text-text-muted mb-2">
            质量改进的推荐路径（各页顶部也有「怎么用」折叠说明）：
          </p>
          <ol className="list-decimal pl-5 text-sm text-text-muted space-y-1">
            <li>
              用户在 <strong>Jnao Chat</strong> 对回答点 👍/👎；点踩可填期望答案。
            </li>
            <li>
              <strong>用户反馈</strong>页 →「规则研判」分类 bad case → 对「已分类」条目点「采纳并执行建议」。
            </li>
            <li>
              系统自动执行改进（如加入标准评测集 golden、提议检索别名等），状态变为「已执行」。
            </li>
            <li>
              <strong>评测报告</strong>页查看指标；采纳写入 golden 后会自动跑评测，也可手动「立即评测」。
            </li>
            <li>对比报告中的 Δ（相对上一份），确认忠实度/相关性是否提升。</li>
          </ol>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">8. 工具（管理员）</h3>
          <p className="text-sm text-text-muted"><strong>工具</strong>页：入库清洗工具（Presidio 脱敏、语种检测等）开关、大模型选工具路由。</p>
        </section>

        <section>
          <h3 className="text-base font-semibold mb-2">9. 链路 Trace（管理员）</h3>
          <p className="text-sm text-text-muted">查看本地 JSONL 链路追踪状态与文件位置。反馈页「查看链路」依赖此功能。</p>
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
