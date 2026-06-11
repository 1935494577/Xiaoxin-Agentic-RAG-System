import { type KeyboardEvent, useRef, useEffect } from "react";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  streaming: boolean;
  onStop: () => void;
  placeholder?: string;
};

export function ChatInput({
  value,
  onChange,
  onSend,
  streaming,
  onStop,
  placeholder = "输入问题，助手将基于知识库内容回答",
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!streaming) ref.current?.focus();
  }, [streaming]);

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!streaming && value.trim()) onSend();
    }
  };

  return (
    <div className="w-full max-w-[820px] mx-auto flex gap-2.5 items-end bg-surface-muted border border-border rounded-[20px] px-[18px] py-2.5 shadow-sm transition-all focus-within:border-brand focus-within:shadow-[0_2px_16px_rgba(21,101,192,0.12)]">
      <textarea
        ref={ref}
        rows={1}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={streaming}
        className="flex-1 border-none outline-none resize-none text-[15px] leading-relaxed min-h-6 max-h-[200px] font-[inherit] bg-transparent placeholder:text-text-muted disabled:opacity-50"
      />
      {streaming ? (
        <button
          type="button"
          onClick={onStop}
          className="border-none bg-error text-white rounded-[10px] px-4 py-2 text-sm font-medium cursor-pointer shrink-0"
        >
          停止
        </button>
      ) : (
        <button
          type="button"
          onClick={onSend}
          disabled={!value.trim()}
          className="border-none bg-brand text-white rounded-xl px-[18px] py-2 text-sm font-medium cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          发送
        </button>
      )}
    </div>
  );
}
