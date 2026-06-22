import { describe, expect, it } from "vitest";
import {
  appendFinalTranscript,
  isBrowserSpeechRecognitionSupported,
  mergeDisplayTranscript,
  microphoneDeniedMessage,
  microphoneErrorMessage,
  MicrophoneAccessError,
} from "../src/lib/speechRecognition";

describe("speechRecognition helpers", () => {
  it("appendFinalTranscript adds spaced chunk", () => {
    expect(appendFinalTranscript("你好", "世界")).toBe("你好 世界");
    expect(appendFinalTranscript("", "开始")).toBe("开始");
  });

  it("mergeDisplayTranscript combines base and interim", () => {
    expect(mergeDisplayTranscript("超脑阅读", "要求")).toBe("超脑阅读要求");
    expect(mergeDisplayTranscript("", "")).toBe("");
  });

  it("isBrowserSpeechRecognitionSupported is false without window API", () => {
    expect(isBrowserSpeechRecognitionSupported()).toBe(false);
  });

  it("microphone error messages are actionable", () => {
    expect(microphoneDeniedMessage()).toContain("地址栏");
    expect(microphoneErrorMessage("insecure")).toContain("127.0.0.1");
    expect(new MicrophoneAccessError("denied", microphoneDeniedMessage()).code).toBe("denied");
  });
});
