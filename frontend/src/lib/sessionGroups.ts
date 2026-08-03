import type { ChatSession } from "../api/types";

export type SessionGroup = {
  key: "today" | "yesterday" | "week" | "earlier";
  label: string;
  items: ChatSession[];
};

function dayStart(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

export function groupSessionsByDate(sessions: ChatSession[], now: Date = new Date()): SessionGroup[] {
  const todayStart = dayStart(now);
  const yesterdayStart = todayStart - 86_400_000;
  const weekStart = todayStart - 6 * 86_400_000;

  const groups: SessionGroup[] = [
    { key: "today", label: "今天", items: [] },
    { key: "yesterday", label: "昨天", items: [] },
    { key: "week", label: "近 7 天", items: [] },
    { key: "earlier", label: "更早", items: [] },
  ];

  for (const session of sessions) {
    const ts = session.updated_at ? new Date(session.updated_at).getTime() : NaN;
    if (!Number.isFinite(ts)) {
      groups[3].items.push(session);
    } else if (ts >= todayStart) {
      groups[0].items.push(session);
    } else if (ts >= yesterdayStart) {
      groups[1].items.push(session);
    } else if (ts >= weekStart) {
      groups[2].items.push(session);
    } else {
      groups[3].items.push(session);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}
