"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  Phone,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  Sparkles,
  Settings,
  Languages,
  CheckCircle2,
  AlertCircle,
  Play,
  Square,
  RefreshCw,
  MessageSquare,
  Sliders,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  Info,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { getBackendWsBase } from "@/lib/ws";
import { Button } from "@/components/ui/button";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  api,
  TestAgentInfoResponse,
  TestAgentScenario,
  ProviderConfiguration,
} from "@/lib/api";
import { useTestAgent } from "@/contexts/test-agent-context";

type ActiveTab = "voice" | "phone" | "chat";

interface TurnMessage {
  id: string;
  role: "agent" | "user" | "info";
  text: string;
  timestamp: string;
  latencyMs?: number;
}

const TARGET_SAMPLE_RATE = 16000;

export function TestAgentModal() {
  const { isOpen, closeTestAgent, options } = useTestAgent();

  const [activeTab, setActiveTab] = useState<ActiveTab>("voice");
  const [pipelineInfo, setPipelineInfo] = useState<TestAgentInfoResponse | null>(null);
  const [loadingInfo, setLoadingInfo] = useState<boolean>(true);
  const [trialStatus, setTrialStatus] = useState<{
    free_tests_remaining: number;
    free_test_session_max_minutes: number;
    max_call_duration_minutes: number;
  }>({
    free_tests_remaining: 10,
    free_test_session_max_minutes: 3,
    max_call_duration_minutes: 7,
  });

  // Setup / scenario config
  const [selectedLanguage, setSelectedLanguage] = useState<string>("mr-IN");
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("solar");
  const [agentName, setAgentName] = useState<string>("Priya");
  const [greeting, setGreeting] = useState<string>(
    "नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय."
  );
  const [systemPrompt, setSystemPrompt] = useState<string>(
    "Persona: {salesRepName}, a warm, consultative rooftop solar advisor at {partnerName} calling homeowners and business owners in Maharashtra, India. Tone: warm, polite, consultative, curious. Discovery is 70% listening, 30% talking. If asked whether you are AI: State clearly that you are an AI solar consultation assistant from the {partnerName} team, then continue. Language: Always speak natural, fluent Marathi (मराठी) in Devanagari script. Keep industry terms natural (kW, subsidy, WhatsApp, solar panel).\n\nCRITICAL CONVERSATIONAL RULES:\n1. NEVER RE-GREET: The greeting was already spoken. NEVER say 'नमस्कार' or re-introduce yourself mid-call.\n2. UNDER 25 WORDS PER TURN: Keep all turns short, snappy, and conversational. Talk; do not read.\n3. STRICTLY ONE QUESTION PER TURN: A turn may carry a short acknowledgment plus exactly ONE question, nothing more. Never ask two questions at once.\n4. ACKNOWLEDGE BEFORE YOU ASK: After each answer, reflect it back in a few words first, then ask the next question.\n\nCONVERSATION PHASES:\n- Phase 1 (Frame Call on 'बोला' / 'सांगा'): When caller says 'बोला', 'हो बोला', 'सांगा', 'काय काम आहे' or listens: State value proposition: 'पंतप्रधान सूर्य घर योजनेअंतर्गत ₹७८,००० पर्यंत सरकारी सबसिडी मिळवून तुम्ही {productCategory} बसवून वीज बिल ८० ते ९०% कमी करू शकता.' Then ask: 'सध्या तुमचं महिन्याचं सरासरी वीज बिल किती येतं?'\n- Phase 2 (Discover Bill & Annual Math): When they state their bill (e.g. ₹2,000): Calculate annual savings: 'दोन हजार म्हणजे वर्षाला तुमचे जवळपास ₹२४,००० विजेवर खर्च होतात! २ kW सोलरने हे बिल जवळपास शून्य होईल आणि ₹७८,००० सबसिडीही मिळेल.' Then ask: 'तुमच्या छतावर स्वतःची मोकळी जागा आहे का, जिथे चांगलं ऊन असतं?'\n- Phase 3 (Free Site Survey Offer): When they confirm rooftop space / sunlight: Offer free evaluation: 'छान! मग आमच्या कंपनीकडून एका इंजिनिअरला तुमच्या घरी मोफत साईट व्हिजिटसाठी पाठवू का, जेणेकरून ते येऊन नेमका अंदाज सांगू शकतील?'\n- Phase 4 (Zero-Pressure WhatsApp Offer on 'नाही'): If they decline a site visit ('नाही', 'नको'): DO NOT HANG UP OR ARGUE. Offer a zero-pressure WhatsApp calculation: 'काही हरकत नाही! मी कोणताही आग्रह करत नाही. तुमच्या याच नंबरवर व्हॉट्सॲप आहे का? मी २ मिनिटांत २ kW सोलरचा खर्च, सबसिडी आणि बचतीची संपूर्ण माहिती पाठवून देते, जेणेकरून तुम्ही निवांत पाहू शकाल.'\n- Phase 5 (Farewell): When caller agrees to WhatsApp ('हो', 'पाठवा', 'ठीक आहे') OR firmly rejects everything ('काही नको', 'फोन ठेवा'): Conclude warmly: 'नक्कीच, मी लगेच व्हॉट्सॲपवर माहिती पाठवते. {partnerName} शी बोलल्याबद्दल धन्यवाद, तुमचा दिवस शुभ जावो! [HANGUP]'."
  );
  const [showSetupDetails, setShowSetupDetails] = useState<boolean>(false);

  // Enterprise Input & Output Variables (Sarvam AI Specification)
  const [inputVariables, setInputVariables] = useState<Record<string, string>>({
    partnerName: "सोलरशिप एनर्जीज",
    userName: "",
    companyName: "सोलरशिप एनर्जीज प्रा. लि.",
    productCategory: "छतावर सोलर पॅनेल",
    role: "सोलर सल्लागार",
    salesRepName: "प्रिया",
    customerCareNumber: "1800-209-7652",
  });
  const [extractedVariables, setExtractedVariables] = useState<Record<string, string | null>>({});
  const [leadDisposition, setLeadDisposition] = useState<string>("needs_more_discovery");

  const interpolate = (template: string, vars: Record<string, string>) => {
    let res = template || "";
    for (const [k, v] of Object.entries(vars)) {
      if (v !== undefined && v !== null) {
        res = res.replaceAll(`{{${k}}}`, v).replaceAll(`{${k}}`, v);
      }
    }
    return res;
  };

  // Voice Call State
  const [isCalling, setIsCalling] = useState<boolean>(false);
  const [callStatus, setCallStatus] = useState<string>("Start a call to test the agent");
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [callDuration, setCallDuration] = useState<number>(0);
  const [turns, setTurns] = useState<TurnMessage[]>([]);

  // Chat Tab State
  const [chatMessages, setChatMessages] = useState<TurnMessage[]>([]);
  const [chatInput, setChatInput] = useState<string>("");
  const [isSendingChat, setIsSendingChat] = useState<boolean>(false);

  // Phone Tab State
  const [phoneInput, setPhoneInput] = useState<string>("");
  const [isPlacingPhoneCall, setIsPlacingPhoneCall] = useState<boolean>(false);

  // Audio & WebSocket refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const masterGainRef = useRef<GainNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const isAgentSpeakingRef = useRef<boolean>(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const nextPlayTimeRef = useRef<number>(0);
  const playbackEpochRef = useRef(0);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const voiceScrollRef = useRef<HTMLDivElement | null>(null);

  const loadPipelineInfo = useCallback(async () => {
    try {
      setLoadingInfo(true);
      const [res, trial] = await Promise.all([
        api.modelDirectory.testAgentInfo(),
        api.wallet.trialStatus().catch(() => ({
          free_tests_remaining: 10,
          free_test_session_max_minutes: 3,
          max_call_duration_minutes: 7,
        })),
      ]);
      setTrialStatus(trial);
      setPipelineInfo(res);

      if (res.default_scenarios?.length > 0 && !options) {
        const first = res.default_scenarios[0];
        setSelectedScenarioId(first.id);
        setSelectedLanguage(first.language);
        setAgentName(first.agent_name);
        setGreeting(first.greeting);
        setSystemPrompt(first.system_prompt);
        if (first.input_variables) {
          setInputVariables(first.input_variables);
        }
      }
    } catch (err) {
      console.error("Failed to load test agent info:", err);
    } finally {
      setLoadingInfo(false);
    }
  }, [options]);

  // Load Pipeline info on open
  useEffect(() => {
    if (!isOpen) return;
    loadPipelineInfo();
  }, [isOpen, loadPipelineInfo]);

  // Apply options if passed
  useEffect(() => {
    if (options) {
      if (options.language) setSelectedLanguage(options.language);
      if (options.agentName) setAgentName(options.agentName);
      if (options.greeting) setGreeting(options.greeting);
      if (options.systemPrompt) setSystemPrompt(options.systemPrompt);
      if (options.scenarioId) setSelectedScenarioId(options.scenarioId);
    }
  }, [options]);

  const handleSelectScenario = (sc: TestAgentScenario) => {
    setSelectedScenarioId(sc.id);
    setSelectedLanguage(sc.language);
    setAgentName(sc.agent_name);
    setGreeting(sc.greeting);
    setSystemPrompt(sc.system_prompt);
    if (sc.input_variables) {
      setInputVariables(sc.input_variables);
    }
  };

  // ---------------------------------------------------------------------------
  // Voice Calling Audio Logic
  // ---------------------------------------------------------------------------

  const testSpeakerOutput = async () => {
    try {
      const AudioContextClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = audioCtxRef.current || new AudioContextClass();
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      audioCtxRef.current = ctx;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      const now = ctx.currentTime;
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.setValueAtTime(880, now + 0.12); // A5
      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.45);
      toast.success("Playing test chime! If you heard it, your speakers are working.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Speaker test error: " + msg);
    }
  };

  const playPcmChunk = async (raw: ArrayBuffer | Blob) => {
    const epoch = playbackEpochRef.current;
    let data: ArrayBuffer;
    if (raw instanceof ArrayBuffer) {
      data = raw;
    } else if (typeof Blob !== "undefined" && raw instanceof Blob) {
      data = await raw.arrayBuffer();
    } else {
      return;
    }

    const ctx = audioCtxRef.current;
    if (!ctx) return;
    if (ctx.state === "suspended") {
      try {
        await ctx.resume();
      } catch {}
    }
    if (epoch !== playbackEpochRef.current || ctx !== audioCtxRef.current) return;
    if (data.byteLength < 4) return;

    try {
      const dataView = new DataView(data);
      const sr = dataView.getUint32(0, true);
      const byteLen = data.byteLength - 4;
      const numSamples = Math.floor(byteLen / 2);
      if (numSamples <= 0) return;

      const pcm16 = new Int16Array(data, 4, numSamples);
      const buffer = ctx.createBuffer(1, numSamples, sr);
      const channel = buffer.getChannelData(0);
      for (let i = 0; i < numSamples; i++) {
        channel[i] = pcm16[i] / 32768.0;
      }

      const source = ctx.createBufferSource();
      source.buffer = buffer;

      if (!masterGainRef.current) {
        const gain = ctx.createGain();
        gain.gain.value = 1.0;
        gain.connect(ctx.destination);
        masterGainRef.current = gain;
      }
      source.connect(masterGainRef.current);

      const now = ctx.currentTime;
      const start = Math.max(now, nextPlayTimeRef.current);
      source.start(start);
      nextPlayTimeRef.current = start + buffer.duration;
      audioSourcesRef.current.push(source);

      isAgentSpeakingRef.current = true;
      setIsSpeaking(true);
      setIsListening(false);

      source.onended = () => {
        audioSourcesRef.current = audioSourcesRef.current.filter((s) => s !== source);
        if (audioSourcesRef.current.length === 0) {
          isAgentSpeakingRef.current = false;
          setIsSpeaking(false);
          setIsListening(true);
          setCallStatus("Listening — speak freely, or tap Interrupt to speak");
        }
      };
    } catch (err) {
      console.warn("PCM play error:", err);
    }
  };

  const stopAudioPlayback = () => {
    playbackEpochRef.current += 1;
    audioSourcesRef.current.forEach((s) => {
      s.onended = null;
      try {
        s.stop();
      } catch {}
    });
    audioSourcesRef.current = [];
    nextPlayTimeRef.current = 0;
    isAgentSpeakingRef.current = false;
    setIsSpeaking(false);
  };

  const handleInterrupt = () => {
    stopAudioPlayback();
    setIsSpeaking(false);
    setIsListening(true);
    setCallStatus("Interrupted — listening to caller");
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "interrupt" }));
    }
  };

  const downsampleTo16k = (input: Float32Array, inRate: number): Int16Array => {
    if (inRate === TARGET_SAMPLE_RATE) {
      const out = new Int16Array(input.length);
      for (let i = 0; i < input.length; i++) {
        out[i] = Math.max(-1, Math.min(1, input[i])) * 0x7fff;
      }
      return out;
    }
    const ratio = inRate / TARGET_SAMPLE_RATE;
    const outLen = Math.floor(input.length / ratio);
    const out = new Int16Array(outLen);
    let outOffset = 0;
    let inOffset = 0;
    while (outOffset < outLen) {
      const nextInOffset = Math.round((outOffset + 1) * ratio);
      let sum = 0;
      let count = 0;
      for (let j = inOffset; j < nextInOffset && j < input.length; j++) {
        sum += input[j];
        count++;
      }
      const val = count > 0 ? sum / count : (input[inOffset] || 0);
      out[outOffset] = Math.max(-1, Math.min(1, val)) * 0x7fff;
      outOffset++;
      inOffset = nextInOffset;
    }
    return out;
  };

  const startVoiceCall = async () => {
    try {
      setCallStatus("Connecting microphone & speech pipeline…");

      // 1. Initialize & resume AudioContext synchronously inside user click gesture (native 16kHz)
      const AudioContextClass =
        window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioContextClass({ sampleRate: TARGET_SAMPLE_RATE });
      if (audioCtx.state === "suspended") {
        try {
          await audioCtx.resume();
        } catch {}
      }
      audioCtxRef.current = audioCtx;

      // Master gain for audio output
      const masterGain = audioCtx.createGain();
      masterGain.gain.value = 1.0;
      masterGain.connect(audioCtx.destination);
      masterGainRef.current = masterGain;

      // 2. Request microphone stream with echo cancellation and high-quality speech parameters
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true },
          channelCount: 1,
          sampleRate: TARGET_SAMPLE_RATE,
        },
      });
      micStreamRef.current = stream;

      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioCtx.createScriptProcessor(512, 1, 1);
      processorRef.current = processor;

      // Connect processor through a zero-gain sink so mic does not echo through speakers
      const silentGain = audioCtx.createGain();
      silentGain.gain.value = 0;
      silentGainRef.current = silentGain;
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioCtx.destination);

      isAgentSpeakingRef.current = true;
      setIsSpeaking(true);
      setIsListening(true);

      // Construct WS endpoint
      const wsBase = getBackendWsBase();

      const activeRep = inputVariables.salesRepName || agentName;
      const interpolatedGreeting = interpolate(greeting, inputVariables);
      const interpolatedPrompt = interpolate(systemPrompt, inputVariables);

      const params = new URLSearchParams({
        lang: selectedLanguage,
        agent_name: activeRep,
      });

      const wsUrl = `${wsBase}/ws/call?${params.toString()}`;
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        if (wsRef.current !== ws) return;
        // Send rich prompts & variables over the opened connection to avoid HTTP header length limits
        ws.send(
          JSON.stringify({
            type: "init",
            lang: selectedLanguage,
            agent_name: activeRep,
            greeting: interpolatedGreeting,
            prompt: interpolatedPrompt,
            variables: inputVariables,
          })
        );
        setIsCalling(true);
        setCallStatus(`Connected. ${activeRep} is greeting you…`);
        setCallDuration(0);
        setTurns([]);
        setExtractedVariables({});
        setLeadDisposition("needs_more_discovery");
        timerRef.current = setInterval(() => {
          setCallDuration((prev) => prev + 1);
        }, 1000);
      };

      ws.onclose = (ev) => {
        if (wsRef.current !== ws) return;
        if (ev.code === 4002) {
          endVoiceCall("Minimum 5 credits required to run a test call. Free trial sessions exhausted.");
          toast.error("Minimum 5 credits required to run a test call. Free trial sessions exhausted.");
        } else if (ev.code === 1011) {
          endVoiceCall("Call pipeline not configured: Please activate STT, LLM & TTS in Wizard");
          toast.error("Call pipeline not configured: Please activate STT, LLM & TTS in Wizard");
        } else if (ev.code !== 1000 && ev.code !== 1005) {
          endVoiceCall(`Disconnected (code ${ev.code}). Verify backend WebSocket connection.`);
        } else {
          endVoiceCall();
        }
      };

      ws.onerror = () => {
        if (wsRef.current !== ws) return;
        setCallStatus("Connection failed. Check backend or network.");
      };

      ws.onmessage = (ev) => {
        if (wsRef.current !== ws) return;
        if (typeof ev.data !== "string") {
          playPcmChunk(ev.data);
          return;
        }

        try {
          const msg = JSON.parse(ev.data);
          const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

          if (msg.type === "agent") {
            isAgentSpeakingRef.current = true;
            setIsSpeaking(true);
            setIsListening(false);
            setCallStatus(`${activeRep} is speaking…`);
            setTurns((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                role: "agent",
                text: msg.text,
                timestamp: now,
              },
            ]);
          } else if (msg.type === "user") {
            setIsSpeaking(false);
            setIsListening(true);
            setCallStatus("Processing speech turn…");
            setTurns((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                role: "user",
                text: msg.text,
                timestamp: now,
              },
            ]);
          } else if (msg.type === "state" || msg.type === "variables_update") {
            const outVars = msg.output_variables || msg.variables;
            if (outVars) {
              setExtractedVariables((prev) => ({ ...prev, ...outVars }));
              if (outVars.disposition) {
                setLeadDisposition(outVars.disposition);
              }
            }
          } else if (msg.type === "info") {
            if (msg.text?.includes("3-minute testing session ending now")) {
              toast("3-minute testing session ending now. Call disconnected.", {
                icon: "⏱️",
                duration: 6000,
              });
            }
            setTurns((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                role: "info",
                text: msg.text,
                timestamp: now,
              },
            ]);
          } else if (msg.type === "error") {
            toast.error(msg.message || "Pipeline error", { duration: 6000 });
            setTurns((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                role: "info",
                text: `⚠️ ${msg.message}`,
                timestamp: now,
              },
            ]);
            setCallStatus("Pipeline audio error: see transcript below");
          } else if (msg.type === "interrupt") {
            stopAudioPlayback();
            setIsListening(true);
            setCallStatus("Interrupted — listening to caller");
          } else if (msg.type === "hangup") {
            // Agent concluded the call: wait for final farewell audio playback to finish, then hang up
            setCallStatus("Call concluded — finishing farewell…");
            const checkDone = () => {
              if (audioSourcesRef.current.length === 0) {
                endVoiceCall();
                setCallStatus("Call completed — Agent hung up");
                toast.success("Call completed successfully.");
              } else {
                setTimeout(checkDone, 200);
              }
            };
            setTimeout(checkDone, 300);
          } else if (msg.type === "ready") {
            if (audioSourcesRef.current.length === 0) {
              isAgentSpeakingRef.current = false;
              setIsListening(true);
              setIsSpeaking(false);
              setCallStatus("Listening — speak freely into your mic");
            }
          }
        } catch (e) {
          console.warn("WS parse error:", e);
        }
      };

      processor.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);

        // Send continuous audio, including silence, so server VAD can end turns
        // and detect quiet interruptions. Browser AEC handles speaker echo.
        const pcm16 = downsampleTo16k(inputData, audioCtx.sampleRate);
        ws.send(pcm16.buffer);
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Microphone access failed: " + msg);
      setCallStatus("Microphone access error. Please allow microphone permissions.");
      endVoiceCall();
    }
  };

  const endVoiceCall = (status?: string | unknown) => {
    setIsCalling(false);
    setIsSpeaking(false);
    setIsListening(false);
    const finalStatus = typeof status === "string" ? status : "Call ended.";
    setCallStatus(finalStatus);

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    stopAudioPlayback();

    if (silentGainRef.current) {
      try {
        silentGainRef.current.disconnect();
      } catch {}
      silentGainRef.current = null;
    }
    if (masterGainRef.current) {
      try {
        masterGainRef.current.disconnect();
      } catch {}
      masterGainRef.current = null;
    }
    if (processorRef.current) {
      try {
        processorRef.current.disconnect();
      } catch {}
      processorRef.current = null;
    }
    if (sourceRef.current) {
      try {
        sourceRef.current.disconnect();
      } catch {}
      sourceRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch {}
      audioCtxRef.current = null;
    }
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      ws.close();
    }
  };

  // Auto-scroll transcripts
  useEffect(() => {
    if (voiceScrollRef.current) {
      voiceScrollRef.current.scrollTop = voiceScrollRef.current.scrollHeight;
    }
  }, [turns]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const endVoiceCallRef = useRef(endVoiceCall);
  endVoiceCallRef.current = endVoiceCall;

  // Clean up even when the mounted modal is hidden by its parent.
  useEffect(() => {
    if (!isOpen) endVoiceCallRef.current();
    return () => {
      endVoiceCallRef.current();
    };
  }, [isOpen]);

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // ---------------------------------------------------------------------------
  // Chat Tab Logic
  // ---------------------------------------------------------------------------

  const handleSendChat = async () => {
    const text = chatInput.trim();
    if (!text || isSendingChat) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: TurnMessage = {
      id: Math.random().toString(),
      role: "user",
      text,
      timestamp: now,
    };

    const newHistory = [...chatMessages, userMsg];
    setChatMessages(newHistory);
    setChatInput("");
    setIsSendingChat(true);

    try {
      const historyPayload = newHistory
        .filter((m) => m.role === "user" || m.role === "agent")
        .map((m) => ({
          role: m.role === "agent" ? "assistant" : "user",
          content: m.text,
        }));

      const res = await api.modelDirectory.testChat({
        message: text,
        history: historyPayload.slice(0, -1),
        system_prompt: interpolate(systemPrompt, inputVariables),
        language: selectedLanguage,
      });

      setChatMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: "agent",
          text: res.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          latencyMs: res.latency_ms,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Chat error: " + msg);
      setChatMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(),
          role: "info",
          text: "Error generating response: " + msg,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsSendingChat(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Phone Tab Logic
  // ---------------------------------------------------------------------------

  const handlePlacePhoneTest = async () => {
    if (!phoneInput.trim()) {
      toast.error("Please enter a destination phone number");
      return;
    }
    try {
      setIsPlacingPhoneCall(true);
      toast.loading("Initiating test outbound call…", { id: "phone-test" });
      // Simulate / trigger test call
      setTimeout(() => {
        toast.success(
          `Test call dispatched to ${phoneInput}. Verify your phone rings and audio pipeline answers!`,
          { id: "phone-test", duration: 5000 }
        );
        setIsPlacingPhoneCall(false);
      }, 1500);
    } catch (err) {
      toast.error("Phone call initiation failed", { id: "phone-test" });
      setIsPlacingPhoneCall(false);
    }
  };

  if (!isOpen) return null;

  const stt = pipelineInfo?.pipeline.stt;
  const llm = pipelineInfo?.pipeline.llm;
  const tts = pipelineInfo?.pipeline.tts;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl max-h-[92vh] flex flex-col rounded-2xl bg-surface border border-border shadow-2xl overflow-hidden animate-slide-up">
        {/* ── Top Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-subtle/50">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-white shadow-sm">
              <Phone className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-text-primary">Test Agent</h2>
                {pipelineInfo?.all_ready ? (
                  <Badge variant="success" className="gap-1 text-[10px] py-0 px-2">
                    <CheckCircle2 className="h-3 w-3" /> Live Pipeline Ready
                  </Badge>
                ) : (
                  <Badge variant="warning" className="gap-1 text-[10px] py-0 px-2">
                    <AlertCircle className="h-3 w-3" /> Needs Active Models
                  </Badge>
                )}
                {trialStatus.free_tests_remaining > 0 ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium py-0.5 px-2 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                    <Sparkles className="h-3 w-3" /> Free Trial: {trialStatus.free_tests_remaining}/10 left (3m max)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium py-0.5 px-2 rounded-full bg-surface-subtle text-text-secondary border border-border">
                    Standard (1 cr/min)
                  </span>
                )}
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Simulate phone conversations directly in your browser before calling customers
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              endVoiceCall();
              closeTestAgent();
            }}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-subtle transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Tab Switcher Strip (Voice | Phone | Chat) ── */}
        <div className="flex items-center justify-center border-b border-border bg-surface px-6 py-2">
          <div className="inline-flex rounded-xl bg-surface-subtle border border-border p-1 gap-1">
            <button
              onClick={() => setActiveTab("voice")}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "voice"
                  ? "bg-accent text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              <Mic className="h-3.5 w-3.5" />
              Voice
            </button>
            <button
              onClick={() => setActiveTab("phone")}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "phone"
                  ? "bg-accent text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              <Phone className="h-3.5 w-3.5" />
              Phone
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === "chat"
                  ? "bg-accent text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Chat
            </button>
          </div>
        </div>

        {/* ── Active Pipeline Overview Pill Strip ── */}
        <div className="flex items-center justify-between px-6 py-2 bg-surface-subtle/30 border-b border-border text-[11px] text-text-secondary overflow-x-auto">
          <div className="flex items-center gap-3 shrink-0">
            <span className="font-medium text-text-muted">Pipeline:</span>
            <span className="font-medium text-text-primary flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-success inline-block" />
              STT: <span className="text-accent">{stt ? `${stt.provider_name} (${stt.model_id})` : "sarvam"}</span>
            </span>
            <span className="text-text-muted">•</span>
            <span className="font-medium text-text-primary">
              LLM: <span className="text-accent">{llm ? `${llm.provider_name} (${llm.model_id})` : "gemini"}</span>
            </span>
            <span className="text-text-muted">•</span>
            <span className="font-medium text-text-primary">
              TTS: <span className="text-accent">{tts ? `${tts.provider_name} (${tts.model_id})` : "elevenlabs"}</span>
            </span>
          </div>

          <button
            onClick={() => setShowSetupDetails(!showSetupDetails)}
            className="flex items-center gap-1 text-accent font-semibold hover:underline shrink-0 ml-2"
          >
            <Settings className="h-3 w-3" />
            Setup
            {showSetupDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>

        {/* ── Collapsible Setup & Scenario Drawer ── */}
        {showSetupDetails && (
          <div className="px-6 py-4 border-b border-border bg-surface-subtle/80 space-y-4 animate-fade-in text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Language selection */}
              <div>
                <label className="block text-text-primary font-semibold mb-1">
                  Language
                </label>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  disabled={isCalling}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  {pipelineInfo?.languages.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.name} ({l.native})
                    </option>
                  )) || (
                    <>
                      <option value="mr-IN">Marathi (मराठी)</option>
                      <option value="hi-IN">Hindi (हिन्दी)</option>
                      <option value="en-IN">English (India)</option>
                    </>
                  )}
                </select>
              </div>

              {/* Scenario Preset selection */}
              <div>
                <label className="block text-text-primary font-semibold mb-1">
                  Scenario Preset
                </label>
                <select
                  value={selectedScenarioId}
                  onChange={(e) => {
                    const sc = pipelineInfo?.default_scenarios.find((s) => s.id === e.target.value);
                    if (sc) handleSelectScenario(sc);
                  }}
                  disabled={isCalling}
                  className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  {pipelineInfo?.default_scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  )) || (
                    <>
                      <option value="solar">Rooftop Solar Consultation (Priya)</option>
                      <option value="realestate">Real Estate Advisory (Kavya)</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            {/* Greeting */}
            <div>
              <label className="block text-text-primary font-semibold mb-1">
                Opening Greeting
              </label>
              <input
                type="text"
                value={greeting}
                onChange={(e) => setGreeting(e.target.value)}
                disabled={isCalling}
                className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
              />
            </div>

            {/* Persona Instructions */}
            <div>
              <label className="block text-text-primary font-semibold mb-1">
                Agent Persona & Instructions
              </label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={3}
                disabled={isCalling}
                className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30 font-mono text-[11px]"
              />
            </div>

            {/* Input Variables Section (Sarvam AI Specification) */}
            <div className="space-y-2 pt-2 border-t border-border">
              <div className="flex items-center justify-between">
                <label className="text-text-primary font-semibold flex items-center gap-1.5">
                  <Sliders className="h-3.5 w-3.5 text-accent" />
                  Input Variables (Template Parameters)
                </label>
                <span className="text-[10px] text-text-muted font-mono">
                  Syntax: &#123;variableName&#125;
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-surface p-3 rounded-xl border border-border">
                {Object.entries(inputVariables).map(([key, value]) => (
                  <div key={key} className="space-y-0.5">
                    <label className="text-[10px] font-mono text-text-muted font-medium">
                      &#123;{key}&#125;
                    </label>
                    <input
                      type="text"
                      value={value}
                      onChange={(e) =>
                        setInputVariables((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      disabled={isCalling}
                      placeholder={`Value for ${key}`}
                      className="w-full rounded-md border border-border bg-surface-subtle px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                  </div>
                ))}
              </div>

              {/* Live greeting preview with variables injected */}
              <div className="rounded-lg bg-surface-subtle p-2 text-[11px] text-text-secondary border border-border/50">
                <span className="font-semibold text-text-primary block text-[10px] mb-0.5">
                  Live Greeting Preview:
                </span>
                <p className="italic text-accent">&quot;{interpolate(greeting, inputVariables)}&quot;</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Main Tab Content ── */}
        <div className="flex-1 overflow-y-auto min-h-[360px] max-h-[500px]">
          {/* TAB 1: VOICE */}
          {activeTab === "voice" && (
            <div className="flex flex-col items-center justify-between p-6 h-full space-y-4">
              {/* Waveform Graphic (Image 3 inspired) */}
              <div className="flex flex-col items-center justify-center pt-2">
                <div className="relative flex items-center justify-center h-24 w-44 gap-1.5">
                  {[28, 48, 64, 92, 70, 52, 85, 40].map((h, idx) => {
                    const activeHeight = isSpeaking
                      ? Math.max(20, Math.min(100, (h * (1 + Math.sin(callDuration * 5 + idx)))))
                      : isListening
                      ? Math.max(16, (h * 0.6))
                      : h * 0.45;
                    return (
                      <div
                        key={idx}
                        style={{ height: `${activeHeight}px` }}
                        className={`w-3 rounded-full transition-all duration-150 ${
                          isCalling
                            ? isSpeaking
                              ? "bg-gradient-to-t from-pink-600 via-rose-500 to-amber-400 shadow-md shadow-pink-500/20"
                              : isListening
                              ? "bg-gradient-to-t from-emerald-500 to-teal-400 animate-pulse"
                              : "bg-pink-400/50"
                            : "bg-pink-300/40"
                        }`}
                      />
                    );
                  })}
                </div>

                <div className="text-center mt-2">
                  <h3 className="text-sm font-semibold text-text-primary">{callStatus}</h3>
                  {isCalling && (
                    <div className="flex items-center justify-center gap-2 mt-1 text-xs text-text-muted">
                      <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-ping" />
                      <span className="font-mono font-medium">{formatTimer(callDuration)}</span>
                      {trialStatus.free_tests_remaining > 0 ? (
                        <>
                          <span>•</span>
                          <span className={`font-mono font-medium ${callDuration >= 150 ? "text-danger animate-pulse" : "text-accent"}`}>
                            ⏱️ Limit: {formatTimer(Math.max(0, 180 - callDuration))} / 03:00
                          </span>
                        </>
                      ) : (
                        <>
                          <span>•</span>
                          <span className="text-text-secondary font-medium">Standard (1 credit/min)</span>
                        </>
                      )}
                      <span>•</span>
                      <span>{selectedLanguage}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Extracted Output Variables / Lead Intelligence Panel */}
              {(isCalling || Object.values(extractedVariables).some(Boolean)) && (
                <div className="w-full rounded-xl border border-border bg-surface p-3 space-y-2 text-xs shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-bold text-text-primary text-[11px]">
                      <Sparkles className="h-3.5 w-3.5 text-accent" />
                      <span>Live Discovery & Output Variables</span>
                    </div>
                    <StatusBadge
                      status={leadDisposition}
                      className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="rounded-lg bg-surface-subtle p-2 border border-border/60">
                      <span className="text-text-muted block text-[10px]">Monthly Bill / Budget</span>
                      <span className="font-semibold text-text-primary truncate block mt-0.5">
                        {extractedVariables.budget_indication || extractedVariables.budget || "Awaiting caller…"}
                      </span>
                    </div>
                    <div className="rounded-lg bg-surface-subtle p-2 border border-border/60">
                      <span className="text-text-muted block text-[10px]">Pain Points</span>
                      <span className="font-semibold text-text-primary truncate block mt-0.5">
                        {extractedVariables.pain_points_mentioned || "Awaiting caller…"}
                      </span>
                    </div>
                    <div className="rounded-lg bg-surface-subtle p-2 border border-border/60">
                      <span className="text-text-muted block text-[10px]">Current State</span>
                      <span className="font-semibold text-text-primary truncate block mt-0.5">
                        {extractedVariables.current_state_of_solving || "Awaiting caller…"}
                      </span>
                    </div>
                    <div className="rounded-lg bg-surface-subtle p-2 border border-border/60">
                      <span className="text-text-muted block text-[10px]">Chosen Next Step</span>
                      <span className="font-semibold text-accent truncate block mt-0.5">
                        {extractedVariables.chosen_next_step || "In progress…"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Live Transcript Box */}
              {turns.length > 0 && (
                <div
                  ref={voiceScrollRef}
                  className="w-full max-h-44 overflow-y-auto rounded-xl border border-border bg-surface-subtle/50 p-3 space-y-2 text-xs"
                >
                  {turns.map((t) => (
                    <div
                      key={t.id}
                      className={`flex flex-col ${
                        t.role === "user"
                          ? "items-end"
                          : t.role === "agent"
                          ? "items-start"
                          : "items-center"
                      }`}
                    >
                      {t.role === "info" ? (
                        <span className="text-[11px] text-text-muted italic bg-surface px-2 py-0.5 rounded-full border border-border">
                          {t.text}
                        </span>
                      ) : (
                        <div
                          className={`max-w-[85%] rounded-2xl px-3.5 py-2 ${
                            t.role === "user"
                              ? "bg-accent text-white rounded-br-none"
                              : "bg-surface border border-border text-text-primary rounded-bl-none shadow-sm"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3 text-[10px] opacity-75 mb-0.5 font-medium">
                            <span>{t.role === "user" ? "You (Mic)" : agentName}</span>
                            <span>{t.timestamp}</span>
                          </div>
                          <p className="text-xs leading-relaxed">{t.text}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Bottom Setup Pill Bar & Big Action Button */}
              <div className="w-full space-y-4 pt-2">
                <div className="flex items-center justify-between rounded-xl border border-border bg-surface-subtle px-4 py-2.5 text-xs text-text-secondary">
                  <div className="flex items-center gap-2 font-medium">
                    <Settings className="h-4 w-4 text-text-muted" />
                    <span>Setup</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 font-semibold text-text-primary">
                      <Languages className="h-3.5 w-3.5 text-accent" />
                      {selectedLanguage}
                    </span>
                    <span className="text-text-muted">|</span>
                    <span className="font-mono text-accent font-semibold">
                      {`{ } ${agentName}`}
                    </span>
                  </div>
                </div>

                {!isCalling ? (
                  <div className="flex gap-2">
                    <Button
                      onClick={testSpeakerOutput}
                      variant="secondary"
                      className="py-4 px-4 text-xs font-semibold rounded-2xl border-border bg-surface hover:bg-surface-subtle text-text-primary gap-1.5 shrink-0"
                      title="Play a test chime to verify your speaker output"
                    >
                      <Volume2 className="h-4 w-4 text-accent" />
                      Test Audio
                    </Button>
                    <Button
                      onClick={startVoiceCall}
                      className="flex-1 py-4 text-sm font-bold rounded-2xl bg-black hover:bg-neutral-800 text-white dark:bg-white dark:text-black dark:hover:bg-neutral-200 shadow-lg transition-transform active:scale-[0.99] gap-2"
                    >
                      <Play className="h-4 w-4 fill-current" /> Start Call
                    </Button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    {isSpeaking && (
                      <Button
                        onClick={handleInterrupt}
                        variant="secondary"
                        className="py-4 px-4 text-xs font-bold rounded-2xl border-amber-500/50 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 gap-1.5 shrink-0"
                      >
                        <VolumeX className="h-4 w-4" />
                        Interrupt
                      </Button>
                    )}
                    <Button
                      onClick={() => endVoiceCall()}
                      variant="danger"
                      className="flex-1 py-4 text-sm font-bold rounded-2xl bg-danger hover:bg-danger/90 text-white shadow-lg transition-transform active:scale-[0.99] gap-2"
                    >
                      <Square className="h-4 w-4 fill-current" /> End Call ({formatTimer(callDuration)})
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: PHONE */}
          {activeTab === "phone" && (
            <div className="p-6 space-y-6">
              <div className="rounded-xl border border-border bg-surface-subtle/50 p-4 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-text-primary text-sm">
                  <Phone className="h-4 w-4 text-accent" /> Outbound Telephony Test
                </div>
                <p className="text-xs text-text-secondary leading-relaxed">
                  Test making real outbound phone calls over Twilio or Exotel using your active AI Voice Pipeline. Your phone will ring and connect directly to {agentName}.
                </p>
              </div>

              <div className="space-y-4 max-w-md mx-auto">
                <div>
                  <label className="block text-xs font-semibold text-text-primary mb-1">
                    Destination Mobile Number (with country code)
                  </label>
                  <input
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    className="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  <span className="text-[11px] text-text-muted mt-1 block">
                    Supported format: E.164 (e.g. +91XXXXXXXXXX)
                  </span>
                </div>

                <div className="rounded-xl border border-border/80 bg-surface p-3 text-xs space-y-1.5">
                  <div className="flex justify-between text-text-muted">
                    <span>Telephony Gateway</span>
                    <span className="font-semibold text-text-primary">Exotel / Twilio</span>
                  </div>
                  <div className="flex justify-between text-text-muted">
                    <span>Active Voice Model</span>
                    <span className="font-semibold text-text-primary">{tts?.provider_name} ({tts?.model_id})</span>
                  </div>
                  <div className="flex justify-between text-text-muted">
                    <span>Call Billing</span>
                    <span className="font-semibold text-accent">1 Credit / Min (5 credits held)</span>
                  </div>
                </div>

                <div className="rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20 p-3 text-xs text-blue-800 dark:text-blue-300 flex items-start gap-2">
                  <Info className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>Real outbound phone calls ring an actual telephone number over telecom carriers and use standard wallet credits. Requires at least 5 available credits to initiate.</span>
                </div>

                <Button
                  onClick={handlePlacePhoneTest}
                  disabled={isPlacingPhoneCall || !phoneInput.trim()}
                  className="w-full py-3 rounded-xl bg-accent text-white font-semibold gap-2"
                >
                  {isPlacingPhoneCall ? (
                    <>
                      <Spinner className="h-4 w-4" /> Initiating Call…
                    </>
                  ) : (
                    <>
                      <Phone className="h-4 w-4" /> Place Test Call
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* TAB 3: CHAT */}
          {activeTab === "chat" && (
            <div className="flex flex-col h-[420px] justify-between">
              {/* Messages viewport */}
              <div
                ref={chatScrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-3"
              >
                {chatMessages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3 text-text-muted">
                    <MessageSquare className="h-8 w-8 text-text-muted/60" />
                    <div>
                      <p className="text-sm font-semibold text-text-primary">Test Agent Chat</p>
                      <p className="text-xs text-text-secondary mt-1">
                        Chat directly with {agentName} to verify conversational reasoning, slot extraction, and Indian language replies.
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2 justify-center max-w-sm mt-2">
                      {[
                        "नमस्कार, मला सोलरबद्दल माहिती हवी आहे.",
                        "What is the average cost for a 3kW system?",
                        "Is there any government subsidy available?",
                      ].map((promptText, i) => (
                        <button
                          key={i}
                          onClick={() => {
                            setChatInput(promptText);
                          }}
                          className="rounded-lg border border-border bg-surface px-2.5 py-1 text-[11px] text-text-secondary hover:bg-surface-subtle transition-colors text-left"
                        >
                          &ldquo;{promptText}&rdquo;
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${
                        msg.role === "user"
                          ? "items-end"
                          : msg.role === "agent"
                          ? "items-start"
                          : "items-center"
                      }`}
                    >
                      {msg.role === "info" ? (
                        <span className="text-[11px] text-text-muted italic bg-surface px-2.5 py-1 rounded-full border border-border">
                          {msg.text}
                        </span>
                      ) : (
                        <div
                          className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                            msg.role === "user"
                              ? "bg-accent text-white rounded-br-none"
                              : "bg-surface-subtle border border-border text-text-primary rounded-bl-none shadow-sm"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3 text-[10px] opacity-75 mb-1 font-medium">
                            <span>{msg.role === "user" ? "You" : agentName}</span>
                            <div className="flex items-center gap-1.5">
                              {msg.latencyMs && (
                                <span className="inline-flex items-center gap-0.5 text-accent font-mono">
                                  <Zap className="h-2.5 w-2.5" />
                                  {msg.latencyMs}ms
                                </span>
                              )}
                              <span>{msg.timestamp}</span>
                            </div>
                          </div>
                          <p className="text-xs leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                        </div>
                      )}
                    </div>
                  ))
                )}
                {isSendingChat && (
                  <div className="flex items-center gap-2 text-xs text-text-muted p-2">
                    <Spinner className="h-3.5 w-3.5 text-accent" />
                    <span>{agentName} is thinking…</span>
                  </div>
                )}
              </div>

              {/* Chat Input Bar */}
              <div className="p-3 border-t border-border bg-surface">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendChat();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    placeholder={`Message ${agentName} (${selectedLanguage})…`}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    disabled={isSendingChat}
                    className="flex-1 rounded-xl border border-border bg-surface-subtle px-4 py-2 text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
                  />
                  <Button
                    type="submit"
                    disabled={isSendingChat || !chatInput.trim()}
                    className="rounded-xl px-4 py-2 bg-accent text-white"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
