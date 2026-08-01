import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../../../components/ui/Button";
import { useAuth } from "../../../context/AuthContext";
import {
  assembleExamPaperNl,
  autoGenerateExamPaper,
  downloadExamPaperExport,
  EXAM_EXPORT_FORMAT_OPTIONS,
  DEFAULT_EXAM_EXPORT_FORMAT,
  fetchExamCollections,
  fetchExamInventory,
  fetchExamMeta,
  fetchExamSourcePaper,
  finalizeExamBasket,
  formatExamApiError,
  generateExamLesson,
  swapExamQuestion,
  type ExamExportFormat,
  type ExamQuestion,
  type ExamSourcePaper,
} from "../../../lib/examBank";
import { ExamAssembleDashboard } from "./ExamAssembleDashboard";
import {
  ExamDiffProportionCard,
  splitNeedByPaperDiff,
} from "./ExamDiffProportionCard";
import { ExamField, ExamWizardChrome, examControlClass } from "./ExamWizardChrome";
import { ExamBasketPanel, ExamQuestionCard } from "./ExamQuestionBasket";
import { ExamMathText, collapseSpacedCjk } from "./ExamMathText";
import { ExamQuestionEditDrawer } from "./ExamQuestionEditDrawer";

type RowSpec = { need: number; easy: number; mid: number; hard: number };
type ScenarioId = "practice" | "stage" | "final";
type DiffChip = "all" | "easy" | "mid" | "hard";
type LeftTab = "chapter" | "tag";
type YearPreset = "all" | "y3" | "y5" | "pick";

const SCENARIOS: {
  id: ScenarioId;
  label: string;
  titleHint: string;
  /** 相对科目题型包的默认需要道数（按 id 顺序取前几个） */
  defaultNeeds: Record<string, number>;
}[] = [
  {
    id: "practice",
    label: "课堂练习",
    titleHint: "课堂练习卷",
    defaultNeeds: { choice: 5, fill: 3, short: 1, calc: 1 },
  },
  {
    id: "stage",
    label: "阶段检测",
    titleHint: "阶段检测卷",
    defaultNeeds: { choice: 8, fill: 4, short: 3, calc: 2 },
  },
  {
    id: "final",
    label: "期末备考",
    titleHint: "期末备考卷",
    defaultNeeds: { choice: 10, fill: 5, short: 4, calc: 2, big: 1 },
  },
];

const DIFF_CHIPS: { id: DiffChip; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "easy", label: "容易" },
  { id: "mid", label: "适中" },
  { id: "hard", label: "困难" },
];

