import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Brain, ShieldCheck, TrendingUp } from "lucide-react";
import { GlassButton } from "@/components/ui/glass-button";
import { cn } from "@/lib/utils";

const REVEAL_MS = 2000;
const TAGLINE_DELAY_MS = 400;
const CTA_DELAY_MS = 250;
const EXIT_MS = 700;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const VALUE_PILLS = [
  { icon: Brain, label: "脑科训练" },
  { icon: TrendingUp, label: "科学提分" },
  { icon: ShieldCheck, label: "部门权限" },
] as const;

export default function WelcomePage() {
  const navigate = useNavigate();
  const [showTagline, setShowTagline] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const reduced = prefersReducedMotion();
    if (reduced) {
      setShowTagline(true);
      setShowLogin(true);
      return;
    }
    const taglineTimer = window.setTimeout(
      () => setShowTagline(true),
      REVEAL_MS + TAGLINE_DELAY_MS
    );
    const ctaTimer = window.setTimeout(
      () => setShowLogin(true),
      REVEAL_MS + TAGLINE_DELAY_MS + CTA_DELAY_MS
    );
    return () => {
      window.clearTimeout(taglineTimer);
      window.clearTimeout(ctaTimer);
    };
  }, []);

  function goLogin() {
    if (exiting) return;
    setExiting(true);
    window.setTimeout(() => {
      navigate("/login", { state: { fromWelcome: true } });
    }, EXIT_MS);
  }

  return (
    <main
      className={cn(
        "relative flex min-h-dvh w-full flex-col items-center justify-center",
        exiting && "auth-welcome-exit"
      )}
    >
      <div className="relative z-10 flex min-h-dvh w-full max-w-3xl flex-col items-center justify-center px-6 py-12">
        <div className="flex flex-col items-center gap-8 md:gap-10">
          <div className="auth-welcome-title text-center">
            <span className="welcome-stream-title inline-flex items-baseline select-none whitespace-nowrap">
              <span className="text-8xl font-semibold tracking-tighter text-white sm:text-9xl md:text-[9.5rem]">
                <span className="text-[#ff8a65]">J</span>nao
              </span>
              <span className="ml-2 text-2xl font-medium tracking-wide text-white/90 sm:text-3xl md:text-4xl">
                劲脑
              </span>
            </span>
          </div>

          <div
            className={cn(
              "auth-welcome-tagline flex max-w-lg flex-col items-center gap-4 text-center transition-all duration-700 ease-out",
              showTagline
                ? "translate-y-0 opacity-100"
                : "pointer-events-none translate-y-4 opacity-0"
            )}
          >
            <p className="text-balance text-lg font-medium leading-relaxed text-white/92 sm:text-xl">
              以脑科训练为基，助力孩子科学提分
            </p>
            <p className="text-pretty text-sm leading-relaxed text-white/65 sm:text-base">
              劲脑内部工作平台 · 按部门开放功能权限
            </p>
            <ul className="mt-1 flex flex-wrap items-center justify-center gap-2.5">
              {VALUE_PILLS.map(({ icon: Icon, label }) => (
                <li
                  key={label}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/[0.07] px-3.5 py-1.5 text-xs font-medium text-white/80 backdrop-blur-sm sm:text-sm"
                >
                  <Icon className="h-3.5 w-3.5 text-[#ffd54f]" aria-hidden />
                  {label}
                </li>
              ))}
            </ul>
          </div>

          <div
            className={cn(
              "auth-welcome-cta flex justify-center transition-all duration-700 ease-out",
              showLogin
                ? "translate-y-0 opacity-100"
                : "pointer-events-none translate-y-6 opacity-0"
            )}
          >
            <GlassButton
              type="button"
              size="lg"
              className="pointer-events-auto"
              contentClassName="min-w-[9.5rem] px-9 py-4 text-lg font-medium"
              onClick={goLogin}
              disabled={exiting}
            >
              员工登录
            </GlassButton>
          </div>
        </div>
      </div>
    </main>
  );
}
