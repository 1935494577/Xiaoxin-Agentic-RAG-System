/** Map API / network errors to operator-readable Chinese messages. */

export function formatAdminLoadError(error: unknown, fallback: string): string {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  if (!raw.trim()) return fallback;

  try {
    const parsed = JSON.parse(raw) as { detail?: string; feature?: string; department?: string };
    if (parsed.detail) {
      if (raw.includes("403") || parsed.detail.includes("无权")) {
        return `${parsed.detail}。「工具」页仅技术部可配置；运营/媒体/剪辑请在 Jnao Chat 使用，或联系技术部开启 web_search。`;
      }
      return parsed.detail;
    }
  } catch {
    /* not JSON */
  }

  if (/failed to fetch|network|load/i.test(raw)) {
    return "无法连接后端 API，请确认 run-dev 已启动且 http://127.0.0.1:8010/health 返回 ok，然后点重试。";
  }

  return raw.length > 200 ? `${raw.slice(0, 200)}…` : raw;
}
