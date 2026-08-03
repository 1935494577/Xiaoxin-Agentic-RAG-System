import { useEffect, useRef, useState, type ReactNode } from "react";

import { TALENT_MASCOTS, type TalentId } from "@/lib/talentMascots";
import { cn } from "@/lib/utils";

type TalentEditorialMascotsProps = {
  isTyping: boolean;
  password: string;
  showPassword: boolean;
};

type Look = { x: number; y: number } | undefined;

type PoseOpts = {
  hiding: boolean;
  revealing: boolean;
  siPeek: boolean;
  watching: boolean;
};

const INK = "#1a1625";
const SKIN = "#FFDFC8";
const SKIN_SHADOW = "#F5C4A8";
const BLUSH = "#FFAB91";
const LIMB = "rgba(255,255,255,0.96)";
const LIMB_W = 5;

function Limb({
  d,
  className,
  w = LIMB_W,
}: {
  d: string;
  className?: string;
  w?: number;
}) {
  return (
    <path
      d={d}
      stroke={LIMB}
      strokeWidth={w}
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
      className={className}
    />
  );
}

function Torso({
  d,
  accent,
}: {
  d: string;
  accent: string;
}) {
  return (
    <path
      d={d}
      fill={accent}
      stroke={INK}
      strokeWidth="2.4"
      strokeLinejoin="round"
    />
  );
}

function useMousePosition() {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => setMouse({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);
  return mouse;
}

function useBlink(min = 2600, max = 5200) {
  const [blinking, setBlinking] = useState(false);
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const schedule = () => {
      timeout = setTimeout(
        () => {
          setBlinking(true);
          setTimeout(() => {
            setBlinking(false);
            schedule();
          }, 140);
        },
        Math.random() * (max - min) + min
      );
    };
    schedule();
    return () => clearTimeout(timeout);
  }, [min, max]);
  return blinking;
}

function MangaEye({
  cx,
  cy,
  w,
  h,
  iris,
  look,
  blink,
  mouse,
  flip,
}: {
  cx: number;
  cy: number;
  w: number;
  h: number;
  iris: string;
  look?: Look;
  blink: boolean;
  mouse: { x: number; y: number };
  flip?: boolean;
}) {
  const ref = useRef<SVGEllipseElement>(null);
  const dir = flip ? -1 : 1;

  const offset = (() => {
    if (look) return { x: look.x * dir, y: look.y };
    if (!ref.current) return { x: 0, y: 0 };
    const rect = ref.current.getBoundingClientRect();
    const dx = mouse.x - (rect.left + rect.width / 2);
    const dy = mouse.y - (rect.top + rect.height / 2);
    const dist = Math.min(Math.hypot(dx, dy), w * 0.35);
    const a = Math.atan2(dy, dx);
    return { x: Math.cos(a) * dist * dir, y: Math.sin(a) * dist * 0.8 };
  })();

  if (blink) {
    return (
      <path
        d={`M${cx - w} ${cy} Q${cx} ${cy + 2} ${cx + w} ${cy}`}
        stroke={INK}
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
      />
    );
  }

  const px = cx + offset.x * 0.5;
  const py = cy + offset.y * 0.5;

  return (
    <g>
      <ellipse ref={ref} cx={cx} cy={cy} rx={w} ry={h} fill="white" stroke={INK} strokeWidth="2" />
      <ellipse cx={px} cy={py} rx={w * 0.55} ry={h * 0.62} fill={iris} />
      <ellipse cx={px} cy={py + h * 0.08} rx={w * 0.28} ry={h * 0.35} fill={INK} />
      <ellipse cx={px - w * 0.22} cy={py - h * 0.28} rx={w * 0.18} ry={h * 0.22} fill="white" />
      <circle cx={px + w * 0.15} cy={py + h * 0.1} r={w * 0.08} fill="white" opacity="0.9" />
    </g>
  );
}

type FigureProps = {
  accent: string;
  accentDark: string;
  look?: Look;
  blink: boolean;
  mouse: { x: number; y: number };
  hideFace?: boolean;
  leanAway?: boolean;
  peek?: boolean;
  watchForm?: boolean;
};

function ChibiHead({
  cx,
  cy,
  r,
  children,
}: {
  cx: number;
  cy: number;
  r: number;
  children?: ReactNode;
}) {
  return (
    <g>
      <circle cx={cx} cy={cy + 2} r={r + 1} fill={INK} opacity="0.12" />
      <circle cx={cx} cy={cy} r={r} fill={SKIN} stroke={INK} strokeWidth="2.4" />
      <ellipse cx={cx - r * 0.45} cy={cy + r * 0.15} rx={r * 0.12} ry={r * 0.07} fill={BLUSH} opacity="0.55" />
      <ellipse cx={cx + r * 0.45} cy={cy + r * 0.15} rx={r * 0.12} ry={r * 0.07} fill={BLUSH} opacity="0.55" />
      {children}
    </g>
  );
}

