import type { ChatMessage, ChatSession } from "../api/types";

function basename(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
}

export function messagesToMarkdown(
  messages: ChatMessage[],
  session?: Pick<ChatSession, "title"> | null
): string {
  const title = session?.title?.trim() || "对话导出";
  const lines: string[] = [`# ${title}`, "", `导出时间：${new Date().toLocaleString()}`, ""];

  for (const msg of messages) {
    const role = msg.role === "user" ? "用户" : "助手";
    lines.push(`## ${role}`, "", msg.content.trim(), "");
    if (msg.role === "assistant") {
      const refs = msg.meta?.source_refs?.length
        ? msg.meta.source_refs.map((r) => basename(r.source || r.parent_id || ""))
        : (msg.meta?.sources || []).map(basename);
      if (refs.length) {
        lines.push(`> 引用：${refs.join(" · ")}`, "");
      }
    }
  }

  return lines.join("\n").trimEnd() + "\n";
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
