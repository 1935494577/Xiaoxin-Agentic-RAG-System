import { useEffect, useRef, useState, type RefObject } from "react";

type PupilProps = {
  size?: number;
  maxDistance?: number;
  pupilColor?: string;
  forceLookX?: number;
  forceLookY?: number;
};

export function Pupil({
  size = 12,
  maxDistance = 5,
  pupilColor = "#2D2D2D",
  forceLookX,
  forceLookY,
}: PupilProps) {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const pupilRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  const pos = (() => {
    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }
    if (!pupilRef.current) return { x: 0, y: 0 };
    const r = pupilRef.current.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const dx = mouseX - cx;
    const dy = mouseY - cy;
    const dist = Math.min(Math.hypot(dx, dy), maxDistance);
    const angle = Math.atan2(dy, dx);
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist };
  })();

  return (
    <div
      ref={pupilRef}
      className="rounded-full transition-transform duration-100 ease-out"
      style={{
        width: size,
        height: size,
        backgroundColor: pupilColor,
        transform: `translate(${pos.x}px, ${pos.y}px)`,
      }}
    />
  );
}

type EyeBallProps = {
  size?: number;
  pupilSize?: number;
  maxDistance?: number;
  eyeColor?: string;
  pupilColor?: string;
  isBlinking?: boolean;
  forceLookX?: number;
  forceLookY?: number;
};

export function EyeBall({
  size = 48,
  pupilSize = 16,
  maxDistance = 10,
  eyeColor = "white",
  pupilColor = "#2D2D2D",
  isBlinking = false,
  forceLookX,
  forceLookY,
}: EyeBallProps) {
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const eyeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      setMouseX(e.clientX);
      setMouseY(e.clientY);
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  const pos = (() => {
    if (forceLookX !== undefined && forceLookY !== undefined) {
      return { x: forceLookX, y: forceLookY };
    }
    if (!eyeRef.current) return { x: 0, y: 0 };
    const r = eyeRef.current.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const dx = mouseX - cx;
    const dy = mouseY - cy;
    const dist = Math.min(Math.hypot(dx, dy), maxDistance);
    const angle = Math.atan2(dy, dx);
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist };
  })();

  return (
    <div
      ref={eyeRef}
      className="flex items-center justify-center rounded-full transition-all duration-150"
      style={{
        width: size,
        height: isBlinking ? 2 : size,
        backgroundColor: eyeColor,
        overflow: "hidden",
      }}
    >
      {!isBlinking && (
        <div
          className="rounded-full transition-transform duration-100 ease-out"
          style={{
            width: pupilSize,
            height: pupilSize,
            backgroundColor: pupilColor,
            transform: `translate(${pos.x}px, ${pos.y}px)`,
          }}
        />
      )}
    </div>
  );
}

type FacePos = { faceX: number; faceY: number; bodySkew: number };

function useMousePosition() {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => setMouse({ x: e.clientX, y: e.clientY });
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);
  return mouse;
}

function calcFacePos(
  ref: RefObject<HTMLDivElement | null>,
  mouseX: number,
  mouseY: number
): FacePos {
  if (!ref.current) return { faceX: 0, faceY: 0, bodySkew: 0 };
  const rect = ref.current.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 3;
  const dx = mouseX - cx;
  const dy = mouseY - cy;
  return {
    faceX: Math.max(-15, Math.min(15, dx / 20)),
    faceY: Math.max(-10, Math.min(10, dy / 30)),
    bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
  };
}

function useBlink() {
  const [blinking, setBlinking] = useState(false);
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const schedule = () => {
      timeout = setTimeout(
        () => {
          setBlinking(true);
          setTimeout(() => {
            setBlinking(false);
            schedule();
          }, 150);
        },
        Math.random() * 4000 + 3000
      );
    };
    schedule();
    return () => clearTimeout(timeout);
  }, []);
  return blinking;
}

export type AnimatedCharacterMascotsProps = {
  isTyping: boolean;
  password: string;
  showPassword: boolean;
};

