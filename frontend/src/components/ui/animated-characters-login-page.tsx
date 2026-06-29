import { useEffect, useRef, useState, type RefObject } from "react";

type Look = { x?: number; y?: number } | undefined;

type FacePos = { faceX: number; faceY: number; bodySkew: number; bodyTilt: number };

function useMousePosition() {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => setMouse({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);
  return mouse;
}

function calcFacePos(
  ref: RefObject<HTMLDivElement | null>,
  mouseX: number,
  mouseY: number,
  sensitivity = 1
): FacePos {
  if (!ref.current) return { faceX: 0, faceY: 0, bodySkew: 0, bodyTilt: 0 };
  const rect = ref.current.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height * 0.32;
  const dx = mouseX - cx;
  const dy = mouseY - cy;
  return {
    faceX: Math.max(-10, Math.min(10, (dx / 24) * sensitivity)),
    faceY: Math.max(-7, Math.min(7, (dy / 30) * sensitivity)),
    bodySkew: Math.max(-4, Math.min(4, (-dx / 140) * sensitivity)),
    bodyTilt: Math.max(-3, Math.min(3, (dx / 200) * sensitivity)),
  };
}

function useBlink(minDelay = 2600, maxDelay = 5200) {
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
          }, 130);
        },
        Math.random() * (maxDelay - minDelay) + minDelay
      );
    };
    schedule();
    return () => clearTimeout(timeout);
  }, [minDelay, maxDelay]);
  return blinking;
}

type EyeProps = {
  size: number;
  pupil: number;
  maxMove: number;
  look?: Look;
  blink: boolean;
  sparkle?: boolean;
};

function TalentEye({ size, pupil, maxMove, look, blink, sparkle }: EyeProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { x: mouseX, y: mouseY } = useMousePosition();

  const offset = (() => {
    if (look?.x !== undefined && look?.y !== undefined) {
      return { x: look.x, y: look.y };
    }
    if (!ref.current) return { x: 0, y: 0 };
    const r = ref.current.getBoundingClientRect();
    const dx = mouseX - (r.left + r.width / 2);
    const dy = mouseY - (r.top + r.height / 2);
    const dist = Math.min(Math.hypot(dx, dy), maxMove);
    const a = Math.atan2(dy, dx);
    return { x: Math.cos(a) * dist, y: Math.sin(a) * dist };
  })();

  return (
    <div
      ref={ref}
      className="relative flex items-center justify-center rounded-full bg-white transition-all duration-150"
      style={{ width: size, height: blink ? 2 : size, overflow: "hidden" }}
    >
      {!blink && (
        <>
          <div
            className="rounded-full bg-[#1a1d21] transition-transform duration-100"
            style={{
              width: pupil,
              height: pupil,
              transform: `translate(${offset.x}px, ${offset.y}px)`,
            }}
          />
          {sparkle && (
            <div
              className="pointer-events-none absolute rounded-full bg-white/90"
              style={{ width: pupil * 0.35, height: pupil * 0.35, top: 2, left: 3 }}
            />
          )}
        </>
      )}
    </div>
  );
}

type TalentId = "si" | "ying" | "xue" | "de" | "xing";

type TalentSpec = {
  id: TalentId;
  name: string;
  ability: string;
  brain: string;
  left: number;
  width: number;
  height: number;
  z: number;
  idle: string;
  gradient: [string, string];
  accent: string;
};

const TALENTS: TalentSpec[] = [
  {
    id: "si",
    name: "思者",
    ability: "创造力",
    brain: "右脑5",
    left: 0,
    width: 96,
    height: 248,
    z: 1,
    idle: "talent-idle-si",
    gradient: ["#9575FF", "#5E35B1"],
    accent: "#FFE082",
  },
  {
    id: "ying",
    name: "赢者",
    ability: "想象力",
    brain: "右脑4",
    left: 88,
    width: 92,
    height: 210,
    z: 2,
    idle: "talent-idle-ying",
    gradient: ["#FFD54F", "#F9A825"],
    accent: "#FFFDE7",
  },
  {
    id: "xue",
    name: "学者",
    ability: "专注力",
    brain: "平衡3",
    left: 172,
    width: 88,
    height: 196,
    z: 3,
    idle: "talent-idle-xue",
    gradient: ["#42A5F5", "#1565C0"],
    accent: "#E3F2FD",
  },
  {
    id: "de",
    name: "德者",
    ability: "观察力",
    brain: "左脑4",
    left: 252,
    width: 94,
    height: 224,
    z: 4,
    idle: "talent-idle-de",
    gradient: ["#66BB6A", "#2E7D32"],
    accent: "#DCEDC8",
  },
  {
    id: "xing",
    name: "行者",
    ability: "记忆力",
    brain: "左脑5",
    left: 338,
    width: 90,
    height: 188,
    z: 5,
    idle: "talent-idle-xing",
    gradient: ["#FF8A65", "#E64A19"],
    accent: "#FFCCBC",
  },
];

