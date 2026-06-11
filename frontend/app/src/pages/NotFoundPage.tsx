import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex items-center justify-center h-full bg-surface-muted">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-text-muted mb-4">404</h1>
        <p className="text-text-muted mb-6">页面未找到</p>
        <Link
          to="/"
          className="inline-flex items-center px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors"
        >
          返回对话
        </Link>
      </div>
    </div>
  );
}