export function AnimatedCharacterMascots({
  isTyping,
  password,
  showPassword,
}: AnimatedCharacterMascotsProps) {
  const { x: mouseX, y: mouseY } = useMousePosition();
  const purpleRef = useRef<HTMLDivElement>(null);
  const blackRef = useRef<HTMLDivElement>(null);
  const orangeRef = useRef<HTMLDivElement>(null);
  const yellowRef = useRef<HTMLDivElement>(null);
  const tealRef = useRef<HTMLDivElement>(null);

  const isPurpleBlinking = useBlink();
  const isBlackBlinking = useBlink();
  const isTealBlinking = useBlink();
  const [isLookingAtEachOther, setIsLookingAtEachOther] = useState(false);
  const [isPurplePeeking, setIsPurplePeeking] = useState(false);

  const hidingPassword = password.length > 0 && !showPassword;
  const revealingPassword = password.length > 0 && showPassword;

  useEffect(() => {
    if (!isTyping) {
      setIsLookingAtEachOther(false);
      return;
    }
    setIsLookingAtEachOther(true);
    const t = setTimeout(() => setIsLookingAtEachOther(false), 800);
    return () => clearTimeout(t);
  }, [isTyping]);

  useEffect(() => {
    if (!revealingPassword) {
      setIsPurplePeeking(false);
      return;
    }
    let peekEnd: ReturnType<typeof setTimeout> | undefined;
    const peekStart = setTimeout(() => {
      setIsPurplePeeking(true);
      peekEnd = setTimeout(() => setIsPurplePeeking(false), 800);
    }, Math.random() * 2000 + 1500);
    return () => {
      clearTimeout(peekStart);
      if (peekEnd) clearTimeout(peekEnd);
    };
  }, [revealingPassword]);

  const purplePos = calcFacePos(purpleRef, mouseX, mouseY);
  const blackPos = calcFacePos(blackRef, mouseX, mouseY);
  const orangePos = calcFacePos(orangeRef, mouseX, mouseY);
  const yellowPos = calcFacePos(yellowRef, mouseX, mouseY);
  const tealPos = calcFacePos(tealRef, mouseX, mouseY);

  return (
    <div className="relative" style={{ width: "640px", height: "400px" }}>
      {/* Purple tall rectangle */}
      <div
        ref={purpleRef}
        className="absolute bottom-0 transition-all duration-700 ease-in-out"
        style={{
          left: "55px",
          width: "170px",
          height: isTyping || hidingPassword ? "440px" : "400px",
          backgroundColor: "#6C3FF5",
          borderRadius: "10px 10px 0 0",
          zIndex: 1,
          transform: revealingPassword
            ? "skewX(0deg)"
            : isTyping || hidingPassword
              ? `skewX(${(purplePos.bodySkew || 0) - 12}deg) translateX(40px)`
              : `skewX(${purplePos.bodySkew || 0}deg)`,
          transformOrigin: "bottom center",
        }}
      >
        <div
          className="absolute flex gap-8 transition-all duration-700 ease-in-out"
          style={{
            left: revealingPassword
              ? "20px"
              : isLookingAtEachOther
                ? "55px"
                : `${45 + purplePos.faceX}px`,
            top: revealingPassword
              ? "35px"
              : isLookingAtEachOther
                ? "65px"
                : `${40 + purplePos.faceY}px`,
          }}
        >
          <EyeBall
            size={18}
            pupilSize={7}
            maxDistance={5}
            isBlinking={isPurpleBlinking}
            forceLookX={
              revealingPassword
                ? isPurplePeeking
                  ? 4
                  : -4
                : isLookingAtEachOther
                  ? 3
                  : undefined
            }
            forceLookY={
              revealingPassword
                ? isPurplePeeking
                  ? 5
                  : -4
                : isLookingAtEachOther
                  ? 4
                  : undefined
            }
          />
          <EyeBall
            size={18}
            pupilSize={7}
            maxDistance={5}
            isBlinking={isPurpleBlinking}
            forceLookX={
              revealingPassword
                ? isPurplePeeking
                  ? 4
                  : -4
                : isLookingAtEachOther
                  ? 3
                  : undefined
            }
            forceLookY={
              revealingPassword
                ? isPurplePeeking
                  ? 5
                  : -4
                : isLookingAtEachOther
                  ? 4
                  : undefined
            }
          />
        </div>
      </div>

      {/* Black tall rectangle */}
      <div
        ref={blackRef}
        className="absolute bottom-0 transition-all duration-700 ease-in-out"
        style={{
          left: "215px",
          width: "110px",
          height: "310px",
          backgroundColor: "#2D2D2D",
          borderRadius: "8px 8px 0 0",
          zIndex: 2,
          transform: revealingPassword
            ? "skewX(0deg)"
            : isLookingAtEachOther
              ? `skewX(${(blackPos.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
              : isTyping || hidingPassword
                ? `skewX(${(blackPos.bodySkew || 0) * 1.5}deg)`
                : `skewX(${blackPos.bodySkew || 0}deg)`,
          transformOrigin: "bottom center",
        }}
      >
        <div
          className="absolute flex gap-6 transition-all duration-700 ease-in-out"
          style={{
            left: revealingPassword
              ? "10px"
              : isLookingAtEachOther
                ? "32px"
                : `${26 + blackPos.faceX}px`,
            top: revealingPassword
              ? "28px"
              : isLookingAtEachOther
                ? "12px"
                : `${32 + blackPos.faceY}px`,
          }}
        >
          <EyeBall
            size={16}
            pupilSize={6}
            maxDistance={4}
            isBlinking={isBlackBlinking}
            forceLookX={revealingPassword ? -4 : isLookingAtEachOther ? 0 : undefined}
            forceLookY={revealingPassword ? -4 : isLookingAtEachOther ? -4 : undefined}
          />
          <EyeBall
            size={16}
            pupilSize={6}
            maxDistance={4}
            isBlinking={isBlackBlinking}
            forceLookX={revealingPassword ? -4 : isLookingAtEachOther ? 0 : undefined}
            forceLookY={revealingPassword ? -4 : isLookingAtEachOther ? -4 : undefined}
          />
        </div>
      </div>

      {/* Orange semi-circle */}
      <div
        ref={orangeRef}
        className="absolute bottom-0 transition-all duration-700 ease-in-out"
        style={{
          left: "0px",
          width: "240px",
          height: "200px",
          zIndex: 3,
          backgroundColor: "#FF9B6B",
          borderRadius: "120px 120px 0 0",
          transform: revealingPassword
            ? "skewX(0deg)"
            : `skewX(${orangePos.bodySkew || 0}deg)`,
          transformOrigin: "bottom center",
        }}
      >
        <div
          className="absolute flex gap-8 transition-all duration-200 ease-out"
          style={{
            left: revealingPassword ? "50px" : `${82 + (orangePos.faceX || 0)}px`,
            top: revealingPassword ? "85px" : `${90 + (orangePos.faceY || 0)}px`,
          }}
        >
          <Pupil
            size={12}
            maxDistance={5}
            forceLookX={revealingPassword ? -5 : undefined}
            forceLookY={revealingPassword ? -4 : undefined}
          />
          <Pupil
            size={12}
            maxDistance={5}
            forceLookX={revealingPassword ? -5 : undefined}
            forceLookY={revealingPassword ? -4 : undefined}
          />
        </div>
      </div>

      {/* Yellow rounded rectangle */}
      <div
        ref={yellowRef}
        className="absolute bottom-0 transition-all duration-700 ease-in-out"
        style={{
          left: "285px",
          width: "130px",
          height: "230px",
          backgroundColor: "#E8D754",
          borderRadius: "70px 70px 0 0",
          zIndex: 4,
          transform: revealingPassword
            ? "skewX(0deg)"
            : `skewX(${yellowPos.bodySkew || 0}deg)`,
          transformOrigin: "bottom center",
        }}
      >
        <div
          className="absolute flex gap-6 transition-all duration-200 ease-out"
          style={{
            left: revealingPassword ? "20px" : `${52 + (yellowPos.faceX || 0)}px`,
            top: revealingPassword ? "35px" : `${40 + (yellowPos.faceY || 0)}px`,
          }}
        >
          <Pupil
            size={12}
            maxDistance={5}
            forceLookX={revealingPassword ? -5 : undefined}
            forceLookY={revealingPassword ? -4 : undefined}
          />
          <Pupil
            size={12}
            maxDistance={5}
            forceLookX={revealingPassword ? -5 : undefined}
            forceLookY={revealingPassword ? -4 : undefined}
          />
        </div>
        <div
          className="absolute h-1 w-20 rounded-full bg-[#2D2D2D] transition-all duration-200 ease-out"
          style={{
            left: revealingPassword ? "10px" : `${40 + (yellowPos.faceX || 0)}px`,
            top: revealingPassword ? "88px" : `${88 + (yellowPos.faceY || 0)}px`,
          }}
        />
      </div>

      {/* Teal capsule — front right */}
      <div
        ref={tealRef}
        className="absolute bottom-0 transition-all duration-700 ease-in-out"
        style={{
          left: "455px",
          width: "100px",
          height: "195px",
          backgroundColor: "#42B8A8",
          borderRadius: "50px 50px 0 0",
          zIndex: 5,
          transform: revealingPassword
            ? "skewX(0deg)"
            : isTyping
              ? `skewX(${(tealPos.bodySkew || 0) * 1.2}deg) translateX(-8px)`
              : `skewX(${tealPos.bodySkew || 0}deg)`,
          transformOrigin: "bottom center",
        }}
      >
        <div
          className="absolute flex gap-4 transition-all duration-200 ease-out"
          style={{
            left: revealingPassword ? "18px" : `${30 + (tealPos.faceX || 0)}px`,
            top: revealingPassword ? "32px" : `${36 + (tealPos.faceY || 0)}px`,
          }}
        >
          <EyeBall
            size={14}
            pupilSize={5}
            maxDistance={4}
            isBlinking={isTealBlinking}
            forceLookX={revealingPassword ? -4 : undefined}
            forceLookY={revealingPassword ? -3 : undefined}
          />
          <EyeBall
            size={14}
            pupilSize={5}
            maxDistance={4}
            isBlinking={isTealBlinking}
            forceLookX={revealingPassword ? -4 : undefined}
            forceLookY={revealingPassword ? -3 : undefined}
          />
        </div>
        <div
          className="absolute h-1 w-10 rounded-full bg-[#2D2D2D] transition-all duration-200 ease-out"
          style={{
            left: revealingPassword ? "22px" : `${34 + (tealPos.faceX || 0)}px`,
            top: revealingPassword ? "72px" : `${76 + (tealPos.faceY || 0)}px`,
          }}
        />
      </div>
    </div>
  );
}

/** @deprecated use AnimatedCharacterMascots */
export const AnimatedLetterMascots = AnimatedCharacterMascots;
export type AnimatedLetterMascotsProps = AnimatedCharacterMascotsProps;