function TalentBadge({ name, ability, brain }: Pick<TalentSpec, "name" | "ability" | "brain">) {
  return (
    <div className="talent-badge pointer-events-none absolute -bottom-5 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-full border border-white/15 bg-black/40 px-2 py-0.5 backdrop-blur-md">
      <p className="text-center text-[9px] font-semibold leading-tight text-white/95">{name}</p>
      <p className="text-center text-[8px] leading-tight text-white/55">
        {ability} · {brain}
      </p>
    </div>
  );
}

type MascotProps = {
  spec: TalentSpec;
  pos: FacePos;
  blink: boolean;
  look?: Look;
  hideFace: boolean;
  leanAway: boolean;
  peek: boolean;
  bodyRef: RefObject<HTMLDivElement | null>;
};

function SiMascot({ spec, pos, blink, look, leanAway, peek, bodyRef }: MascotProps) {
  const h = leanAway ? spec.height + 28 : spec.height;
  return (
    <div className={`absolute bottom-8 ${spec.idle}`} style={{ left: spec.left, width: spec.width, zIndex: spec.z }}>
      <div
        ref={bodyRef}
        className="talent-body talent-body-si relative mx-auto transition-all duration-700"
        style={{
          width: spec.width,
          height: h,
          background: `linear-gradient(168deg, ${spec.gradient[0]} 0%, ${spec.gradient[1]} 100%)`,
          transform: leanAway
            ? `skewX(-10deg) translateX(16px) rotate(${-2 + pos.bodyTilt}deg)`
            : `skewX(${pos.bodySkew}deg) rotate(${-2 + pos.bodyTilt}deg)`,
        }}
      >
        <div className="talent-idea-orbit pointer-events-none absolute -top-9 left-1/2 -translate-x-1/2" aria-hidden>
          <span className="talent-lightbulb absolute left-1/2 top-0 -translate-x-1/2 text-sm leading-none">💡</span>
          <span className="talent-orbit-dot talent-orbit-a block h-2 w-2 rounded-full bg-[#FFE082]" />
          <span className="talent-orbit-dot talent-orbit-b block h-1.5 w-1.5 rounded-full bg-white/70" />
        </div>
        <div
          className="absolute flex gap-2 transition-all duration-300"
          style={{ left: 22 + pos.faceX, top: (peek ? 42 : 36) + pos.faceY - 6 }}
        >
          <div className="relative">
            <div className="absolute -top-1.5 left-0 h-[2px] w-3.5 rounded-full bg-[#311B92]/35" style={{ transform: "rotate(-12deg)" }} />
            <TalentEye size={16} pupil={7} maxMove={4} look={look ?? { x: 0, y: -3 }} blink={blink} sparkle />
          </div>
          <div className="relative">
            <div className="absolute -top-1.5 right-0 h-[2px] w-3.5 rounded-full bg-[#311B92]/35" style={{ transform: "rotate(12deg)" }} />
            <TalentEye size={16} pupil={7} maxMove={4} look={look ?? { x: 0, y: -3 }} blink={blink} sparkle />
          </div>
        </div>
        <div className="absolute left-[26px] top-[58px] h-2 w-2 rounded-full bg-[#FFAB91]/55" />
        <div className="absolute right-[24px] top-[62px] h-2 w-2 rounded-full bg-[#FFAB91]/55" />
        <div
          className="absolute h-[3px] w-7 rounded-full bg-[#311B92]/50 transition-all duration-300"
          style={{
            left: 30 + pos.faceX,
            top: 68 + pos.faceY,
            transform: peek ? "rotate(0deg) scaleX(1.1)" : "rotate(-8deg)",
          }}
        />
        <div className="talent-feet absolute bottom-0 left-1/2 flex -translate-x-1/2 gap-3">
          <span className="h-2 w-5 rounded-b-full bg-black/15" />
          <span className="h-2 w-5 rounded-b-full bg-black/15" />
        </div>
        <div className="talent-arm talent-arm-left absolute -left-2 top-[42%] h-7 w-3 rounded-full bg-white/15" />
        <div className="talent-arm talent-arm-right absolute -right-1 top-[36%] h-8 w-3 rounded-full bg-white/15" />
      </div>
      <TalentBadge {...spec} />
    </div>
  );
}

