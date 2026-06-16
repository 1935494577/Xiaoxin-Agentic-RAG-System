import { Outlet, useLocation } from "react-router-dom";

import { ShaderAnimation } from "@/components/ui/shader-lines";

import { cn } from "@/lib/utils";



/** Shared warm education backdrop for welcome → login flow */

export default function AuthEntryLayout() {

  const { pathname } = useLocation();

  const isLogin = pathname === "/login";



  return (

    <div

      className={cn(

        "auth-entry-root relative min-h-dvh overflow-hidden",

        isLogin ? "bg-[#faf8f5]" : "bg-[#0c1628]"

      )}

    >

      {isLogin ? (

        <div className="pointer-events-none absolute inset-y-0 left-0 z-0 hidden w-1/2 overflow-hidden bg-[#0c1628] lg:block">

          <div className="auth-login-shader absolute inset-0 opacity-[0.38]">
            <ShaderAnimation />
          </div>

          <div className="auth-login-warm-glow absolute inset-0" />

          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(255,171,145,0.14)_0%,transparent_55%)]" />

          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_90%,rgba(66,184,168,0.12)_0%,transparent_50%)]" />

          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#0c1628_78%)]" />

        </div>

      ) : (

        <>

          <ShaderAnimation />

          <div className="auth-welcome-warm-glow pointer-events-none absolute inset-0 z-[1]" />

          <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(ellipse_at_50%_0%,rgba(255,213,79,0.08)_0%,transparent_45%)]" />

          <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(ellipse_at_80%_100%,rgba(66,184,168,0.1)_0%,transparent_40%)]" />

          <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_center,transparent_0%,#0c1628_72%)]" />

          <div className="auth-welcome-floats pointer-events-none absolute inset-0 z-[1]" aria-hidden />

        </>

      )}

      <div

        className={cn(

          "relative z-10 min-h-dvh transition-opacity duration-700 ease-out",

          isLogin ? "auth-route-login" : "auth-route-welcome"

        )}

      >

        <Outlet />

      </div>

    </div>

  );

}

