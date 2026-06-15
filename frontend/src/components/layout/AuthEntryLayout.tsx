import { Outlet, useLocation } from "react-router-dom";
import { ShaderAnimation } from "@/components/ui/shader-lines";
import { cn } from "@/lib/utils";

/** Shared dark + shader backdrop for welcome → login flow */
export default function AuthEntryLayout() {
  const { pathname } = useLocation();
  const isLogin = pathname === "/login";

  return (
    <div
      className={cn(
        "relative min-h-screen overflow-hidden",
        isLogin ? "bg-surface-muted" : "bg-[#050a14]"
      )}
    >
      {isLogin ? (
        <>
          <div className="pointer-events-none absolute inset-y-0 left-0 z-0 hidden w-1/2 overflow-hidden bg-[#050a14] lg:block">
            <ShaderAnimation />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#050a14_72%)]" />
          </div>
        </>
      ) : (
        <>
          <ShaderAnimation />
          <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_center,transparent_0%,#050a14_72%)]" />
        </>
      )}
      <div
        className={cn(
          "relative z-10 min-h-screen transition-opacity duration-700 ease-out",
          isLogin ? "auth-route-login" : "auth-route-welcome"
        )}
      >
        <Outlet />
      </div>
    </div>
  );
}