function ExamPaperBody({
  title,
  questions,
  includeAnswers,
}: {
  title: string;
  questions: ExamQuestion[];
  includeAnswers: boolean;
}) {
  const anyMedia = questions.some((q) => Boolean(q.media_ingest_id));
  return (
    <div
      className="px-5 py-6 text-[14px] leading-7 text-[#1a1a1a] text-left space-y-5"
      style={{ fontFamily: '"Songti SC", "SimSun", "Noto Serif SC", serif' }}
    >
      <h2 className="text-center text-lg font-semibold tracking-wide">{title || "试卷"}</h2>
      {!anyMedia ? (
        <p className="text-[11px] text-warning text-center border border-dashed border-warning/40 rounded px-2 py-1">
          本题卷无公式图片媒体（多为 PDF 纯文本入库）。几何图会空白；汉字抽字空格已自动合并。优先用
          Word 卷或 Structure 重入库。
        </p>
      ) : null}
      {questions.map((q, i) => (
        <div key={q.id} className="space-y-1">
          <div>
            <span className="font-medium">{i + 1}. </span>
            <ExamMathText text={q.stem} mediaIngestId={q.media_ingest_id} />
          </div>
          {(q.options || []).map((o, oi) => (
            <div key={`${q.id}-o-${oi}`} className="pl-4">
              <ExamMathText text={o} mediaIngestId={q.media_ingest_id} />
            </div>
          ))}
          {includeAnswers && (q.answer || q.analysis) ? (
            <div className="pl-2 text-[13px] text-[#444] space-y-1 border-l-2 border-border/60 ml-1">
              {q.answer ? (
                <div>
                  <span className="text-text-muted">【答案】</span>
                  <ExamMathText text={q.answer} mediaIngestId={q.media_ingest_id} />
                </div>
              ) : null}
              {q.analysis ? (
                <div>
                  <span className="text-text-muted">【解析】</span>
                  <ExamMathText text={q.analysis} mediaIngestId={q.media_ingest_id} />
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

const TEMPLATE_KEY = "examAssembleTemplate:v3";

type SavedTemplate = {
  scenario: ScenarioId;
  diffChip: DiffChip;
  region: string;
  yearPreset: YearPreset;
  yearPick: string;
  selectedTags: string[];
  selectedChapters: string[];
  leftTab: LeftTab;
  rows: Record<string, RowSpec>;
  title: string;
  exportFormat: ExamExportFormat;
  includeAnswers: boolean;
};

function recentYears(n: number): string[] {
  const y = new Date().getFullYear();
  return Array.from({ length: n }, (_, i) => String(y - i));
}

function StepHeading({
  n,
  title,
  action,
  open,
  onToggle,
}: {
  n: string;
  title: string;
  action?: ReactNode;
  open?: boolean;
  onToggle?: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-2 mb-3">
      <button
        type="button"
        className="flex items-center gap-2 text-left"
        onClick={onToggle}
        disabled={!onToggle}
      >
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand text-xs font-semibold text-white">
          {n}
        </span>
        <h2 className="text-sm font-semibold text-text">{title}</h2>
        {onToggle ? (
          <span className="text-[11px] text-text-muted">{open ? "收起" : "展开"}</span>
        ) : null}
      </button>
      {action}
    </div>
  );
}

export default function ExamBankAssemblePage() {
  const { session } = useAuth();
  const userId = session?.userId || session?.username || "";
  const [params] = useSearchParams();
  const [collectionId, setCollectionId] = useState(params.get("collection") || "");
  const [title, setTitle] = useState("模拟卷 A");
  const [nlOpen, setNlOpen] = useState(false);
  const [nlText, setNlText] = useState("选择 8 + 填空 4 + 解答 4，中等难度");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [leftTab, setLeftTab] = useState<LeftTab>("tag");
  const [scenario, setScenario] = useState<ScenarioId>("stage");
  const [diffChip, setDiffChip] = useState<DiffChip>("all");
  const [region, setRegion] = useState("");
  const [yearPreset, setYearPreset] = useState<YearPreset>("all");
  const [yearPick, setYearPick] = useState("");
  const [open01, setOpen01] = useState(true);
  const [open02, setOpen02] = useState(true);
  const [open03, setOpen03] = useState(true);
  const [rows, setRows] = useState<Record<string, RowSpec>>({});
  const [markdown, setMarkdown] = useState("");
  const [lessonMd, setLessonMd] = useState("");
  const [paperId, setPaperId] = useState("");
  const [poolQuestions, setPoolQuestions] = useState<ExamQuestion[]>([]);
  const [basketIds, setBasketIds] = useState<string[]>([]);
  const [previewMode, setPreviewMode] = useState<"cards" | "paper">("cards");
  const [paperFullscreen, setPaperFullscreen] = useState(false);
  const [sourceTitles, setSourceTitles] = useState<Record<string, string>>({});
  const [sourceModal, setSourceModal] = useState<ExamSourcePaper | null>(null);
  const [editQuestion, setEditQuestion] = useState<ExamQuestion | null>(null);
  const [difficultyCoef, setDifficultyCoef] = useState(0.65);
  const [swapForId, setSwapForId] = useState<string | null>(null);
  const [swapCands, setSwapCands] = useState<ExamQuestion[]>([]);
  const [swapBusyId, setSwapBusyId] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExamExportFormat>(DEFAULT_EXAM_EXPORT_FORMAT);
  const [includeAnswers, setIncludeAnswers] = useState(true);
  const [requireComplete, setRequireComplete] = useState(true);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  const yearsAny = useMemo(() => {
    if (yearPreset === "y3") return recentYears(3);
    if (yearPreset === "y5") return recentYears(5);
    if (yearPreset === "pick" && yearPick) return [yearPick];
    return [] as string[];
  }, [yearPreset, yearPick]);

  const colsQ = useQuery({
    queryKey: ["exam-collections-all", userId],
    queryFn: () => fetchExamCollections(),
  });

  // 未选库时自动选第一个，避免「一句话组卷」按钮灰掉却无提示
  useEffect(() => {
    if (collectionId) return;
    const items = colsQ.data?.items || [];
    if (!items.length) return;
    setCollectionId(items[0].id);
  }, [collectionId, colsQ.data?.items]);

  const active = (colsQ.data?.items || []).find((c) => c.id === collectionId);
  const metaQ = useQuery({
    queryKey: ["exam-meta", active?.grade],
    queryFn: () => fetchExamMeta({ grade: active?.grade || "初二" }),
    enabled: Boolean(active),
  });
  const subjectMeta = (metaQ.data?.subjects || []).find((s) => s.id === active?.subject);
  const qtypes = subjectMeta?.qtypes || [];
  const formatOptions = (metaQ.data?.export_formats || []).length
    ? EXAM_EXPORT_FORMAT_OPTIONS.filter((o) =>
        (metaQ.data?.export_formats || []).includes(o.id),
      )
    : EXAM_EXPORT_FORMAT_OPTIONS;

  const lockedRegion = (active?.region || "").trim();

  useEffect(() => {
    if (lockedRegion) setRegion(lockedRegion);
  }, [lockedRegion]);

  const basketQuestions = useMemo(
    () => poolQuestions.filter((q) => basketIds.includes(q.id)),
    [poolQuestions, basketIds],
  );

  const qtypeLabelFn = (id: string) =>
    qtypes.find((t) => t.id === id)?.label ||
    metaQ.data?.qtype_labels?.[id] ||
    id;

  const invQ = useQuery({
    queryKey: [
      "exam-inventory",
      collectionId,
      selectedTags.join("|"),
      selectedChapters.join("|"),
      lockedRegion,
      yearsAny.join("|"),
    ],
    queryFn: () =>
      fetchExamInventory(collectionId, {
        tags: selectedTags,
        chapters: selectedChapters,
        regions: lockedRegion ? [lockedRegion] : [],
        years: yearsAny,
      }),
    enabled: Boolean(collectionId),
  });

  const tagRows = invQ.data?.by_tag || [];
  const chapterRows = invQ.data?.by_chapter || [];
  const inventoryYears = invQ.data?.years || [];
  useEffect(() => {
    if (!qtypes.length) return;
    setRows((prev) => {
      const next: Record<string, RowSpec> = {};
      for (const t of qtypes) {
        next[t.id] = prev[t.id] || { need: 0, easy: 0, mid: 0, hard: 0 };
      }
      return next;
    });
  }, [qtypes.map((t) => t.id).join("|")]);

  useEffect(() => {
    const sc = SCENARIOS.find((s) => s.id === scenario);
    if (!sc || !active) return;
    setTitle(`${active.subject || ""}${active.grade || ""}${sc.titleHint}`);
  }, [scenario, active?.id]);

  const applyScenarioDefaults = () => {
    const sc = SCENARIOS.find((s) => s.id === scenario);
    if (!sc || !qtypes.length) return;
    setRows(() => {
      const next: Record<string, RowSpec> = {};
      for (const t of qtypes) {
        const need = sc.defaultNeeds[t.id] ?? 0;
        const bands =
          diffChip === "all"
            ? { easy: 0, mid: 0, hard: 0 }
            : splitNeedByPaperDiff(need, diffChip);
        next[t.id] = { need, ...bands };
      }
      return next;
    });
    setHint(`已按「${sc.label}」填入建议题量，可再改`);
  };

  const applyPaperDiffMode = (mode: Exclude<DiffChip, "all">) => {
    setDiffChip(mode);
    setRows((prev) => {
      const next: Record<string, RowSpec> = { ...prev };
      for (const [id, r] of Object.entries(prev)) {
        if (!r || r.need <= 0) continue;
        next[id] = { need: r.need, ...splitNeedByPaperDiff(r.need, mode) };
      }
      return next;
    });
    setHint(`已按「${DIFF_CHIPS.find((d) => d.id === mode)?.label}」试卷难度拆分题量配比`);
  };

  const validation = useMemo(() => {
    const msgs: string[] = [];
    for (const t of qtypes) {
      const r = rows[t.id];
      if (!r || r.need <= 0) continue;
      const bandSum = r.easy + r.mid + r.hard;
      if (bandSum > 0 && bandSum !== r.need) {
        msgs.push(`${t.label}：简单+中等+困难应为 ${r.need}，当前 ${bandSum}`);
      }
    }
    return msgs;
  }, [rows, qtypes]);

  const buildSpec = () => {
    const by_qtype: Record<string, number> = {};
    const by_qtype_band: Record<string, Record<string, number>> = {};
    let anyBandConstraint = false;
    for (const [id, r] of Object.entries(rows)) {
      if (r.need <= 0) continue;
      by_qtype[id] = r.need;
      const bandSum = r.easy + r.mid + r.hard;
      if (bandSum > 0) {
        anyBandConstraint = true;
        by_qtype_band[id] = {
          ...(r.easy > 0 ? { easy: r.easy } : {}),
          ...(r.mid > 0 ? { mid: r.mid } : {}),
          ...(r.hard > 0 ? { hard: r.hard } : {}),
        };
      } else if (diffChip !== "all") {
        anyBandConstraint = true;
        by_qtype_band[id] = { [diffChip]: r.need };
      }
    }
    // 易/中/难均为 0 且选「全部难度」：不传难度系数，按库内随机抽题
    const useCoef = diffChip === "all" && anyBandConstraint;
    return {
      by_qtype,
      ...(Object.keys(by_qtype_band).length ? { by_qtype_band } : {}),
      ...(selectedTags.length ? { knowledge_tags_any: selectedTags } : {}),
      ...(selectedChapters.length ? { chapters_any: selectedChapters } : {}),
      ...(yearsAny.length ? { years_any: yearsAny } : {}),
      ...(useCoef ? { difficulty_target_coef: difficultyCoef } : {}),
      require_complete: requireComplete,
      soft_fallback: true,
      seed: 42,
    };
  };

  const applyAssembleResult = (body: {
    paper_id: string;
    title?: string;
    markdown?: string;
    questions?: ExamQuestion[];
    question_ids?: string[];
  }) => {
    setPaperId(body.paper_id);
    setMarkdown(body.markdown || "");
    setLessonMd("");
    const qs = body.questions || [];
    setPoolQuestions(qs);
    setBasketIds(qs.map((q) => q.id));
    setPreviewMode("cards");
    // 异步补全来源卷标题
    for (const q of qs) {
      const spid = q.source_paper_id;
      if (!spid || sourceTitles[spid]) continue;
      void fetchExamSourcePaper(spid)
        .then((sp) => {
          setSourceTitles((prev) => ({ ...prev, [spid]: sp.title || sp.source_filename || spid }));
        })
        .catch(() => undefined);
    }
  };

  const openSwap = async (q: ExamQuestion) => {
    if (!collectionId) return;
    setSwapBusyId(q.id);
    setSwapForId(q.id);
    setSwapCands([]);
    setError("");
    try {
      const res = await swapExamQuestion({
        collection_id: collectionId,
        question_id: q.id,
        exclude_ids: poolQuestions.map((x) => x.id),
        limit: 8,
        soft_fallback: true,
      });
      setSwapCands(res.candidates || []);
      if (!(res.candidates || []).length) {
        setHint("暂无相似替换题，可放宽章节/知识点后再试");
      } else if (res.fallback_applied) {
        setHint(`换题候选已放宽：${(res.fallback_notes || []).join("；")}`);
      }
    } catch (e) {
      setSwapForId(null);
      setError(formatExamApiError((e as Error).message));
    } finally {
      setSwapBusyId(null);
    }
  };

  const applySwapCandidate = (cand: ExamQuestion) => {
    if (!swapForId) return;
    const oldId = swapForId;
    setPoolQuestions((prev) => prev.map((q) => (q.id === oldId ? cand : q)));
    setBasketIds((prev) => {
      if (!prev.includes(oldId)) return prev;
      return prev.map((id) => (id === oldId ? cand.id : id));
    });
    setSwapForId(null);
    setSwapCands([]);
    setHint("已替换题目；定稿导出前请再点「去组卷并导出」");
  };

  const assemble = useMutation({
    mutationFn: async () => {
      setHint("正在按设置智能抽题（条件过严时自动放宽）…");
      const body = await autoGenerateExamPaper({
        collection_id: collectionId,
        title,
        include_answers: includeAnswers,
        spec: buildSpec(),
      });
      return body;
    },
    onSuccess: (body) => {
      const notes = (body as { fallback_notes?: string[] }).fallback_notes || [];
      setHint(
        notes.length
          ? `已抽题（智能兜底：${notes.join("；")}）`
          : "已生成候选题，可在题卡中调整试题篮后导出",
      );
      setError("");
      applyAssembleResult(body);
    },
    onError: (e: Error) => {
      setHint("");
      setError(formatExamApiError(e.message));
    },
  });

  const assembleNl = useMutation({
    mutationFn: async () => {
      if (!collectionId) {
        throw new Error("请先选择题库（页面上方「题库」下拉）");
      }
      setHint("正在理解需求并组卷…");
      const body = await assembleExamPaperNl({
        collection_id: collectionId,
        text: nlText,
        title,
        include_answers: includeAnswers,
      });
      // 按钮文案含「导出」：组卷成功后立即下载所选格式
      await downloadExamPaperExport(body.paper_id, exportFormat, {
        includeAnswers,
        fallbackFilename: `${body.title || title || "试卷"}.${exportFormat === "markdown" ? "md" : exportFormat}`,
      });
      return body;
    },
    onSuccess: (body) => {
      setHint(
        `${body.nl_message || "已生成试卷"} · 已下载 ${exportFormat.toUpperCase()}`,
      );
      setError("");
      if (body.title) setTitle(body.title);
      applyAssembleResult(body);
    },
    onError: (e: Error) => {
      setHint("");
      setError(formatExamApiError(e.message));
    },
  });

  const finalizeBasket = useMutation({
    mutationFn: async () => {
      setHint("正在按试题篮定稿并导出…");
      const body = await finalizeExamBasket({
        collection_id: collectionId,
        title,
        question_ids: basketIds,
        include_answers: includeAnswers,
      });
      await downloadExamPaperExport(body.paper_id, exportFormat, {
        includeAnswers,
        fallbackFilename: `${title || "试卷"}.${exportFormat === "markdown" ? "md" : exportFormat}`,
      });
      return body;
    },
    onSuccess: (body) => {
      setHint("已按试题篮导出");
      setError("");
      setPaperId(body.paper_id);
      setMarkdown(body.markdown || "");
    },
    onError: (e: Error) => {
      setHint("");
      setError(formatExamApiError(e.message));
    },
  });

  const redownload = useMutation({
    mutationFn: () =>
      downloadExamPaperExport(paperId, exportFormat, {
        includeAnswers,
        fallbackFilename: `${title || "试卷"}.${exportFormat === "markdown" ? "md" : exportFormat}`,
      }),
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const lessonMut = useMutation({
    mutationFn: () => generateExamLesson(paperId),
    onSuccess: (body) => {
      setLessonMd(body.markdown || "");
      setError("");
    },
    onError: (e: Error) => setError(formatExamApiError(e.message)),
  });

  const setRow = (id: string, patch: Partial<RowSpec>) => {
    setRows((s) => ({ ...s, [id]: { ...(s[id] || { need: 0, easy: 0, mid: 0, hard: 0 }), ...patch } }));
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const toggleChapter = (chapter: string) => {
    setSelectedChapters((prev) =>
      prev.includes(chapter) ? prev.filter((c) => c !== chapter) : [...prev, chapter],
    );
  };

  const clearScope = () => {
    setSelectedTags([]);
    setSelectedChapters([]);
  };

  const saveTemplate = () => {
    const payload: SavedTemplate = {
      scenario,
      diffChip,
      region,
      yearPreset,
      yearPick,
      selectedTags,
      selectedChapters,
      leftTab,
      rows,
      title,
      exportFormat,
      includeAnswers,
    };
    localStorage.setItem(`${TEMPLATE_KEY}:${userId || "anon"}`, JSON.stringify(payload));
    setHint("已存为本地模板");
  };

  const loadTemplate = () => {
    try {
      const raw = localStorage.getItem(`${TEMPLATE_KEY}:${userId || "anon"}`);
      if (!raw) {
        setError("暂无已存模板");
        return;
      }
      const t = JSON.parse(raw) as SavedTemplate & { year?: string };
      setScenario(t.scenario || "stage");
      setDiffChip(t.diffChip || "all");
      setRegion(t.region || "");
      if (t.yearPreset) {
        setYearPreset(t.yearPreset);
        setYearPick(t.yearPick || "");
      } else if (t.year) {
        setYearPreset("pick");
        setYearPick(t.year);
      } else {
        setYearPreset("all");
        setYearPick("");
      }
      setSelectedTags(t.selectedTags || []);
      setSelectedChapters(t.selectedChapters || []);
      if (t.leftTab) setLeftTab(t.leftTab);
      if (t.rows) setRows(t.rows);
      if (t.title) setTitle(t.title);
      if (t.exportFormat) setExportFormat(t.exportFormat);
      setIncludeAnswers(t.includeAnswers !== false);
      setError("");
      setHint("已加载本地模板");
    } catch {
      setError("模板读取失败");
    }
  };

  const canGenerate =
    Boolean(collectionId) &&
    validation.length === 0 &&
    Object.values(rows).some((r) => r.need > 0) &&
    !assemble.isPending;

  return (
    <ExamWizardChrome title="智能组卷" wide>
      {error ? (
        <p className="text-sm text-warning whitespace-pre-wrap rounded-xl border-2 border-warning/40 bg-warning/5 px-3 py-2">
          {error}
        </p>
      ) : null}
      {hint ? <p className="text-sm text-brand text-center">{hint}</p> : null}

      <div className="grid gap-5 xl:grid-cols-[300px_minmax(520px,1.2fr)_minmax(420px,1fr)] items-start pb-24">
        {/* 左：章节 / 知识点（图二） */}
        <aside className="rounded-xl border-2 border-border bg-surface p-4 shadow-sm space-y-3 xl:sticky xl:top-3 xl:max-h-[calc(100vh-7rem)] xl:overflow-hidden flex flex-col">
          <div className="flex rounded-lg border-2 border-border overflow-hidden text-sm shrink-0">
            {(
              [
                { id: "chapter" as const, label: "章节" },
                { id: "tag" as const, label: "知识点" },
              ] as const
            ).map((t) => (
              <button
                key={t.id}
                type="button"
                className={`flex-1 py-2 font-medium ${
                  leftTab === t.id ? "bg-brand text-white" : "bg-surface text-text-muted hover:text-text"
                }`}
                onClick={() => setLeftTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between shrink-0">
            <p className="text-sm font-medium text-text">
              {leftTab === "chapter" ? "章节目录" : "知识点列表"}
            </p>
            <button
              type="button"
              className="text-xs text-text-muted hover:text-brand"
              onClick={clearScope}
            >
              清空
            </button>
          </div>
          {!collectionId ? (
            <p className="text-xs text-text-muted">请先选择题库</p>
          ) : leftTab === "chapter" ? (
            chapterRows.length === 0 ? (
              <p className="text-xs text-text-muted">
                暂无章节（入库拆题写入 chapter 后出现）
              </p>
            ) : (
              <ul className="flex-1 min-h-[280px] max-h-[62vh] overflow-auto space-y-1.5 pr-0.5">
                {chapterRows.map((row) => {
                  const checked = selectedChapters.includes(row.chapter);
                  return (
                    <li key={row.chapter}>
                      <label
                        className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-2 text-sm ${
                          checked
                            ? "border-brand bg-brand/10 text-brand"
                            : "border-border text-text"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="accent-brand"
                          checked={checked}
                          onChange={() => toggleChapter(row.chapter)}
                        />
                        <span className="flex-1 truncate">{row.chapter}</span>
                        <span className="text-text-muted text-xs">{row.count}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )
          ) : tagRows.length === 0 ? (
            <p className="text-xs text-text-muted">本题库暂无知识点标签（入库拆题后自动生成）</p>
          ) : (
            <ul className="flex-1 min-h-[280px] max-h-[62vh] overflow-auto space-y-1.5 pr-0.5">
              {tagRows.map((row) => {
                const checked = selectedTags.includes(row.tag);
                return (
                  <li key={row.tag}>
                    <label
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-2 text-sm ${
                        checked ? "border-brand bg-brand/10 text-brand" : "border-border text-text"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="accent-brand"
                        checked={checked}
                        onChange={() => toggleTag(row.tag)}
                      />
                      <span className="flex-1 truncate">{row.tag}</span>
                      <span className="text-text-muted text-xs">{row.count}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="text-[11px] text-text-muted shrink-0 pt-1 border-t border-border/60">
            {invQ.data?.filter_applied
              ? `筛选后 ${invQ.data?.total ?? "…"} / 全库 ${invQ.data?.total_all ?? "…"} 题`
              : `库存 ${invQ.data?.total ?? "…"} 题`}
            {(invQ.data?.by_qtype_labeled || [])
              .slice(0, 4)
              .map((x) => ` · ${x.label}${x.count}`)
              .join("")}
          </p>
        </aside>

        {/* 中：01/02/03（可折叠） */}
        <section className="space-y-4">
          <div className="rounded-xl border-2 border-border bg-surface p-5 shadow-sm">
            <StepHeading
              n="01"
              title={leftTab === "chapter" ? "选择章节" : "选择知识点"}
              open={open01}
              onToggle={() => setOpen01((v) => !v)}
              action={
                <button
                  type="button"
                  className="text-xs text-text-muted hover:text-brand"
                  onClick={clearScope}
                >
                  清空
                </button>
              }
            />
            {open01 ? (
              <>
                <p className="text-xs text-text-muted mb-2">（从左侧勾选{leftTab === "chapter" ? "章节" : "知识点"}）</p>
                <ExamField label="题库">
                  <select
                    className={examControlClass}
                    value={collectionId}
                    onChange={(e) => {
                      setCollectionId(e.target.value);
                      setSelectedTags([]);
                      setSelectedChapters([]);
                      setRegion("");
                      setYearPreset("all");
                      setYearPick("");
                      setMarkdown("");
                      setPaperId("");
                      setLessonMd("");
                      setPoolQuestions([]);
                      setBasketIds([]);
                    }}
                  >
                    <option value="">请选择</option>
                    {(colsQ.data?.items || []).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.region || "?"} · {c.subject} · {c.grade}
                      </option>
                    ))}
                  </select>
                </ExamField>
                {selectedChapters.length > 0 || selectedTags.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {selectedChapters.map((c) => (
                      <button
                        key={`ch-${c}`}
                        type="button"
                        className="rounded-full border border-brand/40 bg-brand/10 px-2.5 py-0.5 text-xs text-brand"
                        onClick={() => toggleChapter(c)}
                        title="点击移除"
                      >
                        章·{c} ×
                      </button>
                    ))}
                    {selectedTags.map((t) => (
                      <button
                        key={`tg-${t}`}
                        type="button"
                        className="rounded-full border border-brand/40 bg-brand/10 px-2.5 py-0.5 text-xs text-brand"
                        onClick={() => toggleTag(t)}
                        title="点击移除"
                      >
                        {t} ×
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-text-muted">
                    请从左侧勾选；未选 = 不限章节/知识点
                  </p>
                )}
              </>
            ) : null}
          </div>

          <div className="rounded-xl border-2 border-border bg-surface p-5 shadow-sm space-y-4">
            <StepHeading
              n="02"
              title="组卷设置"
              open={open02}
              onToggle={() => setOpen02((v) => !v)}
            />
            {open02 ? (
              <>
            <div>
              <p className="text-xs font-medium text-text-muted mb-1.5">出题场景</p>
              <div className="flex flex-wrap gap-2 items-center">
                {SCENARIOS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className={`rounded-lg border-2 px-3 py-1.5 text-sm ${
                      scenario === s.id
                        ? "border-brand bg-brand/10 text-brand"
                        : "border-border text-text"
                    }`}
                    onClick={() => setScenario(s.id)}
                  >
                    {s.label}
                  </button>
                ))}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={!collectionId || !qtypes.length}
                  onClick={applyScenarioDefaults}
                >
                  填入建议题量
                </Button>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(240px,280px)] items-start">
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium text-text-muted mb-1.5">题目难度</p>
                  <div className="flex flex-wrap gap-2">
                    {DIFF_CHIPS.map((d) => (
                      <button
                        key={d.id}
                        type="button"
                        className={`rounded-lg border-2 px-3 py-1.5 text-sm ${
                          diffChip === d.id
                            ? "border-brand bg-brand/10 text-brand"
                            : "border-border text-text"
                        }`}
                        onClick={() => {
                          if (d.id === "all") setDiffChip("all");
                          else applyPaperDiffMode(d.id);
                        }}
                      >
                        {d.label}
                      </button>
                    ))}
                  </div>
                  {diffChip === "all" ? (
                    <div className="mt-3 space-y-1">
                      <p className="text-[11px] text-text-muted leading-relaxed">
                        易/中/难均填 0 时从库内随机抽题（不套用下方难度系数）；题量不足时自动按库内实际题量出卷。
                      </p>
                      <div className="flex justify-between text-xs text-text-muted">
                        <span>难度系数（填写易/中/难配比后才参与过滤；越高越易）</span>
                        <span className="text-brand">
                          {difficultyCoef.toFixed(2)} · 预估均分 ≈{" "}
                          {Math.round(difficultyCoef * 100)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0.28}
                        max={0.95}
                        step={0.01}
                        value={difficultyCoef}
                        onChange={(e) => setDifficultyCoef(Number(e.target.value))}
                        className="w-full accent-brand"
                      />
                    </div>
                  ) : null}
                  <p className="mt-1 text-[11px] text-text-muted">
                    点右侧配比表或难度芯片，可按试卷难度自动拆分各题型易/中/难道数
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <ExamField label="题库地区（锁定）">
                    <input
                      className={examControlClass}
                      value={lockedRegion || "请先选择题库"}
                      readOnly
                      disabled
                    />
                  </ExamField>
                  <div>
                    <p className="text-xs font-medium text-text-muted mb-1.5">优先年份</p>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {(
                        [
                          { id: "all" as const, label: "全部" },
                          { id: "y3" as const, label: "近3年" },
                          { id: "y5" as const, label: "近5年" },
                          { id: "pick" as const, label: "指定" },
                        ] as const
                      ).map((y) => (
                        <button
                          key={y.id}
                          type="button"
                          className={`rounded-lg border-2 px-2.5 py-1 text-xs ${
                            yearPreset === y.id
                              ? "border-brand bg-brand/10 text-brand"
                              : "border-border text-text"
                          }`}
                          onClick={() => setYearPreset(y.id)}
                        >
                          {y.label}
                        </button>
                      ))}
                    </div>
                    {yearPreset === "pick" ? (
                      <select
                        className={examControlClass}
                        value={yearPick}
                        onChange={(e) => setYearPick(e.target.value)}
                      >
                        <option value="">选择年份</option>
                        {inventoryYears.map((y) => (
                          <option key={y} value={y}>
                            {y}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </div>
                </div>
                <ExamField label="试卷标题">
                  <input
                    className={examControlClass}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </ExamField>
              </div>
              <ExamDiffProportionCard active={diffChip} onSelect={applyPaperDiffMode} />
            </div>
              </>
            ) : null}
          </div>

          <div className="rounded-xl border-2 border-border bg-surface p-5 shadow-sm space-y-3">
            <StepHeading
              n="03"
              title="试题设置"
              open={open03}
              onToggle={() => setOpen03((v) => !v)}
              action={
                invQ.data?.filter_applied ? (
                  <span className="text-[11px] text-brand">库内按当前筛选统计</span>
                ) : null
              }
            />
            {open03 ? (
              <>
            {collectionId && qtypes.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {qtypes.map((t) => {
                  const r = rows[t.id] || { need: 0, easy: 0, mid: 0, hard: 0 };
                  const stock = invQ.data?.by_qtype?.[t.id] ?? 0;
                  return (
                    <div
                      key={t.id}
                      className="rounded-lg border-2 border-border px-3 py-2.5 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-text">{t.label}</span>
                        <span className="text-xs text-text-muted">库内 {stock}</span>
                      </div>
                      <label className="flex items-center justify-between gap-2 text-xs text-text-muted">
                        需要道数
                        <input
                          type="number"
                          min={0}
                          className="w-20 rounded-lg border-2 border-border bg-surface px-2 py-1 text-center text-sm text-text outline-none focus:border-brand"
                          value={r.need}
                          onChange={(e) => setRow(t.id, { need: Number(e.target.value) })}
                        />
                      </label>
                      <div className="grid grid-cols-3 gap-1">
                        {(["easy", "mid", "hard"] as const).map((k) => (
                          <label key={k} className="text-[10px] text-text-muted text-center space-y-0.5">
                            {k === "easy" ? "易" : k === "mid" ? "中" : "难"}
                            <input
                              type="number"
                              min={0}
                              className="w-full rounded border-2 border-border px-1 py-0.5 text-center text-xs"
                              value={r[k]}
                              onChange={(e) => setRow(t.id, { [k]: Number(e.target.value) })}
                            />
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-text-muted">选择题库后显示该科目题型包</p>
            )}

            <fieldset className="space-y-2 pt-2 border-t border-border">
              <legend className="text-xs font-medium text-text-muted">导出格式</legend>
              <p className="text-[11px] text-text-muted">
                默认 Word（国标 OMML）：公式可编辑，比 PDF 更少损坏版式
              </p>
              <div className="grid grid-cols-3 gap-2">
                {formatOptions.map((o) => (
                  <label
                    key={o.id}
                    className={`flex cursor-pointer items-center justify-center rounded-lg border-2 px-2 py-2.5 text-xs ${
                      exportFormat === o.id
                        ? "border-brand bg-brand/10 text-brand"
                        : "border-border text-text"
                    }`}
                  >
                    <input
                      type="radio"
                      name="export-format"
                      className="sr-only"
                      checked={exportFormat === o.id}
                      onChange={() => setExportFormat(o.id)}
                    />
                    {o.label}
                  </label>
                ))}
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-text cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brand"
                  checked={includeAnswers}
                  onChange={(e) => setIncludeAnswers(e.target.checked)}
                />
                包含答案与解析
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-text cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-brand"
                  checked={requireComplete}
                  onChange={(e) => setRequireComplete(e.target.checked)}
                />
                仅用完整题（排除缺选项/答案）
              </label>
            </fieldset>
              </>
            ) : null}
          </div>

          {validation.length > 0 ? (
            <ul className="text-sm text-warning list-disc pl-5">
              {validation.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          ) : null}

          <div className="rounded-xl border border-dashed border-border px-3 py-2">
            <button
              type="button"
              className="text-xs text-brand hover:underline"
              onClick={() => setNlOpen((v) => !v)}
            >
              {nlOpen ? "收起一句话组卷" : "一句话组卷（快捷）"}
            </button>
            {nlOpen ? (
              <div className="mt-2 space-y-2">
                <textarea
                  className={`${examControlClass} min-h-[64px] resize-y`}
                  value={nlText}
                  onChange={(e) => setNlText(e.target.value)}
                />
                {!collectionId ? (
                  <p className="text-[11px] text-warning">请先在上方选择题库，否则无法组卷导出</p>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  variant="primary"
                  disabled={!nlText.trim() || assembleNl.isPending}
                  onClick={() => {
                    if (!collectionId) {
                      setError("请先选择题库（页面上方「题库」下拉）");
                      return;
                    }
                    assembleNl.mutate();
                  }}
                >
                  {assembleNl.isPending ? "组卷导出中…" : "一句话组卷并导出"}
                </Button>
                <p className="text-[11px] text-text-muted">
                  将按当前导出格式（{exportFormat.toUpperCase()}）下载；组卷后右侧会出现题卡
                </p>
              </div>
            ) : null}
          </div>

          <p className="text-xs text-text-muted text-center">
            没有题库？先去{" "}
            <Link to="/admin/exam-bank/ingest?step=1" className="text-brand hover:underline">
              试卷入库
            </Link>
          </p>
        </section>

        {/* 右：题卡 + 试题篮 */}
        <aside className="xl:sticky xl:top-3 space-y-4 min-h-[360px]">
          <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_240px] items-start">
            <div className="rounded-xl border-2 border-border bg-surface p-4 shadow-sm space-y-3 min-h-[420px]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-text">
                  {previewMode === "cards" ? "候选题卡" : "卷面预览"}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    className={`rounded-md border px-2 py-1 text-xs ${
                      previewMode === "cards" ? "border-brand text-brand" : "border-border"
                    }`}
                    onClick={() => setPreviewMode("cards")}
                  >
                    题卡
                  </button>
                  <button
                    type="button"
                    className={`rounded-md border px-2 py-1 text-xs ${
                      previewMode === "paper" ? "border-brand text-brand" : "border-border"
                    }`}
                    onClick={() => setPreviewMode("paper")}
                    disabled={!(basketQuestions.length || poolQuestions.length)}
                  >
                    卷面
                  </button>
                  {(previewMode === "cards"
                    ? poolQuestions.length > 0
                    : basketQuestions.length + poolQuestions.length > 0) ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => setPaperFullscreen(true)}
                    >
                      放大
                    </Button>
                  ) : null}
                  {paperId ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="default"
                      disabled={redownload.isPending}
                      onClick={() => redownload.mutate()}
                    >
                      {redownload.isPending ? "下载中…" : "下载"}
                    </Button>
                  ) : null}
                  {paperId ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={lessonMut.isPending}
                      onClick={() => lessonMut.mutate()}
                    >
                      {lessonMut.isPending ? "生成中…" : "教案"}
                    </Button>
                  ) : null}
                </div>
              </div>

              {previewMode === "cards" ? (
                poolQuestions.length ? (
                  <div className="space-y-3 max-h-[min(72vh,780px)] overflow-auto pr-1">
                    <ExamAssembleDashboard
                      questions={basketQuestions.length ? basketQuestions : poolQuestions}
                      qtypeLabel={qtypeLabelFn}
                    />
                    <div className="flex justify-end">
                      <button
                        type="button"
                        className="text-xs text-brand hover:underline"
                        onClick={() => setBasketIds(poolQuestions.map((q) => q.id))}
                      >
                        全部加入试题篮
                      </button>
                    </div>
                    {poolQuestions.map((q, i) => (
                      <ExamQuestionCard
                        key={q.id}
                        q={q}
                        index={i}
                        qtypeLabel={qtypeLabelFn}
                        inBasket={basketIds.includes(q.id)}
                        onToggleBasket={() =>
                          setBasketIds((prev) =>
                            prev.includes(q.id)
                              ? prev.filter((id) => id !== q.id)
                              : [...prev, q.id],
                          )
                        }
                        onSwap={() => void openSwap(q)}
                        swapBusy={swapBusyId === q.id}
                        sourceTitle={
                          q.source_paper_id ? sourceTitles[q.source_paper_id] : undefined
                        }
                        onOpenSource={() => {
                          if (!q.source_paper_id) return;
                          void fetchExamSourcePaper(q.source_paper_id)
                            .then((sp) => {
                              setSourceTitles((prev) => ({
                                ...prev,
                                [q.source_paper_id!]: sp.title || sp.source_filename || sp.id,
                              }));
                              setSourceModal(sp);
                            })
                            .catch((e: Error) => setError(formatExamApiError(e.message)));
                        }}
                        onEdit={() => setEditQuestion(q)}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-text-muted text-center py-16 px-4">
                    设置题型题量后点「一键抽题入篮」。也可之后在题卡中加减试题篮，再「去组卷并导出」。
                  </p>
                )
              ) : poolQuestions.length || basketQuestions.length ? (
                <div
                  className="rounded-sm border border-border bg-[#faf9f6] text-[#1a1a1a] max-h-[min(72vh,780px)] overflow-auto"
                >
                  <ExamPaperBody
                    title={title}
                    questions={basketQuestions.length ? basketQuestions : poolQuestions}
                    includeAnswers={includeAnswers}
                  />
                </div>
              ) : (
                <p className="text-xs text-text-muted text-center py-16">暂无卷面</p>
              )}

              {lessonMd ? (
                <div className="space-y-1">
                  <p className="text-xs text-text-muted">教案大纲</p>
                  <pre className="whitespace-pre-wrap text-xs rounded-lg border border-border bg-surface-muted/40 p-3 max-h-[200px] overflow-auto">
                    {lessonMd}
                  </pre>
                </div>
              ) : null}
            </div>

            <ExamBasketPanel
              items={basketQuestions}
              qtypeLabel={qtypeLabelFn}
              onRemove={(id) => setBasketIds((prev) => prev.filter((x) => x !== id))}
              onClear={() => setBasketIds([])}
              onFinalize={() => finalizeBasket.mutate()}
              finalizeBusy={finalizeBasket.isPending}
              totalInPool={poolQuestions.length}
            />
          </div>
        </aside>
      </div>

      {/* 图二：底部固定操作条 */}
      <div className="fixed bottom-0 inset-x-0 z-40 border-t-2 border-border bg-surface/95 backdrop-blur-sm shadow-[0_-4px_24px_rgba(0,0,0,0.06)]">
        <div className="mx-auto max-w-[1680px] px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-text-muted">
            {basketQuestions.length
              ? `试题篮 ${basketQuestions.length} 题 · 可继续调设置后重新抽题`
              : "勾选章节/知识点 → 设题量 → 生成试卷"}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" size="sm" variant="ghost" onClick={loadTemplate}>
              加载模板
            </Button>
            <Button type="button" size="sm" variant="default" onClick={saveTemplate}>
              存为模板
            </Button>
            <Button
              type="button"
              size="sm"
              variant="primary"
              disabled={!canGenerate}
              onClick={() => assemble.mutate()}
            >
              {assemble.isPending ? "抽题中…" : "生成试卷"}
            </Button>
          </div>
        </div>
      </div>

      {paperFullscreen ? (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-[#faf9f6] w-full max-w-5xl max-h-[92vh] overflow-auto rounded-lg shadow-xl relative">
            <div className="sticky top-0 z-10 flex items-center justify-between gap-2 bg-[#faf9f6]/95 border-b px-3 py-2">
              <p className="text-sm font-medium text-text">
                {previewMode === "cards" ? "题卡放大" : "卷面放大"}
              </p>
              <button
                type="button"
                className="rounded-md bg-white border px-3 py-1 text-sm"
                onClick={() => setPaperFullscreen(false)}
              >
                关闭
              </button>
            </div>
            {previewMode === "cards" ? (
              <div className="space-y-3 px-4 py-4">
                {poolQuestions.map((q, i) => (
                  <ExamQuestionCard
                    key={q.id}
                    q={q}
                    index={i}
                    qtypeLabel={qtypeLabelFn}
                    inBasket={basketIds.includes(q.id)}
                    onToggleBasket={() =>
                      setBasketIds((prev) =>
                        prev.includes(q.id)
                          ? prev.filter((id) => id !== q.id)
                          : [...prev, q.id],
                      )
                    }
                    onSwap={() => void openSwap(q)}
                    swapBusy={swapBusyId === q.id}
                    sourceTitle={q.source_paper_id ? sourceTitles[q.source_paper_id] : undefined}
                    onOpenSource={() => {
                      if (!q.source_paper_id) return;
                      void fetchExamSourcePaper(q.source_paper_id)
                        .then((sp) => {
                          setSourceTitles((prev) => ({
                            ...prev,
                            [q.source_paper_id!]: sp.title || sp.source_filename || sp.id,
                          }));
                          setSourceModal(sp);
                        })
                        .catch((e: Error) => setError(formatExamApiError(e.message)));
                    }}
                    onEdit={() => setEditQuestion(q)}
                  />
                ))}
              </div>
            ) : (
              <ExamPaperBody
                title={title}
                questions={basketQuestions.length ? basketQuestions : poolQuestions}
                includeAnswers={includeAnswers}
              />
            )}
          </div>
        </div>
      ) : null}

      {sourceModal ? (
        <div
          className="fixed inset-0 z-[55] bg-black/40 flex items-center justify-center p-4"
          onClick={() => setSourceModal(null)}
        >
          <div
            className="bg-surface w-full max-w-3xl max-h-[85vh] overflow-auto rounded-xl border-2 border-border shadow-xl p-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-text">
                  原卷 · {sourceModal.title || sourceModal.source_filename || sourceModal.id}
                </h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  {sourceModal.source_filename || "无文件名"}
                  {sourceModal.media_ingest_id
                    ? ` · 公式媒体 ${sourceModal.media_ingest_id}`
                    : ""}
                </p>
              </div>
              <button
                type="button"
                className="rounded-md border px-2.5 py-1 text-xs"
                onClick={() => setSourceModal(null)}
              >
                关闭
              </button>
            </div>
            <pre className="whitespace-pre-wrap text-xs leading-5 rounded-md border border-border bg-surface-muted/40 px-3 py-3 max-h-[60vh] overflow-auto">
              {collapseSpacedCjk(sourceModal.raw_text || "") || "（无原文文本）"}
            </pre>
          </div>
        </div>
      ) : null}

      <ExamQuestionEditDrawer
        question={editQuestion}
        qtypeLabel={qtypeLabelFn}
        onClose={() => setEditQuestion(null)}
        onSaved={(updated) => {
          setPoolQuestions((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
          setHint("题目已保存");
        }}
      />

      {swapForId ? (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-surface w-full max-w-2xl max-h-[85vh] overflow-auto rounded-xl border-2 border-border shadow-xl p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-text">智能换题 · 选择替换题</h3>
              <button
                type="button"
                className="rounded-md border px-2.5 py-1 text-xs"
                onClick={() => {
                  setSwapForId(null);
                  setSwapCands([]);
                }}
              >
                关闭
              </button>
            </div>
            {swapBusyId === swapForId && !swapCands.length ? (
              <p className="text-xs text-text-muted py-8 text-center">正在检索相似题…</p>
            ) : swapCands.length ? (
              <ul className="space-y-2">
                {swapCands.map((c) => (
                  <li
                    key={c.id}
                    className="rounded-lg border border-border px-3 py-2 space-y-2 hover:border-brand/40"
                  >
                    <div className="text-xs text-text-muted">
                      {qtypeLabelFn(c.qtype)} · 难度 {c.difficulty}
                      {c.chapter ? ` · ${c.chapter}` : ""}
                    </div>
                    <div className="text-sm text-text leading-relaxed">
                      <ExamMathText text={c.stem} mediaIngestId={c.media_ingest_id} />
                    </div>
                    <button
                      type="button"
                      className="rounded-md border-2 border-brand bg-brand text-white px-3 py-1 text-xs font-medium"
                      onClick={() => applySwapCandidate(c)}
                    >
                      用这题替换
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-text-muted py-8 text-center">没有找到可替换题目</p>
            )}
          </div>
        </div>
      ) : null}
    </ExamWizardChrome>
  );
}
