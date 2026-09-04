"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, Language, OutboundResult, wsBase } from "@/lib/api";
import { Topbar } from "@/components/nav";
import { Panel } from "@/components/ui";

const SLOT_KEYS = ["budget", "timeline", "city", "property_type"] as const;
type Slots = Record<string, string | null>;
type Msg = { role: "user" | "agent" | "info"; text: string };

// ---------------------------------------------------------------------------
// Outbound (Twilio dials a real phone)
// ---------------------------------------------------------------------------
function OutboundPanel({ language }: { language: string }) {
  const [to, setTo] = useState("+91");
  const [result, setResult] = useState<OutboundResult | null>(null);
  const [busy, setBusy] = useState(false);

  const place = async () => {
    setBusy(true);
    setResult(null);
    try {
      setResult(await api.placeOutbound(to.trim(), language));
    } catch (e) {
      setResult({ error: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel className="p-5">
      <div className="text-[11px] uppercase tracking-wider text-muted">
        Outbound Call
      </div>
      <p className="mt-2 text-xs text-faint">
        Twilio dials this number and connects Ava. On a trial account the number
        must be verified.
      </p>
      <div className="mt-4 flex gap-2">
        <input
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="+9198XXXXXXXX"
          spellCheck={false}
          className="flex-1 border border-line bg-ink px-3 py-2 font-mono text-sm text-fg outline-none focus:border-accent"
        />
        <button
          onClick={place}
          disabled={busy || to.trim().length < 6}
          className="border border-accent bg-accent px-4 py-2 text-sm font-medium text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Dialing…" : "Place call"}
        </button>
      </div>

      {result ? (
        <div className="mt-4 border border-line bg-ink p-3 text-xs">
          {result.error ? (
            <span className="text-bad">Error: {result.error}</span>
          ) : (
            <div className="space-y-1">
              <div>
                <span className="text-muted">status: </span>
                <span className="text-good">{result.status}</span>
              </div>
              <div className="text-muted">
                call_sid: <span className="font-mono text-faint">{result.call_sid}</span>
              </div>
              <div className="text-faint">
                Watch it appear in Calls once it completes.
              </div>
            </div>
          )}
        </div>
      ) : null}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Browser test (talk to Ava through your mic)
// ---------------------------------------------------------------------------
const TARGET_SR = 16000;

function BrowserCallPanel({ language }: { language: string }) {
  const [active, setActive] = useState(false);
  const [status, setStatus] = useState("Idle.");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [stage, setStage] = useState("—");
  const [slots, setSlots] = useState<Slots>({});

  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const procRef = useRef<ScriptProcessorNode | null>(null);
  const srcRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const activeRef = useRef(false);
  // Web Audio scheduling for seamless streamed playback.
  const nextTimeRef = useRef(0);
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);

  const addMsg = (m: Msg) => setMessages((prev) => [...prev, m]);

  // data = [4-byte LE sample rate][int16 PCM]; schedule it back-to-back.
  const playPcmChunk = useCallback((data: ArrayBuffer) => {
    const ctx = ctxRef.current;
    if (!ctx) return;
    const sr = new DataView(data).getUint32(0, true);
    const pcm = new Int16Array(data, 4);
    if (!pcm.length) return;
    const buffer = ctx.createBuffer(1, pcm.length, sr);
    const ch = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 0x8000;
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    const now = ctx.currentTime;
    const start = Math.max(now, nextTimeRef.current);
    source.start(start);
    nextTimeRef.current = start + buffer.duration;
    sourcesRef.current.push(source);
    source.onended = () => {
      sourcesRef.current = sourcesRef.current.filter((s) => s !== source);
    };
  }, []);

  const stopPlayback = useCallback(() => {
    sourcesRef.current.forEach((s) => {
      try {
        s.stop();
      } catch {}
    });
    sourcesRef.current = [];
    nextTimeRef.current = 0;
  }, []);

  const downsample = (input: Float32Array, inRate: number): Int16Array => {
    const ratio = inRate / TARGET_SR;
    const outLen = Math.floor(input.length / ratio);
    const out = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const s = Math.max(-1, Math.min(1, input[Math.floor(i * ratio)]));
      out[i] = s * 0x7fff;
    }
    return out;
  };

  const start = useCallback(async () => {
    setMessages([]);
    setStage("—");
    setSlots({});
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    streamRef.current = stream;
    const ctx = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    ctxRef.current = ctx;
    const source = ctx.createMediaStreamSource(stream);
    srcRef.current = source;
    const proc = ctx.createScriptProcessor(4096, 1, 1);
    procRef.current = proc;

    const ws = new WebSocket(`${wsBase()}/ws/call?lang=${encodeURIComponent(language)}`);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => setStatus("Connected. Ava is greeting you…");
    ws.onclose = () => setStatus("Call ended.");
    ws.onerror = () => setStatus("Connection error.");
    ws.onmessage = (ev) => {
      if (typeof ev.data !== "string") {
        playPcmChunk(ev.data as ArrayBuffer);
        return;
      }
      const msg = JSON.parse(ev.data);
      if (msg.type === "agent") addMsg({ role: "agent", text: msg.text });
      else if (msg.type === "user") addMsg({ role: "user", text: msg.text });
      else if (msg.type === "info") addMsg({ role: "info", text: msg.text });
      else if (msg.type === "state") {
        setStage(msg.stage);
        setSlots(msg.slots);
      } else if (msg.type === "interrupt") stopPlayback();
      else if (msg.type === "ready")
        setStatus("Listening — just talk. You can interrupt anytime.");
    };

    proc.onaudioprocess = (e) => {
      if (!activeRef.current || ws.readyState !== WebSocket.OPEN) return;
      // Half-duplex: don't capture while Kavya is speaking, so her audio can't
      // echo from the speakers into the mic and create false "turns".
      if (ctx.currentTime < nextTimeRef.current + 0.15) return;
      const pcm = downsample(e.inputBuffer.getChannelData(0), ctx.sampleRate);
      ws.send(pcm.buffer);
    };
    source.connect(proc);
    proc.connect(ctx.destination);

    activeRef.current = true;
    setActive(true);
  }, [playPcmChunk, stopPlayback, language]);

  const end = useCallback(() => {
    activeRef.current = false;
    setActive(false);
    stopPlayback();
    procRef.current?.disconnect();
    srcRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close();
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.close();
    setStatus("Idle.");
  }, [stopPlayback]);

  return (
    <Panel className="p-5">
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-wider text-muted">
          Browser Test Call
        </div>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span
            className={`inline-block h-1.5 w-1.5 ${active ? "bg-good" : "bg-faint"}`}
          />
          {status}
        </div>
      </div>
      <p className="mt-2 text-xs text-faint">
        Talk to Kavya through your mic — no phone needed. She listens once she
        finishes speaking (half-duplex, so her voice can&apos;t echo back). Real
        phone calls are full-duplex and support interruptions.
      </p>

      <button
        onClick={() => (active ? end() : start().catch((e) => setStatus("Mic error: " + e.message)))}
        className={`mt-4 w-full border px-4 py-3 text-sm font-medium transition-colors ${
          active
            ? "border-bad bg-bad text-ink"
            : "border-accent bg-accent text-ink hover:opacity-90"
        }`}
      >
        {active ? "End call" : "Start call"}
      </button>

      {/* stage + slots */}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="border border-accent/50 px-2 py-0.5 uppercase tracking-wide text-accent">
          {stage}
        </span>
        {SLOT_KEYS.map((k) => (
          <span
            key={k}
            className={`border px-2 py-0.5 ${
              slots[k] ? "border-good/40 text-good" : "border-line text-faint"
            }`}
          >
            {k.replace("_", " ")}: {slots[k] ?? "—"}
          </span>
        ))}
      </div>

      {/* transcript */}
      <div className="mt-4 flex max-h-72 flex-col gap-2 overflow-y-auto border border-line bg-ink p-3">
        {messages.length === 0 ? (
          <div className="py-6 text-center text-xs text-faint">
            Transcript will appear here.
          </div>
        ) : (
          messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] px-3 py-2 text-sm ${
                m.role === "user"
                  ? "self-end bg-panel-2 text-fg"
                  : m.role === "agent"
                    ? "self-start border-l-2 border-accent bg-panel-2 text-fg"
                    : "self-center text-xs text-faint"
              }`}
            >
              {m.text}
            </div>
          ))
        )}
      </div>
    </Panel>
  );
}

export default function NewCallPage() {
  const [langs, setLangs] = useState<Language[]>([]);
  const [language, setLanguage] = useState("en-IN");

  useEffect(() => {
    api
      .languages()
      .then((r) => {
        setLangs(r.languages);
        setLanguage(r.default);
      })
      .catch(() => setLangs([{ code: "en-IN", name: "English", native: "English" }]));
  }, []);

  return (
    <div>
      <Topbar title="New Call" />
      <div className="p-6">
        {/* Admin language selector — applies to the call started below */}
        <Panel className="mb-6 flex flex-wrap items-center gap-4 p-5">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted">
              Call Language
            </div>
            <p className="mt-1 text-xs text-faint">
              You (admin) set this before the call. Kavya speaks, listens, and thinks
              in this language.
            </p>
          </div>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="ml-auto border border-line bg-ink px-3 py-2 text-sm text-fg outline-none focus:border-accent"
          >
            {langs.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name} ({l.native}) — {l.code}
              </option>
            ))}
          </select>
        </Panel>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <OutboundPanel language={language} />
          <BrowserCallPanel language={language} />
        </div>
      </div>
    </div>
  );
}
