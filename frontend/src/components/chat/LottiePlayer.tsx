import { useEffect, useRef, useState } from "react";
import { DotLottie } from "@lottiefiles/dotlottie-web";

type Props = {
  animationData: string;
  loop?: boolean;
  className?: string;
};

export default function LottiePlayer({ animationData, loop = true, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      const dotLottie = new DotLottie({
        canvas,
        data: animationData,
        loop,
        autoplay: true,
      });

      return () => dotLottie.destroy();
    } catch (e) {
      console.error("[LottiePlayer] DotLottie init failed:", e);
      setError(true);
    }
  }, [animationData, loop]);

  if (error) {
    return <span className="dot-wave-fallback"><span /><span /><span /></span>;
  }

  return <canvas ref={canvasRef} className={className} />;
}