/** 思者 — 绿 · 沉思踱步 */
function SiMangaFigure({ accent, accentDark, look, blink, leanAway, peek, watchForm, mouse }: FigureProps) {
  const thinkArm = watchForm
    ? "M58 58 L68 52"
    : leanAway
      ? "M58 58 L66 66"
      : "M58 58 L64 46 L56 42";

  return (
    <svg viewBox="0 0 88 132" className="h-full w-full" aria-hidden>
      <g className="talent-manga-thought-si" opacity="0.9">
        <ellipse cx="68" cy="18" rx="12" ry="9" fill="white" stroke={INK} strokeWidth="1.6" />
        <path d="M58 24 L52 30" stroke={INK} strokeWidth="1.4" />
        <text x="62" y="22" fontSize="10" fill={accentDark} fontWeight="bold">
          ?
        </text>
      </g>
      <Limb d="M36 86 L32 112" className="talent-manga-walk-legs-si" />
      <Limb d="M52 86 L56 112" className="talent-manga-walk-legs-si" />
      <Torso d="M28 56 Q44 52 60 56 L56 84 Q44 88 34 84 Z" accent={accent} />
      <Limb d="M30 58 L22 76" />
      <Limb d={thinkArm} className="talent-manga-arm-si" />
      <ChibiHead cx={44} cy={30} r={20}>
        <MangaEye cx={37} cy={28} w={5} h={6} iris={accentDark} look={look ?? { x: 0, y: -2 }} blink={blink} mouse={mouse} />
        <MangaEye cx={51} cy={28} w={5} h={6} iris={accentDark} look={look ?? { x: 0, y: -2 }} blink={blink} mouse={mouse} />
        <path
          d={peek ? "M36 38 Q44 41 52 38" : "M38 38 Q44 36 50 38"}
          stroke={INK}
          strokeWidth="1.8"
          fill="none"
          strokeLinecap="round"
        />
      </ChibiHead>
    </svg>
  );
}

/** 德者 — 棕 · 观察关怀 */
function DeMangaFigure({ accent, accentDark, look, blink, leanAway, mouse }: FigureProps) {
  return (
    <svg viewBox="0 0 88 132" className="h-full w-full" aria-hidden>
      <Limb d="M34 88 L30 112" className="talent-manga-walk-legs-de" />
      <Limb d="M54 88 L58 112" className="talent-manga-walk-legs-de" />
      <Torso d="M26 54 Q44 50 62 54 L58 88 Q44 92 30 88 Z" accent={accent} />
      <path
        d="M44 62 C38 54 30 56 30 64 C30 74 44 80 44 80 C44 80 58 74 58 64 C58 56 50 54 44 62 Z"
        fill="#FFCDD2"
        stroke={INK}
        strokeWidth="1.8"
        className="talent-manga-heart-de"
      />
      <Limb d="M28 56 L20 74" />
      <Limb d="M60 56 L68 46" />
      <g className="talent-manga-scope-de" transform={leanAway ? "translate(4,2)" : undefined}>
        <circle cx="72" cy="42" r="7" fill="white" stroke={accentDark} strokeWidth="1.8" />
        <circle cx="72" cy="42" r="3" fill={accentDark} opacity="0.35" />
        <Limb d="M78 48 L84 56" w={3.5} />
      </g>
      <ChibiHead cx={42} cy={32} r={17}>
        <MangaEye cx={35} cy={30} w={6} h={7} iris={accentDark} look={look} blink={blink} mouse={mouse} />
        <MangaEye cx={49} cy={31} w={4.5} h={5.5} iris={accentDark} look={look ?? { x: 2, y: 0 }} blink={blink} mouse={mouse} flip />
        <path d="M36 40 Q42 42 48 40" stroke={INK} strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </ChibiHead>
    </svg>
  );
}