function YingMascot({ spec, pos, blink, look, hideFace }: MascotProps) {
  return (
    <div className={`absolute bottom-8 ${spec.idle}`} style={{ left: spec.left, width: spec.width, zIndex: spec.z }}>
      <div
        className="talent-body talent-body-ying relative mx-auto transition-all duration-700"
        style={{
          width: spec.width,
          height: spec.height,
          background: `linear-gradient(168deg, ${spec.gradient[0]} 0%, ${spec.gradient[1]} 100%)`,
          transform: `skewX(${pos.bodySkew}deg) rotate(${1 + pos.bodyTilt}deg)`,
        }}
      >
        <div className="pointer-events-none absolute -top-5 left-1/2 flex -translate-x-1/2 items-end gap-1" aria-hidden>
          <span className="talent-crown-block h-3 w-3 rotate-[-18deg] rounded-sm bg-[#FFF8E1]" />
          <span className="talent-crown-block mb-1 h-4 w-4 rounded-sm bg-[#FFFDE7]" />
          <span className="talent-crown-block h-3 w-3 rotate-[18deg] rounded-sm bg-[#FFF8E1]" />
        </div>
        {!hideFace ? (
          <>
            <div className="absolute flex gap-2" style={{ left: 24 + pos.faceX, top: 34 + pos.faceY }}>
              <TalentEye size={14} pupil={6} maxMove={4} look={look} blink={blink} />
              <TalentEye size={14} pupil={6} maxMove={4} look={look} blink={blink} />
            </div>
            <div className="absolute left-[28px] top-[52px] h-1.5 w-1.5 rounded-full bg-[#F57F17]/40" />
            <div className="absolute right-[26px] top-[52px] h-1.5 w-1.5 rounded-full bg-[#F57F17]/40" />
            <div
              className="absolute h-[3px] w-8 rounded-full bg-[#E65100]/55"
              style={{ left: 26 + pos.faceX, top: 58 + pos.faceY }}
            />
          </>
        ) : (
          <div className="absolute flex gap-3" style={{ left: 20, top: 34 }}>
            <div className="h-2.5 w-7 rounded-full bg-[#F9A825]" />
            <div className="h-2.5 w-7 rounded-full bg-[#F9A825]" />
          </div>
        )}
        <div className="pointer-events-none absolute -right-2 top-[28%] text-base text-[#FFF8E1] opacity-90 talent-sparkle-twinkle" aria-hidden>
          ✦
        </div>
        <div className="talent-feet absolute bottom-0 left-1/2 flex -translate-x-1/2 gap-2.5">
          <span className="h-1.5 w-4 rounded-b-full bg-black/12" />
          <span className="h-1.5 w-4 rounded-b-full bg-black/12" />
        </div>
      </div>
      <TalentBadge {...spec} />
    </div>
  );
}

function XueMascot({ spec, pos, blink, look }: MascotProps) {
  return (
    <div className={`absolute bottom-8 ${spec.idle}`} style={{ left: spec.left, width: spec.width, zIndex: spec.z }}>
      <div
        className="talent-body talent-body-xue relative mx-auto transition-all duration-700"
        style={{
          width: spec.width,
          height: spec.height,
          background: `linear-gradient(168deg, ${spec.gradient[0]} 0%, ${spec.gradient[1]} 100%)`,
          transform: `skewX(${pos.bodySkew * 0.6}deg) rotate(${pos.bodyTilt}deg)`,
        }}
      >
        <div className="absolute flex gap-1.5" style={{ left: 18 + pos.faceX, top: 32 + pos.faceY }}>
          <div className="relative rounded-full border-2 border-white/75 p-0.5">
            <TalentEye size={13} pupil={5} maxMove={3} look={look} blink={blink} />
          </div>
          <div className="relative rounded-full border-2 border-white/75 p-0.5">
            <TalentEye size={13} pupil={5} maxMove={3} look={look} blink={blink} />
          </div>
        </div>
        <div
          className="absolute h-[2px] w-5 rounded-full bg-white/35"
          style={{ left: 32 + pos.faceX, top: 50 + pos.faceY }}
        />
        <div
          className="pointer-events-none absolute -right-1 bottom-[36%] h-10 w-7 rounded-sm border border-white/30 shadow-sm talent-book-flip"
          style={{ backgroundColor: spec.accent }}
          aria-hidden
        >
          <div className="mx-auto mt-2 h-0.5 w-4 rounded bg-[#1565C0]/25" />
          <div className="mx-auto mt-1 h-0.5 w-3 rounded bg-[#1565C0]/20" />
          <div className="mx-auto mt-1 h-0.5 w-3.5 rounded bg-[#1565C0]/15" />
        </div>
        <div className="talent-feet absolute bottom-0 left-1/2 flex -translate-x-1/2 gap-2">
          <span className="h-1.5 w-3.5 rounded-b-full bg-black/12" />
          <span className="h-1.5 w-3.5 rounded-b-full bg-black/12" />
        </div>
      </div>
      <TalentBadge {...spec} />
    </div>
  );
}

