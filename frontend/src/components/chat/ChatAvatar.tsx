import { profileInitial } from "../../lib/avatarImage";

type Props = {
  avatarUrl?: string;
  /** Display name for initial fallback */
  label?: string;
  /** Shown when label empty (e.g. "AI") */
  fallback?: string;
  variant?: "user" | "ai";
  size?: "chat" | "sidebar";
};

const SIZE = {
  chat: "w-11 h-11 text-[15px]",
  sidebar: "w-9 h-9 text-sm",
} as const;

export function ChatAvatar({
  avatarUrl = "",
  label = "",
  fallback = "你",
  variant = "user",
  size = "chat",
}: Props) {
  const dim = SIZE[size];
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt=""
        className={`${dim} rounded-full object-cover shrink-0 bg-surface-muted mt-0.5`}
      />
    );
  }

  const trimmed = label.trim();
  const text = trimmed ? profileInitial(trimmed, fallback) : fallback;
  const bg =
    variant === "ai"
      ? "bg-gradient-to-br from-brand to-brand-dark text-white"
      : "bg-gradient-to-br from-brand/85 to-brand-dark text-white";

  return (
    <div
      className={`${dim} rounded-full ${bg} flex items-center justify-center font-semibold shrink-0 mt-0.5 leading-none`}
    >
      {text.length <= 2 ? text : profileInitial(trimmed, fallback)}
    </div>
  );
}