/** 学者 — 蓝 · 探身学习 */
function XueMangaFigure({ accent, accentDark, look, blink, watchForm, mouse }: FigureProps) {
  return (
    <svg viewBox="0 0 88 132" className="h-full w-full" aria-hidden>
      <Limb d="M36 86 L34 112" className="talent-manga-walk-legs-xue" />
      <Limb d="M52 86 L54 112" className="talent-manga-walk-legs-xue" />
      <g className="talent-manga-torso-xue">
        <Torso d="M30 58 Q44 52 58 58 L54 86 Q44 90 34 86 Z" accent={accent} />
      </g>
      <Limb d="M30 60 L22 78" />
      <Limb
        d={watchForm ? "M58 58 L72 50" : "M58 58 Q66 44 72 36"}
        className="talent-manga-reach-xue"
      />
      <rect x="62" y="58" width="14" height="18" rx="2" fill="white" stroke={INK} strokeWidth="1.8" className="talent-manga-book-xue" />
      <path d="M66 64 H72 M66 68 H70 M66 72 H72" stroke={accentDark} strokeWidth="1.2" strokeLinecap="round" />
      <ChibiHead cx={44} cy={34} r={17}>
        <MangaEye cx={38} cy={32} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
        <MangaEye cx={50} cy={32} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
        <path d="M38 42 Q44 44 50 42" stroke={INK} strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </ChibiHead>
    </svg>
  );
}

/** 行者 — 黄 · 跳跃奔走 */
function XingMangaFigure({ accent, accentDark, look, blink, watchForm, mouse }: FigureProps) {
  return (
    <svg viewBox="0 0 88 132" className="h-full w-full" aria-hidden>
      <g className="talent-manga-fx-xing" opacity="0.75">
        <path d="M6 70 L18 70 M4 80 L16 82" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
      </g>
      <Limb d="M38 82 L26 108" className="talent-manga-leg-xing-back" />
      <Limb d="M50 82 L60 100" className="talent-manga-leg-xing-front" />
      <Torso d="M32 54 Q44 48 56 54 L52 80 Q44 84 36 80 Z" accent={accent} />
      <Limb d="M32 56 L18 64" />
      <Limb d="M56 52 L68 36" />
      <ellipse
        cx="40"
        cy="94"
        rx="12"
        ry="9"
        fill={accent}
        stroke={INK}
        strokeWidth="2"
        className="talent-manga-leap-xing"
      />
      <ChibiHead cx={44} cy={28} r={17}>
        <MangaEye cx={38} cy={26} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
        <MangaEye cx={50} cy={26} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
        <path d={watchForm ? "M38 34 Q44 37 50 34" : "M39 34 Q44 32 49 34"} stroke={INK} strokeWidth="1.8" fill="none" strokeLinecap="round" />
      </ChibiHead>
    </svg>
  );
}

/** 赢者 — 红 · 胜利举臂 */
function YingMangaFigure({ accent, accentDark, look, blink, hideFace, mouse }: FigureProps) {
  return (
    <svg viewBox="0 0 88 132" className="h-full w-full" aria-hidden>
      <text x="62" y="22" fontSize="14" fill={accent} className="talent-manga-star-ying">
        ★
      </text>
      <Limb d="M36 86 L34 112" className="talent-manga-walk-legs-ying" />
      <Limb d="M52 86 L54 112" className="talent-manga-walk-legs-ying" />
      <Torso d="M28 54 Q44 50 60 54 L56 86 Q44 90 32 86 Z" accent={accent} />
      {!hideFace ? (
        <>
          <Limb d="M28 56 Q18 42 16 28" className="talent-manga-flex-ying" w={5.5} />
          <Limb d="M60 56 Q70 42 72 28" className="talent-manga-flex-ying" w={5.5} />
          <ellipse cx="16" cy="28" rx="6" ry="7" fill={SKIN_SHADOW} stroke={INK} strokeWidth="1.8" />
          <ellipse cx="72" cy="28" rx="6" ry="7" fill={SKIN_SHADOW} stroke={INK} strokeWidth="1.8" />
        </>
      ) : (
        <path d="M24 48 Q44 40 64 48" stroke={INK} strokeWidth="2.6" fill={SKIN} />
      )}
      <ChibiHead cx={44} cy={34} r={17}>
        {!hideFace ? (
          <>
            <MangaEye cx={37} cy={32} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
            <MangaEye cx={51} cy={32} w={5} h={6} iris={accentDark} look={look} blink={blink} mouse={mouse} />
            <path d="M36 42 Q44 48 52 42" stroke={INK} strokeWidth="2" fill="none" strokeLinecap="round" />
          </>
        ) : (
          <path d="M32 34 L56 34" stroke={INK} strokeWidth="2.2" strokeLinecap="round" />
        )}
      </ChibiHead>
    </svg>
  );
}

const MANGA_FIGURES = {
  si: SiMangaFigure,
  de: DeMangaFigure,
  xue: XueMangaFigure,
  xing: XingMangaFigure,
  ying: YingMangaFigure,
} as const;