function DeMascot({ spec, pos, blink, look, leanAway }: MascotProps) {
  return (
    <div className={`absolute bottom-8 ${spec.idle}`} style={{ left: spec.left, width: spec.width, zIndex: spec.z }}>
      <div
        className="talent-body talent-body-de relative mx-auto transition-all duration-700"
        style={{
          width: spec.width,
          height: spec.height,
          background: `linear-gradient(168deg, ${spec.gradient[0]} 0%, ${spec.gradient[1]} 100%)`,
          transform: leanAway
            ? `skewX(-8deg) translateX(12px) rotate(${-1 + pos.bodyTilt}deg)`
            : `skewX(${pos.bodySkew}deg) rotate(${-1 + pos.bodyTilt}deg)`,
        }}
      >
        <div className="absolute flex items-end gap-2" style={{ left: 16 + pos.faceX, top: 30 + pos.faceY }}>
          <TalentEye size={18} pupil={7} maxMove={5} look={look ?? { x: 3, y: 0 }} blink={blink} />
          <TalentEye size={14} pupil={6} maxMove={4} look={look ?? { x: 3, y: 0 }} blink={blink} />
        </div>
        <div
          className="absolute h-[2px] w-6 rounded-full bg-white/30"
          style={{ left: 34 + pos.faceX, top: 54 + pos.faceY }}
        />
        <div className="pointer-events-none absolute -right-3 top-[32%] talent-scope-sweep" aria-hidden>
          <div className="h-9 w-9 rounded-full border-[3px] border-white/55 bg-white/10" />
          <div className="absolute bottom-0 left-1/2 h-3.5 w-1 -translate-x-1/2 rotate-45 rounded bg-white/45" />
          <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/20" />
        </div>
        <div className="talent-feet absolute bottom-0 left-1/2 flex -translate-x-1/2 gap-2.5">
          <span className="h-2 w-4 rounded-b-full bg-black/12" />
          <span className="h-2 w-4 rounded-b-full bg-black/12" />
        </div>
      </div>
      <TalentBadge {...spec} />
    </div>
  );
}

function XingMascot({ spec, pos, blink, look }: MascotProps) {
  return (
    <div className={`absolute bottom-8 ${spec.idle}`} style={{ left: spec.left, width: spec.width, zIndex: spec.z }}>
      <div
        className="talent-body talent-body-xing relative mx-auto transition-all duration-700"
        style={{
          width: spec.width,
          height: spec.height,
          background: `linear-gradient(168deg, ${spec.gradient[0]} 0%, ${spec.gradient[1]} 100%)`,
          transform: `skewX(${pos.bodySkew * 0.5}deg) rotate(${1 + pos.bodyTilt}deg)`,
        }}
      >
        <div className="absolute flex gap-2" style={{ left: 22 + pos.faceX, top: 30 + pos.faceY }}>
          <TalentEye size={13} pupil={5} maxMove={3} look={look} blink={blink} />
          <TalentEye size={13} pupil={5} maxMove={3} look={look} blink={blink} />
        </div>
        <div
          className="absolute h-[2px] w-5 rounded-full bg-[#BF360C]/45"
          style={{ left: 28 + pos.faceX, top: 48 + pos.faceY }}
        />
        <div className="pointer-events-none absolute -right-0.5 bottom-[34%] flex flex-col gap-1 talent-memory-fan" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="flex items-center gap-1 rounded-sm border border-white/25 bg-white/15 px-1 py-0.5"
              style={{ opacity: 1 - i * 0.12, transform: `translateX(${i * 2}px)` }}
            >
              <span className="h-1.5 w-1.5 rounded-[2px] bg-white/50" />
              <span className="h-0.5 w-3 rounded bg-white/40" />
            </div>
          ))}
        </div>
        <div className="talent-arm absolute -left-1.5 top-[44%] h-6 w-2.5 rounded-full bg-white/15 talent-arm-wave" />
        <div className="talent-feet absolute bottom-0 left-1/2 flex -translate-x-1/2 gap-2">
          <span className="h-1.5 w-4 rounded-b-full bg-black/12" />
          <span className="h-1.5 w-4 rounded-b-full bg-black/12" />
        </div>
      </div>
      <TalentBadge {...spec} />
    </div>
  );
}

