type Props = {
  title: string;
  description?: string;
};

export function PlaceholderPage({ title, description }: Props) {
  return (
    <div className="p-8">
      <h1 className="text-lg font-semibold text-text mb-2">{title}</h1>
      {description && <p className="text-text-muted text-sm">{description}</p>}
      <div className="mt-8 p-12 rounded-xl border-2 border-dashed border-border text-center text-text-muted">
        <p className="text-sm">此页面正在开发中</p>
        <p className="text-xs mt-1">将逐步从 Streamlit 迁移至此</p>
      </div>
    </div>
  );
}
