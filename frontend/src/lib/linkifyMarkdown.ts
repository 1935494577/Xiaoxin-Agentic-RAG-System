/**
 * Turn bare domains in markdown prose into clickable [text](url) links.
 * Skips fenced blocks, inline code, existing markdown links, and math spans.
 */

const FENCE_RE = /(```[\s\S]*?```|~~~[\s\S]*?~~~)/g;
const INLINE_CODE_RE = /(`[^`\n]+`)/g;
const MATH_BLOCK_RE = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\])/g;
const MATH_INLINE_RE = /(\$[^$\n]+\$|\\\([^\\]*\\\))/g;
const MD_LINK_RE = /(\[[^\]\n]+\]\([^)\n]+\))/g;

const DOMAIN_BODY =
  "[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\\.[a-zA-Z]{2,24}";

const BARE_DOMAIN_RE = new RegExp(
  `(?<![/@\\w])\\b(${DOMAIN_BODY})(?:\\/[^\\s<>\\)\\]"']*)?\\b`,
  "gi",
);

const BOLD_DOMAIN_RE = new RegExp(`\\*\\*(${DOMAIN_BODY})\\*\\*`, "gi");

export function isLinkableDomain(text: string): boolean {
  const t = text.trim();
  if (!t || t.includes(" ")) return false;
  return new RegExp(`^${DOMAIN_BODY}$`, "i").test(t);
}

export function isLinkableUrl(text: string): boolean {
  const t = text.trim();
  return /^https?:\/\/.+/i.test(t);
}

export function hrefForDomainOrUrl(text: string): string {
  const t = text.trim();
  if (isLinkableUrl(t)) return t;
  if (isLinkableDomain(t)) return `https://${t.replace(/^\/+/, "")}`;
  return t;
}

function splitMathProtected(segment: string): string[] {
  const parts: string[] = [];
  let last = 0;
  const re = new RegExp(`${MATH_BLOCK_RE.source}|${MATH_INLINE_RE.source}`, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(segment)) !== null) {
    if (m.index > last) parts.push(segment.slice(last, m.index));
    parts.push(m[0]);
    last = m.index + m[0].length;
  }
  if (last < segment.length) parts.push(segment.slice(last));
  return parts.length ? parts : [segment];
}

function protectMarkdownLinks(segment: string): { text: string; links: string[] } {
  const links: string[] = [];
  const text = segment.replace(MD_LINK_RE, (link) => {
    links.push(link);
    return `\x00L${links.length - 1}\x00`;
  });
  return { text, links };
}

function restoreMarkdownLinks(text: string, links: string[]): string {
  return text.replace(/\x00L(\d+)\x00/g, (_, idx) => links[Number(idx)] ?? "");
}

function linkifyProse(segment: string): string {
  const { text: protectedText, links } = protectMarkdownLinks(segment);
  let out = protectedText.replace(BOLD_DOMAIN_RE, (_m, domain: string) => {
    const d = domain.trim();
    return `[**${d}**](https://${d})`;
  });

  out = out.replace(BARE_DOMAIN_RE, (match, _domain, offset) => {
    const before = out.slice(Math.max(0, offset - 2), offset);
    if (before.endsWith("](") || before.endsWith(":/")) return match;
    const chBefore = offset > 0 ? out[offset - 1] : "";
    if (chBefore === "@" || chBefore === "/" || chBefore === "*") return match;
    return `[${match}](https://${match})`;
  });

  return restoreMarkdownLinks(out, links);
}

function linkifySegment(segment: string): string {
  return splitMathProtected(segment)
    .map((p) => {
      if (p.startsWith("$$") || p.startsWith("\\[") || p.startsWith("$") || p.startsWith("\\(")) {
        return p;
      }
      return linkifyProse(p);
    })
    .join("");
}

/** Linkify bare domains in markdown while preserving code & math. */
export function linkifyMarkdown(content: string): string {
  if (!content?.trim()) return content || "";

  const fenced: string[] = [];
  let text = content.replace(FENCE_RE, (block) => {
    fenced.push(block);
    return `\x00F${fenced.length - 1}\x00`;
  });

  const parts = text.split(INLINE_CODE_RE);
  text = parts
    .map((part, i) => {
      if (i % 2 === 1) return part;
      return linkifySegment(part);
    })
    .join("");

  return text.replace(/\x00F(\d+)\x00/g, (_, idx) => fenced[Number(idx)] ?? "");
}

export function prepareChatMarkdown(content: string): string {
  return linkifyMarkdown(content);
}
