import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/admin/PageHeader";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import {
  assembleExamPaper,
  createExamCollection,
  createExamQuestion,
  detectExamSections,
  fetchExamCollections,
  fetchExamInventory,
  fetchExamMeta,
  fetchExamQuestions,
  formatExamApiError,
} from "../../lib/examBank";

export default function ExamBankPage() {
  const { session } = useAuth();
  const userId = session?.userId || session?.username || "";
  const qc = useQueryClient();

  const [filterSubject, setFilterSubject] = useState("数学");
  const [filterGrade, setFilterGrade] = useState("初二");
  const [filterStage, setFilterStage] = useState("junior");
  const [useLlm, setUseLlm] = useState(true);
  const [routerInfo, setRouterInfo] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [colForm, setColForm] = useState({
    name: "",
    subject: "数学",
    grade: "初二",
    region: "某地",
    visibility: "private",
  });
  const [qForm, setQForm] = useState({
    qtype: "choice",
    difficulty: 3,
    stem: "",
    options: "A. …\nB. …\nC. …\nD. …",
    answer: "",
    analysis: "",
    tags: "",
    customQtype: "",
  });
  const [paperTitle, setPaperTitle] = useState("模拟卷 A");
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({ choice: 3, fill: 0 });
  const [bandCounts, setBandCounts] = useState({ easy: 0, mid: 0, hard: 0 });
  const [paperText, setPaperText] = useState("");
  const [detected, setDetected] = useState<
    { heading: string; label: string; qtype: string; approx_count?: number }[]
  >([]);
  const [markdown, setMarkdown] = useState("");
  const [error, setError] = useState("");

  const metaQ = useQuery({
    queryKey: ["exam-meta", filterStage, filterGrade],
    queryFn: () => fetchExamMeta({ stage: filterStage, grade: filterGrade }),
  });

  const colsQ = useQuery({
    queryKey: ["exam-collections", filterSubject, filterGrade, userId],
    queryFn: () =>
      fetchExamCollections({
        subject: filterSubject,
        grade: filterGrade,
        readerUserId: userId || undefined,
      }),
  });

  const subjects = metaQ.data?.subjects || [];
  const subjectMeta = subjects.find((s) => s.id === filterSubject) || subjects[0];
  const grades = subjectMeta?.grades || ["初一", "初二", "初三"];

  const activeId = collectionId || colsQ.data?.items?.[0]?.id || "";

  const inventoryQ = useQuery({
    queryKey: ["exam-inventory", activeId],
    queryFn: () => fetchExamInventory(activeId),
    enabled: Boolean(activeId),
  });

  const questionsQ = useQuery({
    queryKey: ["exam-questions", activeId],
    queryFn: () => fetchExamQuestions(activeId),
    enabled: Boolean(activeId),
  });

  const availableTypes = useMemo(() => {
    const fromSubject = subjectMeta?.qtypes || [];
    const map = new Map(fromSubject.map((t) => [t.id, t.label]));
    for (const row of inventoryQ.data?.by_qtype_labeled || []) {
      map.set(row.id, row.label);
    }
    if (qForm.customQtype.trim()) {
      const id = qForm.customQtype.trim().startsWith("custom:")
        ? qForm.customQtype.trim()
        : `custom:${qForm.customQtype.trim()}`;
      map.set(id, qForm.customQtype.trim().replace(/^custom:/, ""));
    }
    return [...map.entries()].map(([id, label]) => ({ id, label }));
  }, [subjectMeta, inventoryQ.data, qForm.customQtype]);

  useEffect(() => {
    setColForm((s) => ({ ...s, subject: filterSubject, grade: filterGrade }));
    const defaults: Record<string, number> = {};
    for (const t of subjectMeta?.qtypes || []) {
      defaults[t.id] = t.id === "choice" ? 3 : 0;
    }
    setTypeCounts(defaults);
  }, [filterSubject, filterGrade, subjectMeta?.id]);

  const createCol = useMutation({
    mutationFn: () =>
      createExamCollection({
        ...colForm,
        name: colForm.name || `${colForm.subject}-${colForm.grade}-${colForm.region}`,
        owner_user_id: userId,
      }),
    onSuccess: (row) => {
      setError("");
      setCollectionId(row.id);
      void qc.invalidateQueries({ queryKey: ["exam-collections"] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const createQ = useMutation({
    mutationFn: () => {
      const qt = qForm.customQtype.trim() || qForm.qtype;
      return createExamQuestion({
        collection_id: activeId,
        qtype: qt,
        difficulty: Number(qForm.difficulty),
        stem: qForm.stem,
        options: qForm.options
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        answer: qForm.answer,
        analysis: qForm.analysis,
        knowledge_tags: qForm.tags
          .split(/[,，]/)
          .map((s) => s.trim())
          .filter(Boolean),
        quality_status: "published",
      });
    },
    onSuccess: () => {
      setError("");
      setQForm((s) => ({ ...s, stem: "", answer: "", analysis: "" }));
      void qc.invalidateQueries({ queryKey: ["exam-questions", activeId] });
      void qc.invalidateQueries({ queryKey: ["exam-inventory", activeId] });
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const detectMut = useMutation({
    mutationFn: () =>
      detectExamSections({
        text: paperText,
        subject: filterSubject,
        grade: filterGrade,
        use_llm: useLlm,
      }),
    onSuccess: (body) => {
      setDetected(body.sections || []);
      setError("");
      setRouterInfo(
        `路由：${body.router}${body.model ? ` · ${body.model}` : ""}${
          body.confidence != null ? ` · 置信度 ${body.confidence}` : ""
        }${body.note ? ` · ${body.note}` : ""}`,
      );
      if (body.subject) setFilterSubject(body.subject);
      if (body.grade) setFilterGrade(body.grade);
      if (body.stage) setFilterStage(body.stage);
      const next: Record<string, number> = {};
      for (const t of body.suggested_qtypes || []) {
        next[t.id] = 0;
      }
      for (const s of body.sections || []) {
        const n = s.approx_count && s.approx_count > 0 ? s.approx_count : next[s.qtype] || 0;
        next[s.qtype] = Math.max(n, next[s.qtype] || 0);
        if (!next[s.qtype]) next[s.qtype] = s.approx_count || 0;
      }
      if (Object.keys(next).length) setTypeCounts(next);
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const assemble = useMutation({
    mutationFn: () => {
      const by_qtype: Record<string, number> = {};
      for (const [k, v] of Object.entries(typeCounts)) {
        if (v > 0) by_qtype[k] = v;
      }
      const by_difficulty_band: Record<string, number> = {};
      for (const [k, v] of Object.entries(bandCounts)) {
        if (v > 0) by_difficulty_band[k] = v;
      }
      return assembleExamPaper({
        collection_id: activeId,
        title: paperTitle,
        include_answers: true,
        spec: {
          by_qtype,
          ...(Object.keys(by_difficulty_band).length ? { by_difficulty_band } : {}),
          seed: 42,
        },
      });
    },
    onSuccess: (body) => {
      setError("");
      setMarkdown(body.markdown || "");
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  return (
    <div className="p-6 max-w-[1100px] space-y-8">
      <PageHeader
        title="题库与组卷"
        description="按学科 / 年级选题库与题型；支持整卷标题识别（一、选择题…）；多选配比与难度档；缺题型会明确提示。"
      />

      <div className="rounded-xl border border-border bg-surface-muted/40 p-4 text-sm text-text-muted space-y-1">
        <p>
          场景：
          <Link to="/admin/scenarios" className="text-brand hover:underline mx-1">
            exam_assemble
          </Link>
          · API <code className="text-xs">/api/exam/*</code> · 与 Chat 向量库隔离
          {metaQ.data?.llm?.model ? (
            <>
              {" "}
              · 试卷路由模型 <code className="text-xs">{metaQ.data.llm.model}</code>
              {metaQ.data.llm.key_configured ? "" : "（未配置 API Key，将走规则兜底）"}
            </>
          ) : null}
        </p>
      </div>

      {error ? (
        <p className="text-sm text-warning whitespace-pre-wrap rounded-lg border border-warning/40 bg-warning/5 px-3 py-2">
          {error}
        </p>
      ) : null}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text">0. 学段 / 学科 / 年级</h3>
        <div className="grid gap-2 sm:grid-cols-3">
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            value={filterStage}
            onChange={(e) => setFilterStage(e.target.value)}
          >
            {(metaQ.data?.stages || [
              { id: "junior", label: "初中" },
              { id: "senior", label: "高中" },
              { id: "primary", label: "小学" },
            ]).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            value={filterSubject}
            onChange={(e) => setFilterSubject(e.target.value)}
          >
            {(subjects.length ? subjects : [{ id: "数学", label: "数学" }]).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            value={filterGrade}
            onChange={(e) => setFilterGrade(e.target.value)}
          >
            {grades.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>
        <p className="text-xs text-text-muted">
          默认题型随学段变化（如数学=选择/填空/解答）。组卷选项=模板 ∪ 库内实有 ∪ 自定义。
        </p>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text">1. 题库空间（collection）</h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <input
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            placeholder="名称（可空自动生成）"
            value={colForm.name}
            onChange={(e) => setColForm((s) => ({ ...s, name: e.target.value }))}
          />
          <input
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            placeholder="地区"
            value={colForm.region}
            onChange={(e) => setColForm((s) => ({ ...s, region: e.target.value }))}
          />
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            value={colForm.visibility}
            onChange={(e) => setColForm((s) => ({ ...s, visibility: e.target.value }))}
          >
            <option value="private">私有（仅自己）</option>
            <option value="tenant_shared">组织共享</option>
            <option value="platform">平台精选</option>
          </select>
        </div>
        <Button type="button" size="sm" onClick={() => createCol.mutate()} disabled={createCol.isPending}>
          创建题库（{filterSubject}/{filterGrade}）
        </Button>
        <div className="flex flex-wrap gap-2">
          {(colsQ.data?.items || []).map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCollectionId(c.id)}
              className={`rounded-lg border px-3 py-1.5 text-xs ${
                activeId === c.id ? "border-brand bg-brand/10 text-brand" : "border-border text-text-muted"
              }`}
            >
              {c.name} · {c.region || "—"}
            </button>
          ))}
          {!colsQ.data?.items?.length ? (
            <span className="text-xs text-text-muted">当前学科/年级下暂无题库，请先创建。</span>
          ) : null}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text">1b. 整卷智能识别（默认大模型路由）</h3>
        <textarea
          className="w-full min-h-[88px] rounded-lg border border-border bg-surface px-3 py-2 text-sm"
          placeholder={"粘贴试卷文本，例如：\n一、选择题\n二、填空题\n三、解答题"}
          value={paperText}
          onChange={(e) => setPaperText(e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-text-muted">
          <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
          使用大模型路由（关闭则仅规则识别标题）
        </label>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => detectMut.mutate()}
          disabled={!paperText.trim() || detectMut.isPending}
        >
          {detectMut.isPending ? "识别中…" : "识别科目 / 题型 / 估计题量"}
        </Button>
        {routerInfo ? <p className="text-xs text-text-muted">{routerInfo}</p> : null}
        {detected.length > 0 ? (
          <ul className="text-xs text-text-muted space-y-1">
            {detected.map((s, i) => (
              <li key={`${s.qtype}-${i}`}>
                {s.heading} → {s.label}（{s.qtype}
                {s.approx_count ? ` · 约 ${s.approx_count} 题` : ""}）
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text">2. 录题（published）</h3>
        {!activeId ? (
          <p className="text-sm text-text-muted">请先创建或选择题库。</p>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-3">
              <select
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                value={qForm.qtype}
                onChange={(e) => setQForm((s) => ({ ...s, qtype: e.target.value, customQtype: "" }))}
              >
                {availableTypes.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
              <input
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                placeholder="自定义题型（优先）"
                value={qForm.customQtype}
                onChange={(e) => setQForm((s) => ({ ...s, customQtype: e.target.value }))}
              />
              <input
                type="number"
                min={1}
                max={5}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                value={qForm.difficulty}
                onChange={(e) => setQForm((s) => ({ ...s, difficulty: Number(e.target.value) }))}
                title="难度 1–5"
              />
            </div>
            <textarea
              className="w-full min-h-[72px] rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="题干"
              value={qForm.stem}
              onChange={(e) => setQForm((s) => ({ ...s, stem: e.target.value }))}
            />
            <textarea
              className="w-full min-h-[64px] rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              placeholder="选项（每行一项）"
              value={qForm.options}
              onChange={(e) => setQForm((s) => ({ ...s, options: e.target.value }))}
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                placeholder="答案"
                value={qForm.answer}
                onChange={(e) => setQForm((s) => ({ ...s, answer: e.target.value }))}
              />
              <input
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
                placeholder="解析 / 知识点标签"
                value={qForm.tags}
                onChange={(e) => setQForm((s) => ({ ...s, tags: e.target.value }))}
              />
            </div>
            <Button type="button" size="sm" onClick={() => createQ.mutate()} disabled={!qForm.stem || createQ.isPending}>
              发布题目
            </Button>
            <p className="text-xs text-text-muted">
              库存：共 {inventoryQ.data?.total ?? 0} 题
              {(inventoryQ.data?.by_qtype_labeled || [])
                .map((x) => ` · ${x.label} ${x.count}`)
                .join("")}
            </p>
            <ul className="text-sm space-y-1 max-h-36 overflow-auto">
              {(questionsQ.data?.items || []).slice(0, 15).map((q) => (
                <li key={q.id} className="text-text-muted truncate">
                  [{q.qtype}/D{q.difficulty}] {q.stem}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text">3. 组卷导出（多选题型 + 难度档）</h3>
        <input
          className="w-full max-w-md rounded-lg border border-border bg-surface px-3 py-2 text-sm"
          value={paperTitle}
          onChange={(e) => setPaperTitle(e.target.value)}
          placeholder="试卷标题"
        />
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {availableTypes.map((t) => (
            <label key={t.id} className="flex items-center gap-2 text-sm text-text-muted border border-border rounded-lg px-3 py-2">
              <span className="flex-1 truncate">{t.label}</span>
              <span className="text-xs opacity-70">库内 {inventoryQ.data?.by_qtype?.[t.id] ?? 0}</span>
              <input
                type="number"
                min={0}
                className="w-16 rounded border border-border bg-surface px-2 py-1"
                value={typeCounts[t.id] ?? 0}
                onChange={(e) =>
                  setTypeCounts((s) => ({ ...s, [t.id]: Number(e.target.value) }))
                }
              />
            </label>
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          {(metaQ.data?.difficulty_bands || [
            { id: "easy", label: "简单" },
            { id: "mid", label: "中等" },
            { id: "hard", label: "困难" },
          ]).map((b) => (
            <label key={b.id} className="flex items-center gap-2 text-sm text-text-muted">
              {b.label}
              <input
                type="number"
                min={0}
                className="w-16 rounded-lg border border-border bg-surface px-2 py-1"
                value={bandCounts[b.id as keyof typeof bandCounts] ?? 0}
                onChange={(e) =>
                  setBandCounts((s) => ({ ...s, [b.id]: Number(e.target.value) }))
                }
              />
            </label>
          ))}
        </div>
        <p className="text-xs text-text-muted">难度档为 0 表示不按难度约束；某题型数量&gt;0 但库中无该题型时会提示「没有相应题型」。</p>
        <Button type="button" size="sm" onClick={() => assemble.mutate()} disabled={!activeId || assemble.isPending}>
          生成试卷 Markdown
        </Button>
        {markdown ? (
          <pre className="whitespace-pre-wrap rounded-xl border border-border bg-surface p-4 text-xs text-text max-h-[420px] overflow-auto">
            {markdown}
          </pre>
        ) : null}
      </section>
    </div>
  );
}
