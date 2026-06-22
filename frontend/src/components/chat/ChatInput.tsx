import { type KeyboardEvent, useRef, useEffect, useCallback } from "react";
import { Mic, Square } from "lucide-react";
import { useSpeechInput } from "../../hooks/useSpeechInput";

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
  const speech = useSpeechInput({
    value,
    onChange,
    disabled: streaming,
    lang: "zh-CN",
  });
  const { displayValue, toggleSpeech, stopSpeech, active, busy, listening, recording } = speech;

  useEffect(() => {
    if (!streaming) ref.current?.focus();
  }, [streaming]);

  useEffect(() => {
    if (streaming) stopSpeech();
  }, [streaming, stopSpeech]);

  const autoGrow = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
  }, []);

  useEffect(() => {
    autoGrow();
  }, [displayValue, autoGrow]);

  const handleChange = (v: string) => {
    if (active) stopSpeech();
    onChange(v);
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!streaming && value.trim()) onSend();
    }
  };

  const micLabel = busy
    ? "正在识别语音"
    : listening
      ? "停止语音输入"
      : recording
        ? "停止录音并识别"
        : "语音输入";

  return (
    <div className="w-full max-w-[820px] mx-auto flex gap-2.5 items-center bg-surface-muted border border-border rounded-[20px] px-[18px] py-2.5 shadow-sm transition-all focus-within:border-brand focus-within:shadow-[0_2px_16px_rgba(21,101,192,0.12)]">
      <textarea
        ref={ref}
        rows={1}
        value={displayValue}
        placeholder={placeholder}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={streaming || busy}
        className="flex-1 border-none outline-none resize-none text-[15px] leading-relaxed min-h-6 max-h-[200px] font-[inherit] bg-transparent placeholder:text-text-muted disabled:opacity-50"
      />
      <button
        type="button"
        aria-label={micLabel}
        title={micLabel}
        onClick={toggleSpeech}
        disabled={streaming || busy}
        className={`border-none rounded-xl p-2 shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
          active
            ? "bg-error/15 text-error animate-pulse"
            : "bg-transparent text-text-muted hover:text-brand hover:bg-brand/8"
        }`}
      >
        {listening || recording ? (
          <Square className="w-[18px] h-[18px]" aria-hidden />
        ) : (
          <Mic className="w-[18px] h-[18px]" aria-hidden />
        )}
      </button>
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
          disabled={!value.trim() || busy}
          className="border-none bg-brand text-white rounded-xl px-[18px] py-2 text-sm font-medium cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          发送
        </button>
      )}
    </div>
  );
}
