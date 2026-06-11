type Props = {
  enabled: boolean;
  onChange: (on: boolean) => void;
  disabled?: boolean;
};

export function HybridToggle({ enabled, onChange, disabled }: Props) {
  return (
    <label className="inline-flex items-center gap-2.5 cursor-pointer select-none" title="开启后优先检索知识库，未命中时自动使用通用能力">
      <span className="text-[13px] text-text font-medium">混合专家模式</span>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        disabled={disabled}
        onClick={() => onChange(!enabled)}
        className={
          "relative w-10 h-[22px] rounded-full transition-colors flex-shrink-0 p-0 border-none cursor-pointer " +
          (enabled ? "bg-brand" : "bg-[#d1d5db]") +
          (disabled ? " opacity-50 cursor-not-allowed" : "")
        }
      >
        <span
          className={
            "absolute top-0.5 left-0.5 w-[18px] h-[18px] rounded-full bg-white shadow-sm transition-transform " +
            (enabled ? "translate-x-[18px]" : "")
          }
        />
      </button>
      <span className="text-xs text-text-muted">
        {enabled ? "知识库优先 · 可补充通用回答" : "仅知识库检索"}
      </span>
    </label>
  );
}
