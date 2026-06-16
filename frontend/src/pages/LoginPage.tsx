import { type FormEvent, useEffect, useState } from "react";

import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { ArrowLeft, ArrowRight, Brain, Eye, EyeOff, Lock, User } from "lucide-react";

import { toast } from "sonner";

import { saveUserProfile } from "../api/client";

import { TalentEditorialMascots } from "@/components/ui/talent-editorial-mascots";

import { Button } from "@/components/ui/Button";

import { Input } from "@/components/ui/Input";

import { Label } from "@/components/ui/Label";

import { Select } from "@/components/ui/Select";

import { useAuth } from "../hooks/useAuth";

import { DEPT_OPTIONS } from "../lib/constants";

import { cn } from "@/lib/utils";



const HIGHLIGHTS = [

  "脑科训练方案与学员成长数据一站查询",

  "按部门配置功能权限，保障信息安全",

  "智能助手辅助答疑、备课与知识检索",

] as const;



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

        "auth-login-shell min-h-dvh grid lg:grid-cols-2",

        entered && "auth-login-entered"

      )}

    >

      <section className="relative hidden lg:flex flex-col justify-between overflow-hidden px-12 py-10 text-white">

        <div className="auth-login-pattern absolute inset-0 opacity-40" />

        <div className="auth-login-brand relative z-10 flex items-center gap-3">

          <img src="/company_logo.png" alt="Jnao 劲脑" className="h-9 w-auto brightness-0 invert" />

          <div>

            <p className="text-lg font-semibold tracking-wide">

              <span className="text-[#ffab91]">J</span>nao

              <span className="ml-1 text-sm font-medium text-white/80">劲脑</span>

            </p>

            <p className="text-sm text-white/70">脑科教育 · 内部工作平台</p>

          </div>

        </div>



        <div className="auth-login-story relative z-10 max-w-md lg:max-w-sm xl:max-w-md">

          <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">

            <Brain className="h-5 w-5 text-[#ffd54f]" aria-hidden />

          </div>

          <h2 className="text-balance text-3xl font-semibold leading-tight tracking-tight">

            用科学方法，让每一点进步可测量

          </h2>

          <p className="mt-4 text-pretty text-base leading-relaxed text-white/75">

            劲脑以脑科训练为核心，帮助学员夯实认知基础、稳步提升成绩。这里是团队日常协作与业务支撑的统一入口。

          </p>

          <ul className="mt-6 space-y-3">

            {HIGHLIGHTS.map((item) => (

              <li

                key={item}

                className="flex items-start gap-2.5 text-sm leading-relaxed text-white/70"

              >

                <span

                  className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#ffd54f]"

                  aria-hidden

                />

                {item}

              </li>

            ))}

          </ul>

        </div>



        <div className="auth-login-mascots relative z-10 flex min-h-[280px] flex-1 items-end justify-center overflow-visible px-2 pb-4 pt-1">

          <TalentEditorialMascots

            isTyping={isTyping}

            password={password}

            showPassword={showPassword}

          />

        </div>



        <p className="auth-login-footer relative z-10 text-xs text-white/45">

          © Jnao · 脑科教育内部系统

        </p>

      </section>



      <section className="auth-login-form flex items-center justify-center bg-[#faf8f5] px-6 py-10">

        <div className="w-full max-w-[420px]">

          <Link

            to="/"

            className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-text-muted transition-colors hover:text-brand lg:hidden"

          >

            <ArrowLeft className="h-4 w-4" aria-hidden />

            返回欢迎页

          </Link>



          <div className="mb-8 flex items-center gap-2 lg:hidden">

            <img src="/company_logo.png" alt="Jnao 劲脑" className="h-8 w-auto" />

            <span className="text-lg font-semibold text-brand">Jnao 劲脑</span>

          </div>



          <div className="rounded-2xl border border-[#ebe6df] bg-white p-8 shadow-[0_8px_32px_-12px_rgba(21,101,192,0.12)]">

            <div className="mb-8">

              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-light text-brand">

                <Lock className="h-5 w-5" aria-hidden />

              </div>

              <h1 className="text-2xl font-semibold text-text">员工登录</h1>

              <p className="mt-1.5 text-pretty text-sm leading-relaxed text-text-muted">

                使用内部账号登录，系统将根据所选部门开放对应功能权限

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

                    placeholder="请输入工号或姓名"

                    value={username}

                    onChange={(e) => setUsername(e.target.value)}

                    onFocus={() => setIsTyping(true)}

                    onBlur={() => setIsTyping(false)}

                    className="h-11 border-[#e8e2d9] bg-[#fdfcfa] pl-9 focus:border-brand/40"

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

                    className="h-11 border-[#e8e2d9] bg-[#fdfcfa] pl-9 pr-10 focus:border-brand/40"

                  />

                  <button

                    type="button"

                    onClick={() => setShowPassword((v) => !v)}

                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted transition-colors hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30 rounded"

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

                <Label htmlFor="department">所属部门</Label>

                <p className="mb-1.5 text-xs text-text-muted">

                  不同部门可使用的管理功能与数据范围可能不同

                </p>

                <Select

                  id="department"

                  value={department}

                  onChange={(e) => setDepartment(e.target.value)}

                  className="h-11 border-[#e8e2d9] bg-[#fdfcfa] focus:border-brand/40"

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

                className="h-11 w-full text-base shadow-[0_4px_14px_-4px_rgba(21,101,192,0.45)] transition-transform active:scale-[0.98]"

                disabled={submitting}

              >

                {submitting ? "登录中…" : "进入工作台"}

                {!submitting && <ArrowRight className="h-4 w-4" />}

              </Button>

            </form>



            <p className="mt-6 text-center text-xs leading-relaxed text-text-muted">

              开发环境暂未接入 SSO，任意密码即可登录。

            </p>

          </div>



          <p className="mt-6 text-center text-sm text-text-muted">

            暂不登录？{" "}

            <Link

              to="/chat"

              className="font-medium text-brand transition-colors hover:text-brand-dark"

            >

              仅体验对话功能

            </Link>

          </p>

        </div>

      </section>

    </div>

  );

}

