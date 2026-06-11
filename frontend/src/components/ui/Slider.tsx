import { cn } from "../../lib/utils";

type Props = {
  value: number;
  onChange: (val: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  id?: string;
};

export function Slider({ value, onChange, min = 0, max = 100, step = 1, disabled, id }: Props) {
  return (
    <input
      id={id}
      type="range"
      value={value}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      onChange={(e) => onChange(Number(e.target.value))}
      className={cn(
        "w-full h-2 rounded-full appearance-none bg-border cursor-pointer",
        "accent-brand",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    />
  );
}
