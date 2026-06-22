/** Browser speech recognition helpers (Web Speech API + transcript merge). */

export type SpeechRecognitionErrorCode =
  | "not-supported"
  | "not-allowed"
  | "no-speech"
  | "network"
  | "aborted"
  | "unknown";

export type SpeechRecognitionResultList = {
  length: number;
  [index: number]: {
    isFinal: boolean;
    0: { transcript: string };
  };
};

export type SpeechRecognitionEvent = {
  resultIndex: number;
  results: SpeechRecognitionResultList;
};

export type SpeechRecognitionErrorEvent = {
  error: string;
};

export type BrowserSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

declare global {
  interface Window {
    SpeechRecognition?: new () => BrowserSpeechRecognition;
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
  }
}

export function getBrowserSpeechRecognitionCtor():
  | (new () => BrowserSpeechRecognition)
  | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function isBrowserSpeechRecognitionSupported(): boolean {
  return getBrowserSpeechRecognitionCtor() != null;
}

export function appendFinalTranscript(base: string, chunk: string): string {
  const left = (base || "").trimEnd();
  const right = (chunk || "").trim();
  if (!right) return base || "";
  if (!left) return right;
  return `${left} ${right}`;
}

export function mergeDisplayTranscript(base: string, interim: string): string {
  const b = base || "";
  const i = (interim || "").trim();
  if (!i) return b;
  if (!b) return i;
  const sep = b.endsWith(" ") || i.startsWith(" ") ? "" : "";
  return `${b}${sep}${i}`;
}

export function mapSpeechError(code: string): SpeechRecognitionErrorCode {
  if (code === "not-allowed" || code === "service-not-allowed") return "not-allowed";
  if (code === "no-speech") return "no-speech";
  if (code === "network") return "network";
  if (code === "aborted") return "aborted";
  return "unknown";
}

export function speechErrorMessage(code: SpeechRecognitionErrorCode): string {
  switch (code) {
    case "not-supported":
      return "当前浏览器不支持实时语音识别，将尝试录音后识别。";
    case "not-allowed":
      return microphoneDeniedMessage();
    case "no-speech":
      return "未检测到语音，请靠近麦克风重试。";
    case "network":
      return "语音识别网络异常，请检查网络后重试。";
    case "aborted":
      return "";
    default:
      return "语音识别失败，请重试或使用文字输入。";
  }
}

export type MicrophoneAccessErrorCode =
  | "insecure"
  | "unsupported"
  | "denied"
  | "no-device"
  | "unknown";

export class MicrophoneAccessError extends Error {
  code: MicrophoneAccessErrorCode;

  constructor(code: MicrophoneAccessErrorCode, message: string) {
    super(message);
    this.name = "MicrophoneAccessError";
    this.code = code;
  }
}

export function isSecureContextForSpeech(): boolean {
  if (typeof window === "undefined") return false;
  return window.isSecureContext;
}

export function microphoneDeniedMessage(): string {
  return "麦克风权限被拒绝。请点击地址栏左侧锁图标 → 网站设置 → 麦克风 → 允许，然后刷新页面重试。";
}

export function microphoneErrorMessage(code: MicrophoneAccessErrorCode): string {
  switch (code) {
    case "insecure":
      return "语音输入需 HTTPS 或 localhost。请使用 http://127.0.0.1:8502 访问，勿用局域网 IP。";
    case "unsupported":
      return "当前浏览器不支持麦克风访问。";
    case "denied":
      return microphoneDeniedMessage();
    case "no-device":
      return "未检测到麦克风设备，请检查硬件连接。";
    default:
      return "无法访问麦克风，请重试。";
  }
}

/** Explicit getUserMedia prompt — required before Web Speech on many browsers. */
export async function ensureMicrophoneAccess(): Promise<MediaStream> {
  if (!isSecureContextForSpeech()) {
    throw new MicrophoneAccessError("insecure", microphoneErrorMessage("insecure"));
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new MicrophoneAccessError("unsupported", microphoneErrorMessage("unsupported"));
  }
  try {
    return await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    const name = err instanceof DOMException ? err.name : "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      throw new MicrophoneAccessError("denied", microphoneErrorMessage("denied"));
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      throw new MicrophoneAccessError("no-device", microphoneErrorMessage("no-device"));
    }
    throw new MicrophoneAccessError("unknown", microphoneErrorMessage("unknown"));
  }
}

export function releaseMediaStream(stream: MediaStream | null | undefined): void {
  stream?.getTracks().forEach((t) => t.stop());
}
