/**
 * 五天赋 — 展示顺序与 flat 图标一致（左→右）：思 · 德 · 学 · 行 · 赢
 * 配色与 `public/talents/` 参考图标一致。
 */

export type TalentId = "si" | "ying" | "xue" | "de" | "xing";

export type TalentMascot = {
  id: TalentId;
  name: string;
  ability: string;
  brain: string;
  src: string;
  accent: string;
  accentDark: string;
  glow: string;
  idleClass: string;
  patrolClass: string;
};

const DEFINITIONS: Record<TalentId, TalentMascot> = {
  si: {
    id: "si",
    name: "思者",
    ability: "创造力",
    brain: "右脑5",
    src: "/talents/xue.jpg",
    accent: "#43A047",
    accentDark: "#2E7D32",
    glow: "rgba(67,160,71,0.32)",
    idleClass: "talent-manga-idle-si",
    patrolClass: "talent-manga-patrol-si",
  },
  de: {
    id: "de",
    name: "德者",
    ability: "观察力",
    brain: "左脑4",
    src: "/talents/de.jpg",
    accent: "#A1887F",
    accentDark: "#6D4C41",
    glow: "rgba(161,136,127,0.28)",
    idleClass: "talent-manga-idle-de",
    patrolClass: "talent-manga-patrol-de",
  },
  xue: {
    id: "xue",
    name: "学者",
    ability: "专注力",
    brain: "平衡3",
    src: "/talents/xing.jpg",
    accent: "#1E88E5",
    accentDark: "#1565C0",
    glow: "rgba(30,136,229,0.28)",
    idleClass: "talent-manga-idle-xue",
    patrolClass: "talent-manga-patrol-xue",
  },
  xing: {
    id: "xing",
    name: "行者",
    ability: "记忆力",
    brain: "左脑5",
    src: "/talents/si.jpg",
    accent: "#FFB300",
    accentDark: "#F57F17",
    glow: "rgba(255,179,0,0.32)",
    idleClass: "talent-manga-idle-xing",
    patrolClass: "talent-manga-patrol-xing",
  },
  ying: {
    id: "ying",
    name: "赢者",
    ability: "想象力",
    brain: "右脑4",
    src: "/talents/ying.jpg",
    accent: "#EF5350",
    accentDark: "#C62828",
    glow: "rgba(239,83,80,0.28)",
    idleClass: "talent-manga-idle-ying",
    patrolClass: "talent-manga-patrol-ying",
  },
};

/** 左→右：思者 · 德者 · 学者 · 行者 · 赢者 */
export const TALENT_DISPLAY_ORDER: readonly TalentId[] = [
  "si",
  "de",
  "xue",
  "xing",
  "ying",
];

export const TALENT_MASCOTS: readonly TalentMascot[] = TALENT_DISPLAY_ORDER.map(
  (id) => DEFINITIONS[id]
);

export function getTalent(id: TalentId): TalentMascot {
  return DEFINITIONS[id];
}
