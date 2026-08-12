import { Link } from "react-router-dom";
import { PageHeader } from "../../components/admin/PageHeader";

const CARDS = [
  {
    to: "/admin/exam-bank/ingest?step=1",
    title: "试卷入库",
    desc: "填写学科年级 → 创建/选题库 → 导入 PDF/Word → 预览编辑 → 答案（可跳过）",
  },
  {
    to: "/admin/exam-bank/assemble",
    title: "试卷导出",
    desc: "选题库后填写每种题型道数与简单/中等/困难，一次生成 Markdown",
  },
  {
    to: "/admin/exam-bank/manage",
    title: "题库管理",
    desc: "查看已有题库空间，删除或跳转入库/组卷",
  },
] as const;

export default function ExamBankPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="题库与组卷"
        description="先选任务，再进入分步流程。科目题型包在入库第一步锁定，英语与数学互不混用。"
      />

      <div className="grid gap-4 md:grid-cols-3">
        {CARDS.map((c) => (
          <Link
            key={c.to}
            to={c.to}
            className="group rounded-xl border border-border bg-surface p-5 hover:border-brand/50 hover:bg-brand/5 transition-colors"
          >
            <h3 className="text-base font-semibold text-text group-hover:text-brand">{c.title}</h3>
            <p className="mt-2 text-sm text-text-muted leading-relaxed">{c.desc}</p>
            <span className="mt-4 inline-block text-sm text-brand">进入 →</span>
          </Link>
        ))}
      </div>

      <p className="text-xs text-text-muted">
        场景{" "}
        <Link to="/admin/scenarios" className="text-brand hover:underline">
          exam_assemble
        </Link>{" "}
        · API <code className="text-xs">/api/exam/*</code> · 与 Chat 向量库隔离
      </p>
    </div>
  );
}