const MASCOT_RENDERERS = {
  si: SiMascot,
  ying: YingMascot,
  xue: XueMascot,
  de: DeMascot,
  xing: XingMascot,
} as const;

export type AnimatedCharacterMascotsProps = {
  isTyping: boolean;
  password: string;
  showPassword: boolean;
};

export function AnimatedCharacterMascots({
  isTyping,
  password,
  showPassword,
}: AnimatedCharacterMascotsProps) {
  const { x: mouseX, y: mouseY } = useMousePosition();
  const refs = {
    si: useRef<HTMLDivElement>(null),
    ying: useRef<HTMLDivElement>(null),
    xue: useRef<HTMLDivElement>(null),
    de: useRef<HTMLDivElement>(null),
    xing: useRef<HTMLDivElement>(null),
  };

  const blinks = {
    si: useBlink(2200, 4200),
    ying: useBlink(2800, 5000),
    xue: useBlink(3000, 5500),
    de: useBlink(2400, 4600),
    xing: useBlink(2600, 4800),
  };

  const [watching, setWatching] = useState(false);
  const [siPeek, setSiPeek] = useState(false);

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
    }, Math.random() * 1600 + 1000);
    return () => {
      clearTimeout(start);
      if (end) clearTimeout(end);
    };
  }, [revealing]);

  const positions = {
    si: calcFacePos(refs.si, mouseX, mouseY, 1.1),
    ying: calcFacePos(refs.ying, mouseX, mouseY, 0.9),
    xue: calcFacePos(refs.xue, mouseX, mouseY, 0.75),
    de: calcFacePos(refs.de, mouseX, mouseY, 1),
    xing: calcFacePos(refs.xing, mouseX, mouseY, 0.85),
  };

  function resolveLook(id: TalentId): Look {
    if (revealing) {
      if (id === "si") return siPeek ? { x: 4, y: 4 } : { x: -3, y: -3 };
      return { x: -4, y: -2 };
    }
    if (watching) {
      if (id === "de" || id === "xue") return { x: -3, y: -2 };
      if (id === "ying") return { x: 2, y: -2 };
      return { x: 3, y: 2 };
    }
    if (hiding) {
      if (id === "ying" || id === "de") return { x: -4, y: 2 };
      if (id === "xing") return { x: -3, y: 0 };
    }
    return undefined;
  }

  return (
    <div className="talent-mascot-stage relative mx-auto w-full max-w-[440px] pb-6" style={{ height: "292px" }}>
      <div className="talent-stage-floor pointer-events-none absolute bottom-8 left-1/2 h-4 w-[92%] -translate-x-1/2 rounded-[50%] bg-gradient-to-b from-black/25 to-transparent blur-md" />
      <div className="talent-stage-glow pointer-events-none absolute bottom-12 left-1/2 h-20 w-[75%] -translate-x-1/2 rounded-[50%] bg-[#FFD54F]/10 blur-2xl" />

      {TALENTS.map((spec) => {
        const Renderer = MASCOT_RENDERERS[spec.id];
        return (
          <Renderer
            key={spec.id}
            spec={spec}
            pos={positions[spec.id]}
            blink={blinks[spec.id]}
            look={resolveLook(spec.id)}
            hideFace={hiding && spec.id === "ying"}
            leanAway={hiding && (spec.id === "si" || spec.id === "de")}
            peek={revealing && spec.id === "si" && siPeek}
            bodyRef={refs[spec.id]}
          />
        );
      })}
    </div>
  );
}
