import { type FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Lock, User } from "lucide-react";
import { toast } from "sonner";
import { saveUserProfile } from "../api/client";
import { AnimatedCharacterMascots } from "@/components/ui/animated-characters-login-page";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { useAuth } from "../hooks/useAuth";
import { DEPT_OPTIONS } from "../lib/constants";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { userId, login } = useAuth();
  const fromWelcome = Boolean(
    (location.state as { fromWelcome?: boolean } | null)?.fromWelcome
  );

  const [entered, setEntered] = useState(!fromWelcome);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [department, setDepartment] = useState<string>(DEPT_OPTIONS[0]);
  const [remember, setRemember] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const returnTo = searchParams.get("from") || "/chat";

  useEffect(() => {
    if (!fromWelcome) {
      setEntered(true);
      return;
    }
    const id = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(id);
  }, [fromWelcome]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const name = username.trim();
    if (!name) {
      toast.error("请输入用户名");
      return;
    }
    if (!password) {
      toast.error("请输入密码");
      return;
    }

    setSubmitting(true);
    try {
      login(name, department, remember);
      try {
        await saveUserProfile({
          user_id: userId,
          display_name: name,
          department,
        });
      } catch {
        toast.warning("登录成功，但个人资料同步失败，可在侧边栏稍后重试");
      }
      toast.success(`欢迎回来，${name}`);
      navigate(returnTo, { replace: true });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className={cn(
        "auth-login-shell min-h-screen grid lg:grid-cols-2",
        entered && "auth-login-entered"
      )}
    >
      {/* Left — animated mascots (shared shader from layout) */}
      <section className="relative hidden lg:flex flex-col justify-between overflow-hidden px-12 py-10 text-white">
        <div className="absolute inset-0 bg-grid-white/[0.04] bg-[size:20px_20px]" />
        <div className="auth-login-brand relative z-10 flex items-center gap-3">
          <img src="/company_logo.png" alt="Logo" className="h-9 w-auto brightness-0 invert" />
          <div>
            <p className="text-lg font-semibold tracking-wide">
              <span className="text-[#ff8a80]">J</span>nao
              <span className="ml-1 text-sm font-medium text-white/80">劲脑</span>
            </p>
            <p className="text-sm text-white/70">Enterprise RAG Platform</p>
          </div>
        </div>

        <div className="auth-login-mascots relative z-10 flex flex-1 items-end justify-center pb-6">
          <AnimatedCharacterMascots
            isTyping={isTyping}
            password={password}
            showPassword={showPassword}
          />
        </div>

        <p className="auth-login-footer relative z-10 text-xs text-white/50">© Jnao · 内部知识平台</p>
      </section>

      {/* Right — form */}
      <section className="auth-login-form flex items-center justify-center bg-surface-muted px-6 py-10">
        <div className="w-full max-w-[420px]">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <img src="/company_logo.png" alt="Logo" className="h-8 w-auto" />
            <span className="text-lg font-semibold text-brand">Jnao 知识库</span>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-8 shadow-sm">
            <div className="mb-8">
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-light text-brand">
                <Lock className="h-5 w-5" />
              </div>
              <h1 className="text-2xl font-semibold text-text">登录账号</h1>
              <p className="mt-1.5 text-sm text-text-muted">
                使用内部账号访问管理后台与个性化对话
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <Label htmlFor="username">用户名</Label>
                <div className="relative">
                  <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                  <Input
                    id="username"
                    autoComplete="username"
                    placeholder="请输入用户名"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    onFocus={() => setIsTyping(true)}
                    onBlur={() => setIsTyping(false)}
                    className="h-11 pl-9"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password">密码</Label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="请输入密码"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 pl-9 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors hover:text-text"
                    aria-label={showPassword ? "隐藏密码" : "显示密码"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <Label htmlFor="department">部门</Label>
                <Select
                  id="department"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="h-11"
                >
                  {DEPT_OPTIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </Select>
              </div>

              <label className="flex cursor-pointer select-none items-center gap-2 text-sm text-text-muted">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-brand focus:ring-brand/30"
                />
                记住登录状态
              </label>

              <Button
                type="submit"
                variant="primary"
                className="h-11 w-full text-base"
                disabled={submitting}
              >
                {submitting ? "登录中…" : "登录"}
                {!submitting && <ArrowRight className="h-4 w-4" />}
              </Button>
            </form>

            <p className="mt-6 text-center text-xs text-text-muted">
              开发环境暂未接入 SSO，任意密码即可登录。
            </p>
          </div>

          <p className="mt-6 text-center text-sm text-text-muted">
            仅使用对话功能？{" "}
            <Link to="/chat" className="font-medium text-brand hover:text-brand-dark">
              继续匿名访问
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
