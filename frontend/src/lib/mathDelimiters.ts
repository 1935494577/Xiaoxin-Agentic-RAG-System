/**
 * Math delimiter detection + light normalization for chat Markdown.
 * Only enable KaTeX when content actually needs it.
 */

const DELIM_RE =
  /\$\$[\s\S]+?\$\$|\$[^$\n]+?\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]|\\begin\{[a-zA-Z*]+\}/;

/** Strong LaTeX command signals (bare markup without $). */
const LOOSE_CMD_RE =
  /\\(?:frac|vec|bar|perp|cdot|times|div|sqrt|sum|int|prod|lim|alpha|beta|gamma|theta|pi|leq|geq|neq|approx|infty|partial|nabla|in|subset|cup|cap|emptyset|varnothing|mathbb|mathrm|mathbf|left|right|mid|overline|underline|hat|tilde|dot|ddot)\b|\\[{}]|\\[a-zA-Z]+\{/;

export function hasMathDelimiters(text: string): boolean {
  return DELIM_RE.test(text || "");
}

export function hasLooseLatex(text: string): boolean {
  return LOOSE_CMD_RE.test(text || "");
}

/** True when MarkdownContent should load remark-math / rehype-katex. */
export function needsMathRender(text: string): boolean {
  const s = text || "";
  return hasMathDelimiters(s) || hasLooseLatex(s);
}

/**
 * Wrap simple paren-groups that contain LaTeX commands into $...$
 * so KaTeX can render RAG excerpts like `( \\vec{a} = (0,1) )`.
 * Skips groups that already use math delimiters.
 */
export function normalizeLooseParenLatex(text: string): string {
  const s = text || "";
  if (!hasLooseLatex(s)) return s;
  // Non-greedy paren groups on one line; require a backslash command inside.
  return s.replace(/\(([^()\n\\]*\\[a-zA-Z{][^()\n]*)\)/g, (full, inner: string) => {
    const t = String(inner).trim();
    if (!t || t.includes("$") || t.startsWith("\\(") || t.startsWith("\\[")) return full;
    if (!LOOSE_CMD_RE.test(t)) return full;
    return `$${t}$`;
  });
}

/** Prepare assistant markdown before ReactMarkdown + optional math plugins. */
export function prepareMathMarkdown(text: string): string {
  return normalizeLooseParenLatex(text || "");
}
