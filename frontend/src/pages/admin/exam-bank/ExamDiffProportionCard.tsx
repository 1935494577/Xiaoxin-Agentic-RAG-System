/** 学科网式：试卷难度 × 试题难度配比表（展示用，联动难度芯片） */
export type PaperDiffMode = "all" | "easy" | "mid" | "hard";

const MATRIX: {
  id: Exclude<PaperDiffMode, "all">;
  label: string;
  easy: number;
  mid: number;
  hard: number;
}[] = [
  { id: "easy", label: "容易", easy: 80, mid: 20, hard: 0 },
  { id: "mid", label: "适中", easy: 20, mid: 60, hard: 20 },
  { id: "hard", label: "困难", easy: 0, mid: 20, hard: 80 },
];

const LEGEND = [
  { label: "容易", range: "1.0 ≥ 容易 > 0.8" },
  { label: "适中", range: "0.8 ≥ 适中 ≥ 0.4" },
  { label: "困难", range: "0.4 > 困难 ≥ 0.0" },
];

export function ExamDiffProportionCard({
  active,
  onSelect,
}: {
  active: PaperDiffMode;
  onSelect?: (mode: Exclude<PaperDiffMode, "all">) => void;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-muted/30 p-3 text-xs space-y-2 min-w-[220px]">
      <p className="font-medium text-text">难度分布参考</p>
      <table className="w-full border-collapse text-center">
        <thead>
          <tr className="text-text-muted">
            <th className="py-1 px-1 font-normal text-left">试卷难度</th>
            <th className="py-1 px-1 font-normal">容易题</th>
            <th className="py-1 px-1 font-normal">适中题</th>
            <th className="py-1 px-1 font-normal">困难题</th>
          </tr>
        </thead>
        <tbody>
          {MATRIX.map((row) => {
            const on = active === row.id;
            return (
              <tr
                key={row.id}
                className={`cursor-pointer border-t border-border/60 ${
                  on ? "bg-brand/10 text-brand font-medium" : "text-text hover:bg-surface-muted/60"
                }`}
                onClick={() => onSelect?.(row.id)}
              >
                <td className="py-1.5 px-1 text-left">{row.label}</td>
                <td className="py-1.5 px-1">{row.easy}%</td>
                <td className="py-1.5 px-1">{row.mid}%</td>
                <td className="py-1.5 px-1">{row.hard}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ul className="space-y-0.5 text-[10px] text-text-muted border-t border-border/60 pt-2">
        {LEGEND.map((l) => (
          <li key={l.label}>
            <span className="text-text">{l.label}</span>：{l.range}
          </li>
        ))}
      </ul>
      {active === "all" ? (
        <p className="text-[10px] text-text-muted">当前为「全部」：用滑块控难度系数，或点上表行切换试卷难度</p>
      ) : null}
    </div>
  );
}

/** 按试卷难度行，把 need 拆成 easy/mid/hard（四舍五入，保证合计 = need） */
export function splitNeedByPaperDiff(
  need: number,
  mode: Exclude<PaperDiffMode, "all">,
): { easy: number; mid: number; hard: number } {
  const row = MATRIX.find((m) => m.id === mode)!;
  if (need <= 0) return { easy: 0, mid: 0, hard: 0 };
  let easy = Math.round((need * row.easy) / 100);
  let mid = Math.round((need * row.mid) / 100);
  let hard = need - easy - mid;
  if (hard < 0) {
    mid += hard;
    hard = 0;
  }
  // 修正舍入导致 mid 为负
  if (mid < 0) {
    easy += mid;
    mid = 0;
  }
  const sum = easy + mid + hard;
  if (sum !== need) hard += need - sum;
  return { easy: Math.max(0, easy), mid: Math.max(0, mid), hard: Math.max(0, hard) };
}
