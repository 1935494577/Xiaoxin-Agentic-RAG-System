import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const REVEAL_MS = 2000;
const BUTTON_DELAY_MS = 600;
const EXIT_MS = 700;

export default function WelcomePage() {
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => setShowLogin(true), REVEAL_MS + BUTTON_DELAY_MS);
    return () => window.clearTimeout(t);
  }, []);

  function goLogin() {
    if (exiting) return;
    setExiting(true);
    window.setTimeout(() => {
      navigate("/login", { state: { fromWelcome: true } });
    }, EXIT_MS);
  }

  return (
    <div
      className={cn(
        "relative flex h-screen w-full flex-col items-center justify-center",
        exiting && "auth-welcome-exit"
      )}
    >
      <div className="relative z-10 h-full w-full px-6">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 auth-welcome-title">
          <span className="welcome-stream-title inline-flex items-baseline select-none whitespace-nowrap">
            <span className="text-7xl font-semibold tracking-tighter text-white md:text-8xl">
              <span className="text-[#e53935]">J</span>nao
            </span>
            <span className="ml-1 text-xl font-medium tracking-wide text-white/90 md:text-2xl">
              劲脑
            </span>
          </span>
        </div>

        <div
          className={cn(
            "auth-welcome-cta absolute left-1/2 top-[62%] -translate-x-1/2 transition-all duration-700 ease-out",
            showLogin
              ? "translate-y-0 opacity-100"
              : "pointer-events-none translate-y-6 opacity-0"
          )}
        >
          <Button
            type="button"
            variant="ghost"
            className={cn(
              "pointer-events-auto h-11 min-w-[168px] px-8 text-base",
              "border border-white/12 bg-[#0c1524] text-white/88",
              "hover:bg-[#152238] hover:text-white hover:border-white/18"
            )}
            onClick={goLogin}
            disabled={exiting}
          >
            登录
          </Button>
        </div>
      </div>
    </div>
  );
}