function resolveLook(id: TalentId, opts: PoseOpts): Look {
  const { hiding, revealing, siPeek, watching } = opts;
  if (revealing) {
    if (id === "si") return siPeek ? { x: 2, y: 2 } : { x: -2, y: -2 };
    return { x: -2, y: -1 };
  }
  if (watching) return { x: 4, y: 0 };
  if (hiding) {
    if (id === "ying" || id === "de") return { x: -3, y: 1 };
    if (id === "xing") return { x: -2, y: 0 };
  }
  return undefined;
}

function resolvePoseClass(id: TalentId, opts: PoseOpts): string {
  const { hiding, revealing, siPeek, watching } = opts;
  if (hiding) {
    if (id === "ying") return "talent-manga-pose-hide-ying";
    if (id === "si" || id === "de") return "talent-manga-pose-lean";
    if (id === "xue") return "talent-manga-pose-quiet";
  }
  if (revealing && id === "si" && siPeek) return "talent-manga-pose-peek";
  if (watching) return "talent-manga-pose-watch";
  return "";
}

export function TalentEditorialMascots({
  isTyping,
  password,
  showPassword,
}: TalentEditorialMascotsProps) {
  const mouse = useMousePosition();
  const [watching, setWatching] = useState(false);
  const [siPeek, setSiPeek] = useState(false);

  const blinks = {
    si: useBlink(2200, 4200),
    de: useBlink(2600, 4800),
    xue: useBlink(3000, 5400),
    xing: useBlink(2400, 4600),
    ying: useBlink(2800, 5000),
  };

  const hiding = password.length > 0 && !showPassword;
  const revealing = password.length > 0 && showPassword;

  useEffect(() => {
    if (!isTyping) {
      setWatching(false);
      return;
    }
    setWatching(true);
    const t = setTimeout(() => setWatching(false), 850);
    return () => clearTimeout(t);
  }, [isTyping]);

  useEffect(() => {
    if (!revealing) {
      setSiPeek(false);
      return;
    }
    let end: ReturnType<typeof setTimeout> | undefined;
    const start = setTimeout(() => {
      setSiPeek(true);
      end = setTimeout(() => setSiPeek(false), 850);
    }, Math.random() * 1400 + 900);
    return () => {
      clearTimeout(start);
      if (end) clearTimeout(end);
    };
  }, [revealing]);

  const poseOpts = { hiding, revealing, siPeek, watching };

  return (
    <div className="talent-manga-theater relative mx-auto w-full max-w-[600px] px-1">
      <div className="relative flex items-end justify-between gap-0.5">
        {TALENT_MASCOTS.map((talent, index) => {
            const Figure = MANGA_FIGURES[talent.id];
            const pose = resolvePoseClass(talent.id, poseOpts);
            const look = resolveLook(talent.id, poseOpts);

            return (
              <figure
                key={talent.id}
                className={cn(
                  "talent-manga-slot group relative flex flex-col items-center",
                  talent.idleClass,
                  `talent-manga-${talent.id}`
                )}
                style={{ width: "19%", animationDelay: `${index * 0.08}s` }}
              >
                <div
                  className={cn(
                    "talent-manga-walker relative h-[148px] w-full",
                    talent.patrolClass,
                    pose
                  )}
                >
                  <div
                    className="pointer-events-none absolute inset-x-0 bottom-0 top-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                    style={{
                      background: `radial-gradient(ellipse at center bottom, ${talent.glow} 0%, transparent 70%)`,
                    }}
                  />
                  <div className="talent-manga-body relative h-full w-full">
                    <Figure
                      accent={talent.accent}
                      accentDark={talent.accentDark}
                      look={look}
                      blink={blinks[talent.id]}
                      mouse={mouse}
                      hideFace={hiding && talent.id === "ying"}
                      leanAway={hiding && (talent.id === "si" || talent.id === "de")}
                      peek={revealing && talent.id === "si" && siPeek}
                      watchForm={watching}
                    />
                  </div>
                </div>
                <figcaption className="talent-manga-caption relative z-10 mt-1 text-center">
                  <span
                    className="inline-block rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wide sm:text-[11px]"
                    style={{
                      color: talent.accent,
                      background: "rgba(255,255,255,0.1)",
                      border: `1px solid ${talent.accent}55`,
                      boxShadow: `0 0 12px ${talent.glow}`,
                    }}
                  >
                    {talent.name}
                  </span>
                  <span className="mt-0.5 block text-[8px] leading-tight text-white/50 sm:text-[9px]">
                    {talent.ability} · {talent.brain}
                  </span>
                </figcaption>
              </figure>
            );
        })}
      </div>
    </div>
  );
}
