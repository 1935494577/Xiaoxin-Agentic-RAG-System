import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { transcribeAudio } from "../api/client";
import {
  appendFinalTranscript,
  ensureMicrophoneAccess,
  getBrowserSpeechRecognitionCtor,
  isBrowserSpeechRecognitionSupported,
  mapSpeechError,
  mergeDisplayTranscript,
  MicrophoneAccessError,
  releaseMediaStream,
  speechErrorMessage,
  type BrowserSpeechRecognition,
  type SpeechRecognitionErrorEvent,
  type SpeechRecognitionEvent,
} from "../lib/speechRecognition";

const MAX_RECORD_MS = 60_000;

export type SpeechInputMode = "browser" | "recorder" | "unsupported";

export type UseSpeechInputOptions = {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
  lang?: string;
};

export function useSpeechInput({
  value,
  onChange,
  disabled = false,
  lang = "zh-CN",
}: UseSpeechInputOptions) {
  const [listening, setListening] = useState(false);
  const [recording, setRecording] = useState(false);
  const [interim, setInterim] = useState("");
  const [busy, setBusy] = useState(false);
  const valueRef = useRef(value);
  const listeningRef = useRef(false);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const recordTimerRef = useRef<number | null>(null);

  const browserSupported = isBrowserSpeechRecognitionSupported();
  const mode: SpeechInputMode = browserSupported
    ? "browser"
    : typeof navigator !== "undefined" &&
        !!navigator.mediaDevices?.getUserMedia &&
        typeof MediaRecorder !== "undefined"
      ? "recorder"
      : "unsupported";

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    listeningRef.current = listening;
  }, [listening]);

  const stopBrowserRecognition = useCallback(() => {
    listeningRef.current = false;
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    releaseMediaStream(micStreamRef.current);
    micStreamRef.current = null;
    setListening(false);
    setInterim("");
  }, []);

  const stopRecorder = useCallback(() => {
    if (recordTimerRef.current != null) {
      window.clearTimeout(recordTimerRef.current);
      recordTimerRef.current = null;
    }
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    }
    recorderRef.current = null;
    setRecording(false);
  }, []);

  const uploadRecording = useCallback(
    async (blob: Blob) => {
      if (!blob.size) {
        toast.message("未录到有效音频");
        return;
      }
      setBusy(true);
      try {
        const { text } = await transcribeAudio(blob, "zh");
        const trimmed = (text || "").trim();
        if (!trimmed) {
          toast.message("未识别到语音内容");
          return;
        }
        onChange(appendFinalTranscript(valueRef.current, trimmed));
      } catch (err) {
        const msg = err instanceof Error ? err.message : "语音识别失败";
        toast.error(msg);
      } finally {
        setBusy(false);
      }
    },
    [onChange]
  );

  const startRecorder = useCallback(async () => {
    try {
      const stream = await ensureMicrophoneAccess();
      micStreamRef.current = stream;
      const mime =
        MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "";
      const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        releaseMediaStream(stream);
        if (micStreamRef.current === stream) micStreamRef.current = null;
        const type = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        void uploadRecording(blob);
      };
      recorder.onerror = () => {
        releaseMediaStream(stream);
        if (micStreamRef.current === stream) micStreamRef.current = null;
        toast.error("录音失败，请重试");
        setRecording(false);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      recordTimerRef.current = window.setTimeout(() => {
        toast.message("已达最长录音时长，正在识别…");
        stopRecorder();
      }, MAX_RECORD_MS);
    } catch (err) {
      toast.error(err instanceof MicrophoneAccessError ? err.message : "请允许麦克风权限后再使用语音输入");
    }
  }, [stopRecorder, uploadRecording]);

  const startBrowserRecognition = useCallback(async () => {
    const Ctor = getBrowserSpeechRecognitionCtor();
    if (!Ctor) {
      toast.error(speechErrorMessage("not-supported"));
      return;
    }

    let stream: MediaStream | null = null;
    try {
      stream = await ensureMicrophoneAccess();
      micStreamRef.current = stream;
    } catch (err) {
      toast.error(err instanceof MicrophoneAccessError ? err.message : "请允许麦克风权限后再使用语音输入");
      return;
    }

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimText = "";
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i]?.[0]?.transcript ?? "";
        if (event.results[i]?.isFinal) finalText += piece;
        else interimText += piece;
      }
      if (finalText.trim()) {
        onChange(appendFinalTranscript(valueRef.current, finalText));
        setInterim("");
      } else {
        setInterim(interimText);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = mapSpeechError(event.error);
      const msg = speechErrorMessage(code);
      if (msg) toast.error(msg);
      releaseMediaStream(micStreamRef.current);
      micStreamRef.current = null;
      setListening(false);
      setInterim("");
      listeningRef.current = false;
    };

    recognition.onend = () => {
      if (listeningRef.current) {
        try {
          recognition.start();
        } catch {
          releaseMediaStream(micStreamRef.current);
          micStreamRef.current = null;
          setListening(false);
          setInterim("");
          listeningRef.current = false;
        }
        return;
      }
      releaseMediaStream(micStreamRef.current);
      micStreamRef.current = null;
      setInterim("");
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
      listeningRef.current = true;
    } catch {
      releaseMediaStream(stream);
      micStreamRef.current = null;
      toast.error("无法启动语音识别，请重试");
    }
  }, [lang, onChange]);

  const toggleSpeech = useCallback(() => {
    if (disabled || busy) return;
    if (mode === "unsupported") {
      toast.error("当前浏览器不支持语音输入");
      return;
    }
    if (mode === "browser") {
      if (listening) stopBrowserRecognition();
      else void startBrowserRecognition();
      return;
    }
    if (recording) stopRecorder();
    else void startRecorder();
  }, [
    busy,
    disabled,
    listening,
    mode,
    recording,
    startBrowserRecognition,
    startRecorder,
    stopBrowserRecognition,
    stopRecorder,
  ]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
      releaseMediaStream(micStreamRef.current);
      micStreamRef.current = null;
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") rec.stop();
      recorderRef.current = null;
      if (recordTimerRef.current != null) window.clearTimeout(recordTimerRef.current);
    };
  }, []);

  const displayValue = mergeDisplayTranscript(value, interim);
  const active = listening || recording || busy;

  return {
    mode,
    listening,
    recording,
    busy,
    active,
    displayValue,
    toggleSpeech,
    stopSpeech: () => {
      stopBrowserRecognition();
      stopRecorder();
    },
  };
}
