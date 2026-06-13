import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const mdComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-xl font-semibold mt-6 mb-3 first:mt-0 text-text tracking-tight">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold mt-5 mb-2.5 first:mt-0 text-text tracking-tight">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold mt-4 mb-2 first:mt-0 text-text">{children}</h3>
  ),
  p: ({ children }) => <p className="my-2.5 leading-7 text-[15px] text-text">{children}</p>,
  ul: ({ children }) => <ul className="my-2.5 pl-5 list-disc space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-2.5 pl-5 list-decimal space-y-1">{children}</ol>,
  li: ({ children }) => <li className="leading-7 text-[15px] pl-0.5">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-text">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-[3px] border-brand/35 pl-4 my-3 text-text-muted">{children}</blockquote>
  ),
  hr: () => <hr className="my-6 border-0 border-t border-border" />,
  table: ({ children }) => (
    <div className="my-4 overflow-x-auto rounded-lg border border-border bg-white">
      <table className="w-full min-w-[280px] text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-surface-muted/80">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-border px-3.5 py-2.5 text-left font-semibold text-text whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-border px-3.5 py-2.5 text-text align-top leading-relaxed">{children}</td>
  ),
  tr: ({ children }) => <tr className="last:[&>td]:border-b-0">{children}</tr>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-brand underline underline-offset-2 hover:text-brand-dark"
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className?.includes("language-"));
    if (isBlock) {
      return (
        <pre className="my-3 rounded-lg bg-[#f6f8fa] border border-border px-4 py-3 overflow-x-auto text-[13px] leading-relaxed">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      );
    }
    return (
      <code
        className="rounded-md px-1.5 py-0.5 bg-surface-muted text-[13px] font-mono text-brand-dark"
        {...props}
      >
        {children}
      </code>
    );
  },
  del: ({ children }) => <span className="line-through">{children}</span>,
};

type Props = {
  content: string;
};

export function MarkdownContent({ content }: Props) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[[remarkGfm, { singleTilde: false }]]} components={mdComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export function StreamingPlainText({ content }: Props) {
  return (
    <div className="markdown-body markdown-stream">
      <p className="whitespace-pre-wrap break-words m-0 leading-7 text-[15px] text-text">
        {content}
        <span className="stream-cursor" aria-hidden />
      </p>
    </div>
  );
}
