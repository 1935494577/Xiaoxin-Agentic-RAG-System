import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { ExamQuestion } from "../../../lib/examBank";

function coefOf(q: ExamQuestion): number {
  if (typeof q.difficulty_coef === "number" && q.difficulty_coef > 0) return q.difficulty_coef;
  const d = Number(q.difficulty || 3);
  const map: Record<number, number> = { 1: 0.92, 2: 0.85, 3: 0.65, 4: 0.45, 5: 0.28 };
  return map[d] ?? 0.65;
}

/** 预估均分：ease 越高分越高，粗算 100 * mean(coef) */
export function estimateAvgScore(questions: ExamQuestion[]): number {
  if (!questions.length) return 0;
  const m = questions.reduce((s, q) => s + coefOf(q), 0) / questions.length;
  return Math.round(m * 100);
}

export function ExamAssembleDashboard({
  questions,
  qtypeLabel,
}: {
  questions: ExamQuestion[];
  qtypeLabel: (id: string) => string;
}) {
  const avg = estimateAvgScore(questions);

  const radarOpt = useMemo((): EChartsOption => {
    const tagCounts = new Map<string, number>();
    for (const q of questions) {
      for (const t of q.knowledge_tags || []) {
        const k = String(t).trim();
        if (k) tagCounts.set(k, (tagCounts.get(k) || 0) + 1);
      }
    }
    const top = [...tagCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (!top.length) {
      return {
        title: { text: "知识点覆盖", left: "center", textStyle: { fontSize: 12 } },
        graphic: {
          type: "text",
          left: "center",
          top: "middle",
          style: { text: "暂无知识点标签", fill: "#999", fontSize: 12 },
        },
      };
    }
    const max = Math.max(...top.map(([, n]) => n), 1);
    return {
      title: { text: "知识点覆盖", left: "center", textStyle: { fontSize: 12 } },
      tooltip: {},
      radar: {
        indicator: top.map(([name]) => ({ name: name.slice(0, 6), max })),
        radius: "58%",
      },
      series: [
        {
          type: "radar",
          data: [{ value: top.map(([, n]) => n), name: "题量" }],
          areaStyle: { opacity: 0.15 },
        },
      ],
    };
  }, [questions]);

  const diffOpt = useMemo((): EChartsOption => {
    const bands = [
      { key: "易", lo: 1, hi: 2 },
      { key: "中", lo: 3, hi: 3 },
      { key: "难", lo: 4, hi: 5 },
    ];
    const counts = bands.map((b) =>
      questions.filter((q) => {
        const d = Number(q.difficulty || 3);
        return d >= b.lo && d <= b.hi;
      }).length,
    );
    return {
      title: { text: "难度分布", left: "center", textStyle: { fontSize: 12 } },
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: bands.map((b) => b.key) },
      yAxis: { type: "value", minInterval: 1 },
      series: [{ type: "line", data: counts, smooth: true, areaStyle: { opacity: 0.12 } }],
      grid: { left: 36, right: 16, top: 36, bottom: 28 },
    };
  }, [questions]);

  const typeOpt = useMemo((): EChartsOption => {
    const m = new Map<string, number>();
    for (const q of questions) {
      const id = q.qtype || "other";
      m.set(id, (m.get(id) || 0) + 1);
    }
    const rows = [...m.entries()];
    return {
      title: { text: "题型占比", left: "center", textStyle: { fontSize: 12 } },
      tooltip: { trigger: "item" },
      series: [
        {
          type: "pie",
          radius: ["35%", "62%"],
          data: rows.map(([id, v]) => ({ name: qtypeLabel(id), value: v })),
          label: { fontSize: 10 },
        },
      ],
    };
  }, [questions, qtypeLabel]);

  if (!questions.length) {
    return (
      <div className="rounded-xl border-2 border-dashed border-border px-3 py-8 text-center text-xs text-text-muted">
        抽题入篮后显示难度/知识点看板
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-border bg-surface p-3 shadow-sm space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-text">组卷分析</span>
        <span className="text-xs text-brand">预估均分 ≈ {avg}</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <ReactECharts option={radarOpt} style={{ height: 180 }} opts={{ renderer: "canvas" }} />
        <ReactECharts option={diffOpt} style={{ height: 180 }} opts={{ renderer: "canvas" }} />
        <ReactECharts option={typeOpt} style={{ height: 180 }} opts={{ renderer: "canvas" }} />
      </div>
    </div>
  );
}
