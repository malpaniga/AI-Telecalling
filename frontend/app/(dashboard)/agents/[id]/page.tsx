"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ChevronLeft,
  Sparkles,
  Save,
  CheckCircle2,
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Send,
  Languages,
  Sliders,
  Wrench,
  Variable,
  FileText,
  CheckCheck,
  Plus,
  Trash2,
  Copy,
  ExternalLink,
  Bot,
  MessageSquare,
  ShieldAlert,
  ShieldCheck,
  Volume2,
  ArrowRight,
  RefreshCw,
  Info,
  BookOpen,
} from "lucide-react";
import toast from "react-hot-toast";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Modal } from "@/components/ui/modal";
import { Input, Select } from "@/components/ui/input";
import { api, Agent, AgentVersion, VoiceProfile, KnowledgeBase, PhoneNumber } from "@/lib/api";
import { StructuredInstructionEditor } from "@/components/agents/structured-instruction-editor";

type StudioTab = "instructions" | "knowledge" | "variables" | "tools" | "settings" | "tests";
type TestTab = "voice" | "phone" | "chat";

interface ChatMessage {
  id: string;
  sender: "agent" | "user" | "system";
  text: string;
  time: string;
}

export default function SarvamAgentStudioPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  // Agent & Version data
  const [agent, setAgent] = useState<Agent | null>(null);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [activeVersion, setActiveVersion] = useState<AgentVersion | null>(null);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [genieLoading, setGenieLoading] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  // Active studio tab
  const [activeTab, setActiveTab] = useState<StudioTab>("instructions");

  // Agent Editable Configuration State
  const [agentName, setAgentName] = useState("");
  const [greeting, setGreeting] = useState("");
  const [instructions, setInstructions] = useState("");
  const [primaryLanguage, setPrimaryLanguage] = useState("mr-IN");
  const [voiceProfileId, setVoiceProfileId] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [inputVariables, setInputVariables] = useState<Record<string, string>>({});
  const [outputVariables, setOutputVariables] = useState<string[]>([]);
  const [speechSpeed, setSpeechSpeed] = useState(1.0);
  const [sensitivity, setSensitivity] = useState(70);

  // Knowledge Base State
  const [allKbs, setAllKbs] = useState<KnowledgeBase[]>([]);
  const [associatedKbIds, setAssociatedKbIds] = useState<string[]>([]);
  const [knowledgeStrictness, setKnowledgeStrictness] = useState<"flexible" | "strict">("flexible");
  const [kbContextPreview, setKbContextPreview] = useState<string>("");
  const [kbTogglingId, setKbTogglingId] = useState<string | null>(null);

  // Tools state
  const [toolWhatsApp, setToolWhatsApp] = useState(true);
  const [toolCalendar, setToolCalendar] = useState(true);
  const [toolWebhook, setToolWebhook] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("https://api.yourcompany.com/webhooks/voice-lead");

  // Translation Modal State
  const [showTranslateModal, setShowTranslateModal] = useState(false);
  const [targetLang, setTargetLang] = useState("hi-IN");
  const [translating, setTranslating] = useState(false);
  const [translateInstructions, setTranslateInstructions] = useState(false);
  const [saveAsDraftOnTranslate, setSaveAsDraftOnTranslate] = useState(true);

  // Review Agent Modal State
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewTips, setReviewTips] = useState<string[]>([]);

  // ---------------------------------------------------------------------------
  // Right Column: Embedded Live Test Agent State
  // ---------------------------------------------------------------------------
  const [testTab, setTestTab] = useState<TestTab>("voice");
  const [callActive, setCallActive] = useState(false);
  const [callStatus, setCallStatus] = useState<string>("Disconnected");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [micMuted, setMicMuted] = useState(false);
  const [transcript, setTranscript] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [outboundPhone, setOutboundPhone] = useState("+91 ");
  const [dialingOutbound, setDialingOutbound] = useState(false);
  const [assignedNumbers, setAssignedNumbers] = useState<PhoneNumber[]>([]);
  const [selectedCallingNumber, setSelectedCallingNumber] = useState<string>("");
  const [extractedVariables, setExtractedVariables] = useState<Record<string, string>>({});
  const [pipelineStatus, setPipelineStatus] = useState<{
    stt: boolean;
    llm: boolean;
    tts: boolean;
  }>({ stt: false, llm: false, tts: false });

  // Audio refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const audioSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const greetingInputRef = useRef<HTMLTextAreaElement | null>(null);
  const hangupTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const micMutedRef = useRef<boolean>(false);
  const initSentRef = useRef<boolean>(false);

  // Scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // Load organization's assigned phone numbers for phone testing
  useEffect(() => {
    api.phoneNumbers
      .myNumbers()
      .then((nums) => {
        setAssignedNumbers(nums);
        if (nums.length > 0) {
          setSelectedCallingNumber(nums[0].number);
        }
      })
      .catch((err) => {
        console.error("Failed to load assigned phone numbers:", err);
      });
  }, []);

  // Load Agent data
  const loadAgent = useCallback(async (targetVersionId?: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const [agentData, versionsList, profiles, pStatus, kbsList, agentKbsList, ctxPreview] = await Promise.all([
        api.agents.get(id),
        api.agents.versions.list(id),
        api.voiceProfiles.list(),
        api.agents.pipelineStatus().catch(() => null),
        api.knowledge.list().catch(() => []),
        api.knowledge.getForAgent(id).catch(() => []),
        api.knowledge.getContext(id).catch(() => null),
      ]);

      setAgent(agentData);
      setVersions(versionsList);
      setVoiceProfiles(profiles);
      setAllKbs(kbsList);
      setAssociatedKbIds(agentKbsList.map((k) => k.id));
      if (ctxPreview) setKbContextPreview(ctxPreview.context);
      setAgentName(agentData.name);
      setVoiceProfileId(agentData.voice_profile_id || profiles[0]?.id || "");

      if (pStatus) {
        setPipelineStatus({
          stt: !!pStatus.stt?.connected,
          llm: !!pStatus.llm?.connected,
          tts: !!pStatus.tts?.connected,
        });
      }

      // Determine active configuration: prefer targetVersionId > active_version_id > newer draft > latest version
      let currentVersion: AgentVersion | undefined;
      if (targetVersionId) {
        currentVersion = versionsList.find((v) => v.id === targetVersionId);
      }
      if (!currentVersion && agentData.active_version_id) {
        const activeVer = versionsList.find((v) => v.id === agentData.active_version_id);
        const latestDraft = versionsList.find((v) => v.status === "draft");
        if (latestDraft && activeVer && latestDraft.version > activeVer.version) {
          currentVersion = latestDraft;
        } else {
          currentVersion = activeVer;
        }
      }
      if (!currentVersion) {
        // If user has an in-progress draft, load it so greeting / configuration edits aren't lost
        const draftVer = versionsList.find((v) => v.status === "draft");
        if (draftVer) {
          currentVersion = draftVer;
        }
      }
      if (!currentVersion && versionsList.length > 0) {
        currentVersion = versionsList[0];
      }
      setActiveVersion(currentVersion || null);
      setHasUnsavedChanges(false);

      if (currentVersion && currentVersion.configuration) {
        const config = currentVersion.configuration as Record<string, unknown>;
        setGreeting(config.greeting !== undefined && config.greeting !== null ? String(config.greeting) : "");
        setInstructions(config.system_prompt !== undefined && config.system_prompt !== null ? String(config.system_prompt) : "");
        setPrimaryLanguage(String(config.primary_language || "en-IN"));
        if (config.voice_id) {
          setVoiceId(String(config.voice_id));
        } else if (agentData.name?.toLowerCase().includes("chitra")) {
          setVoiceId("chaitra_hi_customer");
        } else {
          setVoiceId("");
        }
        setInputVariables(
          (config.input_variables as Record<string, string>) || {
            partnerName: agentData.name || "Our Company",
            salesRepName: "Assistant",
            userName: "",
            productCategory: "Services",
          }
        );
        setOutputVariables(
          (config.output_variables as string[]) || [
            "disposition",
            "chosen_next_step",
          ]
        );
        if (config.knowledge_strictness) {
          setKnowledgeStrictness(config.knowledge_strictness === "strict" ? "strict" : "flexible");
        }
        if (config.speech_speed) setSpeechSpeed(Number(config.speech_speed));
        if (config.barge_in_sensitivity) setSensitivity(Number(config.barge_in_sensitivity));
        if (config.tools) {
          const tools = config.tools as Record<string, unknown>;
          if (tools.whatsapp !== undefined) setToolWhatsApp(!!tools.whatsapp);
          if (tools.calendar !== undefined) setToolCalendar(!!tools.calendar);
          if (tools.webhook !== undefined) setToolWebhook(!!tools.webhook);
          if (tools.webhook_url) setWebhookUrl(String(tools.webhook_url));
        }
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  // Helper to build full configuration dictionary
  const buildConfigPayload = useCallback(
    (overrides?: Partial<{ greeting: string; primary_language: string; system_prompt: string }>) => {
      return {
        agent_name: agentName,
        greeting: overrides?.greeting ?? greeting,
        system_prompt: overrides?.system_prompt ?? instructions,
        primary_language: overrides?.primary_language ?? primaryLanguage,
        input_variables: inputVariables,
        output_variables: outputVariables,
        speech_speed: speechSpeed,
        barge_in_sensitivity: sensitivity,
        voice_id: voiceId || undefined,
        knowledge_strictness: knowledgeStrictness,
        tools: {
          whatsapp: toolWhatsApp,
          calendar: toolCalendar,
          webhook: toolWebhook,
          webhook_url: webhookUrl,
        },
      };
    },
    [agentName, greeting, instructions, primaryLanguage, inputVariables, outputVariables, speechSpeed, sensitivity, voiceId, knowledgeStrictness, toolWhatsApp, toolCalendar, toolWebhook, webhookUrl]
  );

  // Knowledge Base Association Toggle
  async function handleToggleKb(kbId: string) {
    if (!id) return;
    setKbTogglingId(kbId);
    const isCurrentlyLinked = associatedKbIds.includes(kbId);
    try {
      if (isCurrentlyLinked) {
        await api.knowledge.disassociateAgent(kbId, id);
        setAssociatedKbIds((prev) => prev.filter((k) => k !== kbId));
        toast.success("Knowledge Base unlinked");
      } else {
        await api.knowledge.associateAgent(kbId, id);
        setAssociatedKbIds((prev) => [...prev, kbId]);
        toast.success("Knowledge Base linked to agent");
      }
      const preview = await api.knowledge.getContext(id, undefined).catch(() => null);
      if (preview) setKbContextPreview(preview.context);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update Knowledge Base");
    } finally {
      setKbTogglingId(null);
    }
  }

  // Save Draft Version (without activating)
  async function handleSaveDraft() {
    if (!id) return;
    setSaving(true);
    try {
      const updatedConfig = buildConfigPayload();

      // Also update agent name if changed
      await api.agents.update(id, {
        name: agentName,
        voice_profile_id: voiceProfileId,
      });

      let savedVerId: string;
      if (activeVersion && activeVersion.status === "draft") {
        // Update current draft version
        const updated = await api.agents.versions.update(id, activeVersion.id, updatedConfig);
        savedVerId = updated.id;
        toast.success("Draft version updated!");
      } else {
        // Create new draft version
        const newVer = await api.agents.versions.create(id, {
          configuration: updatedConfig,
          description: `Draft saved ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
          auto_activate: false,
        });
        savedVerId = newVer.id;
        toast.success("Draft version saved!");
      }

      const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setLastSavedAt(nowTime);
      setHasUnsavedChanges(false);
      await loadAgent(savedVerId);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to save draft");
    } finally {
      setSaving(false);
    }
  }

  // Primary Save Action: Persist all edits to greeting, instructions, variables, tools & activate immediately
  const handleSaveChanges = useCallback(async () => {
    if (!id) return;
    setSaving(true);
    try {
      const updatedConfig = buildConfigPayload();

      // 1. Update top-level agent metadata
      await api.agents.update(id, {
        name: agentName,
        voice_profile_id: voiceProfileId,
      });

      let savedVerId: string;
      if (activeVersion && activeVersion.status === "draft") {
        // Update draft with latest state, then publish & activate it so changes become immediate
        await api.agents.versions.update(id, activeVersion.id, updatedConfig);
        const pubVer = await api.agents.versions.publish(id, activeVersion.id);
        savedVerId = pubVer.id;
      } else {
        // Create new version with atomic publish and activate (auto_activate: true)
        const newVer = await api.agents.versions.create(id, {
          configuration: updatedConfig,
          description: `Updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
          auto_activate: true,
        });
        savedVerId = newVer.id;
      }

      const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setLastSavedAt(nowTime);
      setHasUnsavedChanges(false);
      toast.success("Agent greeting & instructions saved successfully!");
      await loadAgent(savedVerId);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to save agent changes");
    } finally {
      setSaving(false);
    }
  }, [id, agentName, voiceProfileId, activeVersion, buildConfigPayload, loadAgent]);

  // Global Ctrl+S keyboard shortcut to save agent changes
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        handleSaveChanges();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleSaveChanges]);

  // Publish and Activate Version
  async function handlePublish() {
    return handleSaveChanges();
  }

  // Improve with Genie LLM
  async function handleImproveWithGenie() {
    setGenieLoading(true);
    try {
      const res = await api.agents.improveWithGenie({
        instructions,
        greeting,
        persona_focus: agentName,
      });

      setInstructions(res.improved_instructions);
      toast.success("Genie improved your agent instructions!");
      if (res.suggestions && res.suggestions.length > 0) {
        setReviewTips(res.suggestions);
        setShowReviewModal(true);
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Genie optimization failed");
    } finally {
      setGenieLoading(false);
    }
  }

  // Review Agent Tips
  function handleReviewAgent() {
    const tips: string[] = [];
    if (!greeting.includes("{partnerName}")) {
      tips.push("Include {partnerName} in your greeting so the agent introduces your brand naturally.");
    }
    if (!instructions.toLowerCase().includes("under 25 words")) {
      tips.push("Enforce 'Under 25 words per turn' in Speaking Style to keep phone call rhythm snappy.");
    }
    if (!instructions.toLowerCase().includes("acknowledge before you ask")) {
      tips.push("Add 'Acknowledge before asking' rule so the agent feels consultative rather than robotic.");
    }
    if (!instructions.toLowerCase().includes("strictly one question")) {
      tips.push("Enforce 'Strictly one question per turn' to avoid overwhelming the prospect.");
    }
    if (Object.keys(inputVariables).length === 0) {
      tips.push("Define input variables like partnerName and salesRepName to make your agent reusable across campaigns.");
    }
    if (tips.length === 0) {
      tips.push("Excellent work! Your agent prompt follows enterprise conversational voice standards.");
    }
    setReviewTips(tips);
    setShowReviewModal(true);
  }

  // Insert variable chip into greeting
  function insertVariableIntoGreeting(varKey: string) {
    const chipText = `{${varKey}}`;
    if (!greetingInputRef.current) {
      setGreeting((prev) => `${prev} ${chipText}`);
      return;
    }
    const el = greetingInputRef.current;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const nextText = greeting.substring(0, start) + chipText + greeting.substring(end);
    setGreeting(nextText);
    setTimeout(() => {
      el.focus();
      el.setSelectionRange(start + chipText.length, start + chipText.length);
    }, 10);
  }

  // ---------------------------------------------------------------------------
  // Embedded Test Agent: Web Audio & WebSocket Streamer
  // ---------------------------------------------------------------------------
  function stopPlayback() {
    audioSourcesRef.current.forEach((s) => {
      try {
        s.stop();
      } catch {}
    });
    audioSourcesRef.current = [];
    nextPlayTimeRef.current = 0;
  }

  function scheduleAutoHangup(delayBufferMs = 1200) {
    if (hangupTimeoutRef.current) {
      clearTimeout(hangupTimeoutRef.current);
    }
    setCallStatus("Call Completed · Wrapping up...");
    const ctx = audioCtxRef.current;
    const remainingAudioMs = ctx ? Math.max(0, (nextPlayTimeRef.current - ctx.currentTime) * 1000) : 0;
    const totalDelay = Math.max(remainingAudioMs + delayBufferMs, 1200);

    hangupTimeoutRef.current = setTimeout(() => {
      handleEndCall("Call Completed");
      toast.success("Call completed successfully");
      hangupTimeoutRef.current = null;
    }, totalDelay);
  }

  async function playPcmChunk(raw: ArrayBuffer | Blob) {
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

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(1.0, ctx.currentTime);
      src.connect(gainNode);
      gainNode.connect(ctx.destination);

      const now = ctx.currentTime;
      const start = Math.max(now, nextPlayTimeRef.current);
      src.start(start);
      nextPlayTimeRef.current = start + buffer.duration;
      audioSourcesRef.current.push(src);

      setIsSpeaking(true);
      setCallStatus("Speaking");
      src.onended = () => {
        audioSourcesRef.current = audioSourcesRef.current.filter((s) => s !== src);
        if (audioSourcesRef.current.length === 0) {
          setIsSpeaking(false);
          setCallStatus("Connected · Listening");
        }
      };

      // If wrap-up / auto-hangup has been scheduled, extend timer to accommodate new audio buffer
      if (hangupTimeoutRef.current) {
        scheduleAutoHangup();
      }
    } catch (err) {
      console.warn("PCM play error:", err);
    }
  }

  function downsampleTo16k(input: Float32Array, inRate: number): Int16Array {
    const TARGET_SR = 16000;
    if (inRate === TARGET_SR) {
      const out = new Int16Array(input.length);
      for (let i = 0; i < input.length; i++) {
        out[i] = Math.max(-1, Math.min(1, input[i])) * 0x7fff;
      }
      return out;
    }
    const ratio = inRate / TARGET_SR;
    const outLen = Math.floor(input.length / ratio);
    const out = new Int16Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const s = Math.max(-1, Math.min(1, input[Math.floor(i * ratio)]));
      out[i] = s * 0x7fff;
    }
    return out;
  }

  async function handleStartCall() {
    if (hangupTimeoutRef.current) {
      clearTimeout(hangupTimeoutRef.current);
      hangupTimeoutRef.current = null;
    }
    stopPlayback();
    micMutedRef.current = false;
    setMicMuted(false);
    setTranscript([]);
    setExtractedVariables({});
    setCallStatus("Connecting...");
    setIsSpeaking(false);
    setIsListening(false);

    try {
      // 1. Get microphone access with fan noise cancellation and high-pass hum filter
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true },
          channelCount: 1,
          sampleRate: 16000,
          // Advanced WebRTC / Chromium constraints for fan, AC rumble, and room acoustics
          googEchoCancellation: { ideal: true },
          googAutoGainControl: { ideal: true },
          googNoiseSuppression: { ideal: true },
          googHighpassFilter: { ideal: true },
          googTypingNoiseDetection: { ideal: true },
          googAudioMirroring: { ideal: false },
        } as MediaTrackConstraints,
      });
      micStreamRef.current = stream;

      // 2. Setup AudioContext (prefer 16kHz to match pipeline native sample rate)
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }

      // 3. Setup WebSocket connection (use clean URL to avoid HTTP 8KB header limit on large prompts)
      initSentRef.current = false;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname;
      const port = "8000"; // FastAPI backend port
      const voiceParam = voiceId || (agentName.toLowerCase().includes("chitra") ? "chaitra_hi_customer" : "");
      const wsUrl = `${proto}//${host}:${port}/ws/call?lang=${encodeURIComponent(primaryLanguage)}&agent_name=${encodeURIComponent(agentName)}&voice_profile_id=${encodeURIComponent(voiceProfileId)}${voiceParam ? `&voice_id=${encodeURIComponent(voiceParam)}` : ""}&agent_id=${encodeURIComponent(id || "")}&version_id=${encodeURIComponent(activeVersion?.id || "")}`;

      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        // Send full rich prompt, variables & parameters over the accepted WebSocket stream
        ws.send(
          JSON.stringify({
            type: "init",
            lang: primaryLanguage,
            agent_name: agentName,
            greeting: greeting,
            prompt: instructions,
            variables: inputVariables,
            sensitivity: sensitivity,
            voice_profile_id: voiceProfileId,
            voice_id: voiceParam || undefined,
            agent_id: id,
          })
        );
        initSentRef.current = true;
        setCallActive(true);
        setCallStatus("Connected · Waiting for greeting");
      };

      ws.onmessage = async (event) => {
        // Binary PCM chunk received from backend TTS
        if (event.data instanceof ArrayBuffer || (typeof Blob !== "undefined" && event.data instanceof Blob)) {
          await playPcmChunk(event.data);
          return;
        }

        // Text metadata event received
        try {
          const rawText = typeof event.data === "string" ? event.data : await (event.data as Blob).text();
          const msg = JSON.parse(rawText);
          if (msg.type === "error") {
            toast.error(msg.message || "Call pipeline error");
            setCallStatus("Pipeline Error");
            handleEndCall("Error");
            return;
          } else if (msg.type === "ready") {
            setIsListening(true);
            if (audioSourcesRef.current.length === 0) {
              setCallStatus("Connected · Listening");
            }
          } else if (msg.type === "hangup") {
            scheduleAutoHangup();
          } else if (msg.type === "agent") {
            setTranscript((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                sender: "agent",
                text: msg.text,
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
              },
            ]);
            setCallStatus("Speaking");

            // Client-side detection of farewell phrases as extra reliability guarantee
            const lowerText = (msg.text || "").toLowerCase();
            const farewellKeywords = [
              "दिवस शुभ जावो", "दिवस चांगला जावो", "तुमचा दिवस", "आपला दिवस",
              "बोलल्याबद्दल धन्यवाद", "शुभ दिवस", "काळजी घ्या", "पुन्हा संपर्क",
              "दिन शुभ", "अच्छा रहे", "अलविदा", "ख्याल रखें",
              "have a nice day", "have a great day", "have a good day",
              "goodbye", "bye bye", "take care", "thank you for your time"
            ];
            if (farewellKeywords.some((kw) => lowerText.includes(kw))) {
              scheduleAutoHangup();
            }
          } else if (msg.type === "user") {
            setTranscript((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                sender: "user",
                text: msg.text,
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
              },
            ]);
            setCallStatus("Thinking...");
          } else if (msg.type === "state") {
            if (msg.output_variables) {
              setExtractedVariables(msg.output_variables);
            }
          } else if (msg.type === "interrupt") {
            stopPlayback();
            setIsSpeaking(false);
          } else if (msg.type === "info") {
            // Noise or minor status
          }
        } catch {}
      };

      ws.onclose = () => {
        // If an auto-hangup is already scheduled to play out remaining audio, let it finish cleanly
        if (!hangupTimeoutRef.current) {
          handleEndCall();
        }
      };

      ws.onerror = () => {
        toast.error("WebSocket connection failed. Verify backend is running.");
        handleEndCall();
      };

      // 4. Setup Audio Worklet / ScriptProcessor for Mic stream
      const source = audioCtx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        if (!initSentRef.current) return;
        if (micMutedRef.current) return;

        const inputData = e.inputBuffer.getChannelData(0);

        // 1. Calculate audio frame root-mean-square (RMS) energy
        let sumSq = 0;
        for (let i = 0; i < inputData.length; i++) {
          sumSq += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sumSq / inputData.length);

        // 2. While agent audio is actively playing through speakers:
        // Protect against speaker audio bleeding into mic. Only allow transmission
        // if user intentionally speaks up firmly to barge in (rms >= bargeInThreshold)
        const isAgentPlaying = audioCtx.currentTime < nextPlayTimeRef.current;
        if (isAgentPlaying) {
          const bargeInThreshold = Math.max(0.035, 0.075 - (sensitivity / 100) * 0.035);
          if (rms < bargeInThreshold) return;
        }

        // 3. When agent is listening, send all continuous audio frames to backend.
        // Server-side Silero / WebRTC VAD needs the continuous unbroken stream
        // (including trailing silence) to detect speech onset and the end of each turn.
        const pcm16 = downsampleTo16k(inputData, audioCtx.sampleRate);
        wsRef.current.send(pcm16.buffer);
      };

      // ScriptProcessor requires connection to destination to process audio frames,
      // but feeding mic audio into speakers causes acoustic feedback and triggers browser echo ducking.
      // We route it through a silent GainNode (gain = 0).
      const silentGain = audioCtx.createGain();
      silentGain.gain.setValueAtTime(0, audioCtx.currentTime);
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(audioCtx.destination);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Microphone access denied or error occurred");
      handleEndCall();
    }
  }

  function handleEndCall(status?: string | unknown) {
    const finalStatus = typeof status === "string" ? status : "Disconnected";
    if (hangupTimeoutRef.current) {
      clearTimeout(hangupTimeoutRef.current);
      hangupTimeoutRef.current = null;
    }
    setCallActive(false);
    setCallStatus(finalStatus);
    setIsSpeaking(false);
    setIsListening(false);
    stopPlayback();

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch {}
      audioCtxRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
  }

  // Send simulated text chat message
  function handleSendChat() {
    if (!chatInput.trim()) return;
    const text = chatInput.trim();
    setChatInput("");

    setTranscript((prev) => [
      ...prev,
      {
        id: Math.random().toString(),
        sender: "user",
        text,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      },
    ]);

    // Send through WS if active, or simulate agent response
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "user_text", text }));
    } else {
      setTimeout(() => {
        setTranscript((prev) => [
          ...prev,
          {
            id: Math.random().toString(),
            sender: "agent",
            text: `छान! तुमच्या ${text} या उत्तराची नोंद घेतली आहे.`,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
          },
        ]);
      }, 700);
    }
  }

  // Trigger Phone Test
  async function handleDialPhone() {
    if (!outboundPhone.trim() || outboundPhone.trim().length < 8) {
      return toast.error("Please enter a valid phone number with country code");
    }
    if (!selectedCallingNumber) {
      return toast.error("Please select an assigned Calling Number");
    }
    setDialingOutbound(true);
    try {
      await api.calls.initiate({
        to_number: outboundPhone.trim(),
        from_number: selectedCallingNumber,
        agent_id: agent?.id,
        agent_version: activeVersion?.version ?? 1,
      });
      toast.success(`Outbound call queued to ${outboundPhone} from ${selectedCallingNumber}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Outbound call failed");
    } finally {
      setDialingOutbound(false);
    }
  }

  if (loading) {
    return (
      <AppShell title="Agent Studio">
        <div className="flex items-center justify-center py-24">
          <Spinner className="w-8 h-8 text-primary" />
        </div>
      </AppShell>
    );
  }

  if (!agent) {
    return (
      <AppShell title="Agent Not Found">
        <div className="p-8 text-center">
          <p className="text-sm text-text-muted">Agent not found</p>
          <Link href="/agents" className="text-xs text-primary underline mt-2 inline-block">
            Back to Voice Agents
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={agentName || "Agent Studio"}>
      {/* ── Top Bar matching Sarvam AI Studio ── */}
      <div className="border-b border-border/50 bg-background/95 backdrop-blur -mx-6 -mt-6 px-6 py-3.5 mb-6 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {/* Left: Back & Agent Title */}
          <div className="flex items-center gap-3">
            <Link
              href="/agents"
              className="p-1.5 rounded-lg hover:bg-secondary text-text-muted hover:text-text-primary transition-colors"
              title="Back to agents"
            >
              <ChevronLeft className="w-5 h-5" />
            </Link>

            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-sm">
              {agentName.charAt(0).toUpperCase()}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                className="font-bold text-sm bg-transparent border-b border-transparent hover:border-border focus:border-primary focus:outline-none px-1 text-text-primary max-w-xs transition-colors"
                title="Click to rename agent"
              />
              {versions.length > 0 ? (
                <select
                  value={activeVersion?.id || ""}
                  onChange={(e) => loadAgent(e.target.value)}
                  className="text-[11px] font-medium px-2 py-0.5 rounded-lg bg-secondary text-text-secondary border border-border focus:outline-none focus:border-primary cursor-pointer"
                  title="Switch agent version"
                >
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      v{v.version} · {v.status === "published" ? (agent?.active_version_id === v.id ? "Active" : "Published") : "Draft"}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-secondary text-text-muted border border-border">
                  v1 · Draft
                </span>
              )}
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2.5">
            {hasUnsavedChanges ? (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-amber-500 font-medium bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                Unsaved changes
              </span>
            ) : lastSavedAt ? (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-emerald-500 font-medium bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Saved {lastSavedAt}
              </span>
            ) : null}

            <button
              onClick={handleImproveWithGenie}
              disabled={genieLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border border-amber-500/30 transition-colors shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              {genieLoading ? "Improving..." : "Improve with Genie"}
            </button>

            <Button
              onClick={handleSaveDraft}
              loading={saving}
              variant="secondary"
              size="sm"
              className="text-xs gap-1.5"
              title="Save draft version without activating"
            >
              <Save className="w-3.5 h-3.5" />
              Save Draft
            </Button>

            <Button
              onClick={handleSaveChanges}
              loading={saving || publishing}
              size="sm"
              className="text-xs gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-sm"
              title="Save changes and activate immediately (Ctrl+S)"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Save Changes
            </Button>
          </div>
        </div>
      </div>

      {/* ── Studio Main 3-Column Split Layout ── */}
      <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6 items-start pb-16">
        {/* ── Column 1: Left Vertical Navigation ── */}
        <div className="col-span-12 md:col-span-3 lg:col-span-2 flex flex-col justify-between space-y-6">
          <div className="space-y-1">
            <button
              onClick={() => setActiveTab("instructions")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "instructions"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <FileText className="w-4 h-4" />
              Instructions
            </button>

            <button
              onClick={() => setActiveTab("knowledge")}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "knowledge"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <div className="flex items-center gap-3">
                <BookOpen className="w-4 h-4" />
                Knowledge Base
              </div>
              {associatedKbIds.length > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === "knowledge" ? "bg-white/20 text-white" : "bg-primary/10 text-primary"
                }`}>
                  {associatedKbIds.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("variables")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "variables"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <Variable className="w-4 h-4" />
              Variables
            </button>

            <button
              onClick={() => setActiveTab("tools")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "tools"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <Wrench className="w-4 h-4" />
              Tools
            </button>

            <button
              onClick={() => setActiveTab("settings")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "settings"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <Sliders className="w-4 h-4" />
              Settings
            </button>

            <button
              onClick={() => setActiveTab("tests")}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "tests"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-text-secondary hover:bg-secondary/70 hover:text-text-primary"
              }`}
            >
              <CheckCheck className="w-4 h-4" />
              Automated tests
            </button>
          </div>

          {/* Bottom Deployment Status Card */}
          <div className="p-4 rounded-xl border border-border/60 bg-card/60 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                Deployment
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Ready
              </span>
            </div>
            <p className="text-[11px] text-text-muted leading-tight">
              Pinned to campaigns and live telephony.
            </p>
            <div className="space-y-1.5 pt-1">
              <button
                onClick={() => router.push("/campaigns")}
                className="w-full text-left text-[11px] font-medium text-primary hover:underline flex items-center justify-between"
              >
                Connect to campaign <ArrowRight className="w-3 h-3" />
              </button>
              <button
                onClick={() => router.push("/phone-numbers")}
                className="w-full text-left text-[11px] font-medium text-text-secondary hover:text-text-primary flex items-center justify-between"
              >
                Inbound phone routing <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        {/* ── Column 2: Center Canvas (Dynamic by Active Tab) ── */}
        <div className="col-span-12 md:col-span-9 lg:col-span-6 space-y-6">
          {/* TAB 1: Instructions & Greeting */}
          {activeTab === "instructions" && (
            <div className="space-y-6">
              {/* Greeting Card */}
              <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-text-primary">Greeting</h3>
                    <p className="text-xs text-text-muted">
                      The first sentence your agent speaks when the prospect picks up.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant={hasUnsavedChanges ? "primary" : "secondary"}
                      onClick={handleSaveChanges}
                      loading={saving}
                      className="text-xs h-7 px-2.5 gap-1.5 shadow-sm"
                      title="Save & activate agent greeting (Ctrl+S)"
                    >
                      <Save className="w-3.5 h-3.5" />
                      Save
                    </Button>
                    <button
                      onClick={() => setShowTranslateModal(true)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-text-secondary hover:text-text-primary border border-border transition-colors h-7"
                    >
                      <Languages className="w-3.5 h-3.5 text-primary" />
                      Translations
                    </button>
                  </div>
                </div>

                {/* Interactive Variable Chips */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] font-semibold text-text-muted mr-1">Insert chip:</span>
                  {Object.keys(inputVariables).map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => insertVariableIntoGreeting(k)}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-all cursor-pointer"
                    >
                      <span className="text-text-muted font-sans">&#123; &#125;</span> {k}
                    </button>
                  ))}
                </div>

                {/* Greeting Textarea */}
                <textarea
                  ref={greetingInputRef}
                  rows={2}
                  value={greeting}
                  onChange={(e) => {
                    setGreeting(e.target.value);
                    setHasUnsavedChanges(true);
                  }}
                  className="w-full p-3.5 rounded-xl text-xs leading-relaxed bg-secondary/30 border border-border focus:border-primary focus:outline-none text-text-primary resize-none font-medium"
                  placeholder="नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय."
                />
              </div>

              {/* Structured & Markdown Instructions Editor */}
              <div className="space-y-2">
                <div className="flex items-center justify-between px-1">
                  <span className="text-xs font-bold text-text-primary">Agent Instructions</span>
                  <Button
                    size="sm"
                    variant={hasUnsavedChanges ? "primary" : "secondary"}
                    onClick={handleSaveChanges}
                    loading={saving}
                    className="text-xs h-7 px-2.5 gap-1.5 shadow-sm"
                    title="Save & activate agent instructions (Ctrl+S)"
                  >
                    <Save className="w-3.5 h-3.5" />
                    Save Instructions
                  </Button>
                </div>
                <StructuredInstructionEditor
                  value={instructions}
                  onChange={(val) => {
                    setInstructions(val);
                    setHasUnsavedChanges(true);
                  }}
                  availableVariables={inputVariables}
                  agentName={agentName}
                  onReviewAgent={handleReviewAgent}
                  onImproveWithGenie={handleImproveWithGenie}
                  genieLoading={genieLoading}
                />
              </div>
            </div>
          )}

          {/* TAB 2: Variables */}
          {activeTab === "knowledge" && (
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-text-primary">Knowledge Base & Grounding</h3>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                      {associatedKbIds.length} Linked
                    </span>
                  </div>
                  <p className="text-xs text-text-muted mt-1">
                    Select the knowledge bases this agent uses to answer questions, handle objections, and explain products.
                  </p>
                </div>
                <Link href="/knowledge">
                  <Button variant="secondary" size="sm" className="text-xs">
                    <BookOpen className="w-3.5 h-3.5 mr-1.5" />
                    Manage Documents
                  </Button>
                </Link>
              </div>

              {/* Grounding Mode Selector */}
              <div className="p-4 rounded-xl border border-border bg-secondary/20 space-y-3">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-primary" />
                  <span className="text-xs font-bold text-text-primary">Response Grounding Mode</span>
                </div>
                <p className="text-xs text-text-secondary">
                  Choose how the agent behaves when asked questions about products, pricing, or terms:
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => setKnowledgeStrictness("flexible")}
                    className={`p-3.5 rounded-xl border text-left transition-all ${
                      knowledgeStrictness === "flexible"
                        ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary/30"
                        : "border-border bg-card hover:border-border-strong"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-text-primary">Flexible Grounding</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 font-semibold">Recommended</span>
                    </div>
                    <p className="text-[11px] text-text-muted mt-1 leading-relaxed">
                      Prioritizes Knowledge Base facts and pricing as primary truth, but allows warm, natural conversational fallback for general chit-chat and questions outside the KB.
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setKnowledgeStrictness("strict")}
                    className={`p-3.5 rounded-xl border text-left transition-all ${
                      knowledgeStrictness === "strict"
                        ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary/30"
                        : "border-border bg-card hover:border-border-strong"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-text-primary">Strict Grounding</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 font-semibold">Never Guess</span>
                    </div>
                    <p className="text-[11px] text-text-muted mt-1 leading-relaxed">
                      Strictly restricts answers to facts in the linked Knowledge Bases. If a question is not answered in the KB, the agent politely states it does not have that detail and offers a specialist follow-up.
                    </p>
                  </button>
                </div>
              </div>

              {/* Knowledge Bases Multi-select List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-text-primary">Available Knowledge Bases</span>
                  <span className="text-xs text-text-muted">{allKbs.length} available in organization</span>
                </div>

                {allKbs.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-dashed border-border bg-secondary/10">
                    <BookOpen className="w-8 h-8 mx-auto text-text-muted mb-2" />
                    <p className="text-xs font-semibold text-text-primary">No knowledge bases found</p>
                    <p className="text-[11px] text-text-muted mt-1 max-w-sm mx-auto">
                      Create a knowledge base with FAQs or product documentation for your AI agent to reference.
                    </p>
                    <Link href="/knowledge" className="inline-block mt-3">
                      <Button size="sm">Create Knowledge Base</Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {allKbs.map((kb) => {
                      const isLinked = associatedKbIds.includes(kb.id);
                      const isToggling = kbTogglingId === kb.id;
                      return (
                        <div
                          key={kb.id}
                          onClick={() => !isToggling && handleToggleKb(kb.id)}
                          className={`flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all ${
                            isLinked
                              ? "border-primary/50 bg-primary/5 shadow-sm"
                              : "border-border bg-card hover:border-border-strong"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              checked={isLinked}
                              disabled={isToggling}
                              onChange={() => {}}
                              className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                            />
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-text-primary">{kb.name}</span>
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-secondary text-text-secondary font-mono">
                                  {kb.document_count} doc{kb.document_count !== 1 ? "s" : ""}
                                </span>
                              </div>
                              {kb.description && (
                                <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">{kb.description}</p>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {isToggling ? (
                              <Spinner size="sm" />
                            ) : isLinked ? (
                              <span className="text-[11px] font-semibold text-primary flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Linked
                              </span>
                            ) : (
                              <span className="text-[11px] text-text-muted">Click to link</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Live Context Prompt Preview */}
              {associatedKbIds.length > 0 && (
                <div className="pt-2">
                  <details className="p-3.5 rounded-xl border border-border bg-secondary/10 group">
                    <summary className="text-xs font-semibold text-text-primary cursor-pointer flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-primary" />
                        Preview Injected Prompt Context
                      </span>
                      <span className="text-[10px] text-text-muted group-open:rotate-180 transition-transform">▼</span>
                    </summary>
                    <div className="mt-3 pt-3 border-t border-border">
                      <p className="text-[11px] text-text-secondary mb-2">
                        This is the formatted knowledge text injected into the AI calling engine for this agent:
                      </p>
                      <pre className="text-[11px] font-mono bg-card p-3 rounded-lg border border-border text-text-secondary whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {kbContextPreview || "Click 'Save Draft' to refresh preview context."}
                      </pre>
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}

          {activeTab === "variables" && (
            <div className="space-y-6">
              {/* Input Variables Card */}
              <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-text-primary">Input Variables</h3>
                    <p className="text-xs text-text-muted">
                      Campaign or lead data injected before each call starts.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      const key = prompt("Enter new variable key (e.g. partnerName, loanAmount):");
                      if (key && key.trim()) {
                        setInputVariables({ ...inputVariables, [key.trim()]: "" });
                      }
                    }}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-text-primary border border-border"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Variable
                  </button>
                </div>

                <div className="divide-y divide-border/50 border border-border/60 rounded-xl overflow-hidden">
                  {Object.entries(inputVariables).map(([k, val]) => (
                    <div key={k} className="p-3 bg-card/60 flex items-center justify-between gap-4">
                      <div className="w-1/3 min-w-0">
                        <span className="font-mono text-xs font-semibold text-primary">&#123;{k}&#125;</span>
                      </div>
                      <div className="flex-1">
                        <input
                          type="text"
                          value={val}
                          onChange={(e) =>
                            setInputVariables({ ...inputVariables, [k]: e.target.value })
                          }
                          className="w-full px-2.5 py-1 rounded-lg text-xs bg-secondary/50 border border-border focus:border-primary focus:outline-none text-text-primary"
                          placeholder="Default value"
                        />
                      </div>
                      <button
                        onClick={() => {
                          const copy = { ...inputVariables };
                          delete copy[k];
                          setInputVariables(copy);
                        }}
                        className="text-text-muted hover:text-red-400 p-1"
                        title="Delete variable"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Output Variables Card */}
              <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-text-primary">Output Variables</h3>
                    <p className="text-xs text-text-muted">
                      Key data extracted by the agent from the prospect during the call.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      const val = prompt("Enter output slot key to extract (e.g. budget, callback_time):");
                      if (val && val.trim() && !outputVariables.includes(val.trim())) {
                        setOutputVariables([...outputVariables, val.trim()]);
                      }
                    }}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-text-primary border border-border"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Slot
                  </button>
                </div>

                <div className="flex flex-wrap gap-2">
                  {outputVariables.map((slot) => (
                    <span
                      key={slot}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-medium bg-secondary text-text-secondary border border-border"
                    >
                      {slot}
                      <button
                        onClick={() =>
                          setOutputVariables(outputVariables.filter((s) => s !== slot))
                        }
                        className="text-text-muted hover:text-red-400"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Tools */}
          {activeTab === "tools" && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-text-primary">Agent Tools & Integrations</h3>
                  <p className="text-xs text-text-muted">
                    Automations executed automatically during or immediately after the call.
                  </p>
                </div>

                {/* WhatsApp Tool */}
                <div className="flex items-start justify-between p-4 rounded-xl border border-border/80 bg-secondary/20">
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-text-primary flex items-center gap-2">
                      💬 WhatsApp Calculation & Info Dispatch
                    </h4>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Sends immediate savings calculation, subsidy table, and brochure on caller agreement.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={toolWhatsApp}
                    onChange={(e) => setToolWhatsApp(e.target.checked)}
                    className="w-4 h-4 rounded text-primary mt-1"
                  />
                </div>

                {/* Calendar Tool */}
                <div className="flex items-start justify-between p-4 rounded-xl border border-border/80 bg-secondary/20">
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-text-primary flex items-center gap-2">
                      📅 Site Visit & Appointment Scheduling
                    </h4>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Schedules on-site engineer visit or video consultation in Google Calendar / CRM.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={toolCalendar}
                    onChange={(e) => setToolCalendar(e.target.checked)}
                    className="w-4 h-4 rounded text-primary mt-1"
                  />
                </div>

                {/* Webhook Tool */}
                <div className="space-y-3 p-4 rounded-xl border border-border/80 bg-secondary/20">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-text-primary">
                      🔗 Real-time CRM Lead Push Webhook
                    </h4>
                    <input
                      type="checkbox"
                      checked={toolWebhook}
                      onChange={(e) => setToolWebhook(e.target.checked)}
                      className="w-4 h-4 rounded text-primary"
                    />
                  </div>
                  {toolWebhook && (
                    <input
                      type="url"
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      placeholder="https://your-crm.com/api/leads"
                      className="w-full px-3 py-1.5 rounded-lg text-xs bg-secondary border border-border focus:border-primary focus:outline-none text-text-primary font-mono"
                    />
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Settings */}
          {activeTab === "settings" && (
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-5">
              <div>
                <h3 className="text-sm font-bold text-text-primary">Agent Voice & Telephony Settings</h3>
                <p className="text-xs text-text-muted">
                  Fine-tune speech synthesis, language, and conversational dynamics.
                </p>
              </div>

              <div className="space-y-4">
                <Select
                  label="Primary Voice Profile"
                  value={voiceProfileId}
                  onChange={(e) => {
                    const newVpId = e.target.value;
                    setVoiceProfileId(newVpId);
                    const chosen = voiceProfiles.find((p) => p.id === newVpId);
                    if (chosen && chosen.display_name.toLowerCase().includes("chitra")) {
                      setVoiceId("chaitra_hi_customer");
                    }
                  }}
                >
                  {voiceProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name} ({p.language})
                    </option>
                  ))}
                </Select>

                <Select
                  label="Voice Persona / Speaker"
                  value={voiceId}
                  onChange={(e) => setVoiceId(e.target.value)}
                >
                  <option value="">Default for Voice Profile</option>
                  <option value="chaitra_hi_customer">Chitra (Warm, Friendly, Multilingual)</option>
                  <option value="ishita_mr_conversational">Ishita (Conversational Marathi)</option>
                  <option value="kavya_hi_conversational">Kavya (Expressive Hindi)</option>
                  <option value="aditi_en_stories">Aditi (Clear Indian English)</option>
                  <option value="pooja_gu_conversational">Pooja (Gujarati Conversational)</option>
                  <option value="chaitra_kn_conversation">Chaitra (Kannada Conversational)</option>
                </Select>

                <Select
                  label="Primary Language"
                  value={primaryLanguage}
                  onChange={(e) => setPrimaryLanguage(e.target.value)}
                >
                  <option value="mr-IN">मराठी (Marathi - India)</option>
                  <option value="hi-IN">हिन्दी (Hindi - India)</option>
                  <option value="en-IN">English (India)</option>
                  <option value="ta-IN">தமிழ் (Tamil - India)</option>
                  <option value="te-IN">తెలుగు (Telugu - India)</option>
                  <option value="kn-IN">ಕನ್ನಡ (Kannada - India)</option>
                  <option value="bn-IN">বাংলা (Bengali - India)</option>
                  <option value="gu-IN">ગુજરાતી (Gujarati - India)</option>
                </Select>

                <div>
                  <div className="flex justify-between text-xs font-medium text-text-primary mb-1.5">
                    <span>Speech Speed / Rate</span>
                    <span className="font-mono text-primary">{speechSpeed.toFixed(1)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.8"
                    max="1.3"
                    step="0.05"
                    value={speechSpeed}
                    onChange={(e) => setSpeechSpeed(parseFloat(e.target.value))}
                    className="w-full accent-primary"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-text-primary mb-1.5">
                    <span>Interruption / Barge-in Sensitivity</span>
                    <span className="font-mono text-primary">{sensitivity}%</span>
                  </div>
                  <input
                    type="range"
                    min="30"
                    max="100"
                    step="5"
                    value={sensitivity}
                    onChange={(e) => setSensitivity(parseInt(e.target.value))}
                    className="w-full accent-primary"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: Automated Tests */}
          {activeTab === "tests" && (
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
              <div>
                <h3 className="text-sm font-bold text-text-primary">Automated Test Suites</h3>
                <p className="text-xs text-text-muted">
                  Simulate sample customer turns to verify compliance with your prompt guardrails.
                </p>
              </div>

              <div className="space-y-3">
                {[
                  { query: "बोला, काय काम आहे?", expected: "Frame value prop & ask monthly electricity bill" },
                  { query: "माझं बिल दोन हजार रुपये येतं.", expected: "Calculate annual ₹24,000 spend & ask roof space" },
                  { query: "नाही, मला कुणालाही घरी बोलवायचं नाही.", expected: "Zero-pressure WhatsApp calculation offer" },
                ].map((tc, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl border border-border/80 bg-secondary/30 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-text-primary">Scenario {idx + 1}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold">
                        Ready
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary">
                      Prospect says: <span className="font-medium text-text-primary">&ldquo;{tc.query}&rdquo;</span>
                    </p>
                    <p className="text-[11px] text-text-muted">
                      Expected goal: {tc.expected}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Column 3: Right Column Embedded Live Test Agent ── */}
        <div className="col-span-12 lg:col-span-4 sticky top-20">
          <div className="rounded-2xl border border-border bg-card shadow-xl overflow-hidden flex flex-col h-[700px]">
            {/* Test Agent Header with Tabs */}
            <div className="p-3.5 border-b border-border/60 bg-secondary/30 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold text-xs text-text-primary flex items-center gap-1.5">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                  Test Agent
                </span>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  Live Studio
                </span>
              </div>

              <div className="flex items-center bg-secondary/80 rounded-lg p-0.5 border border-border/60">
                <button
                  onClick={() => setTestTab("voice")}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                    testTab === "voice"
                      ? "bg-card text-text-primary shadow-sm"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                >
                  Voice
                </button>
                <button
                  onClick={() => setTestTab("chat")}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                    testTab === "chat"
                      ? "bg-card text-text-primary shadow-sm"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                >
                  Chat
                </button>
                <button
                  onClick={() => setTestTab("phone")}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                    testTab === "phone"
                      ? "bg-card text-text-primary shadow-sm"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                >
                  Phone
                </button>
              </div>
            </div>

            {/* Test Tab: VOICE MODE */}
            {testTab === "voice" && (
              <div className="flex-1 flex flex-col p-4 justify-between overflow-hidden">
                {/* Voice Call Visualizer & Status */}
                <div className="p-4 rounded-xl border border-border/60 bg-secondary/20 flex flex-col items-center justify-center space-y-3">
                  {/* Status Indicator Pill */}
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-card border border-border shadow-sm">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        callActive
                          ? isSpeaking
                            ? "bg-emerald-400 animate-ping"
                            : "bg-emerald-400"
                          : "bg-gray-400"
                      }`}
                    />
                    <span className="text-text-primary">{callStatus}</span>
                  </div>

                  {/* Pulsing Audio Waves */}
                  <div className="flex items-center gap-1.5 h-10 py-1">
                    {[40, 75, 50, 90, 60, 30, 80, 65, 45, 95, 70, 40].map((h, i) => (
                      <span
                        key={i}
                        className={`w-1 rounded-full transition-all duration-150 ${
                          isSpeaking
                            ? "bg-emerald-400"
                            : callActive
                            ? "bg-primary/60"
                            : "bg-border"
                        }`}
                        style={{
                          height: callActive && (isSpeaking || isListening) ? `${h}%` : "15%",
                        }}
                      />
                    ))}
                  </div>

                  {/* Call Controls: Mic Mute & Start/End */}
                  <div className="flex items-center gap-3 pt-1">
                    <button
                      onClick={() => {
                        const next = !micMuted;
                        setMicMuted(next);
                        micMutedRef.current = next;
                      }}
                      disabled={!callActive}
                      className={`p-2.5 rounded-full border transition-all ${
                        micMuted
                          ? "bg-red-500/20 text-red-400 border-red-500/40"
                          : "bg-secondary text-text-primary border-border hover:bg-secondary/80"
                      }`}
                      title={micMuted ? "Unmute Mic" : "Mute Mic"}
                    >
                      {micMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>

                    {!callActive ? (
                      <button
                        onClick={handleStartCall}
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30 transition-all hover:scale-105"
                      >
                        <Phone className="w-4 h-4" /> Start Call
                      </button>
                    ) : (
                      <button
                        onClick={() => handleEndCall("Disconnected")}
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-bold bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/30 transition-all hover:scale-105"
                      >
                        <PhoneOff className="w-4 h-4" /> End Call
                      </button>
                    )}
                  </div>

                  {callActive && (
                    <span className="text-[10px] text-text-muted flex items-center gap-1 pt-0.5">
                      <ShieldCheck className="w-3 h-3 text-emerald-500" />
                      Fan &amp; Echo Filter Active ({sensitivity}% sens.)
                    </span>
                  )}
                </div>

                {/* Real-time Conversation Transcript */}
                <div className="flex-1 my-3 overflow-y-auto space-y-2.5 pr-1 scrollbar-thin">
                  {transcript.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4 text-text-muted">
                      <Bot className="w-8 h-8 mb-2 opacity-40" />
                      <p className="text-xs">Click Start Call to test your agent live with microphone and audio.</p>
                    </div>
                  ) : (
                    transcript.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${
                          msg.sender === "user" ? "items-end" : "items-start"
                        }`}
                      >
                        <span className="text-[10px] text-text-muted mb-0.5 px-1">
                          {msg.sender === "user" ? "You (Mic)" : agentName} · {msg.time}
                        </span>
                        <div
                          className={`max-w-[85%] px-3 py-2 rounded-2xl text-xs leading-relaxed ${
                            msg.sender === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-none"
                              : "bg-secondary text-text-primary rounded-tl-none border border-border/70"
                          }`}
                        >
                          {msg.text}
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={transcriptEndRef} />
                </div>

                {/* Real-time Output Variables Disposition Card */}
                <div className="p-3 rounded-xl border border-border/60 bg-secondary/30 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-bold text-text-primary">
                    <span>Live Extracted Disposition</span>
                    <span className="text-[10px] text-primary font-mono">
                      {Object.keys(extractedVariables).length} slots
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                    {outputVariables.slice(0, 4).map((k) => (
                      <div key={k} className="p-1.5 rounded-lg bg-card border border-border/40 truncate">
                        <span className="text-text-muted block truncate">{k}:</span>
                        <span className="font-semibold text-text-primary truncate">
                          {extractedVariables[k] || "—"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Test Tab: CHAT MODE */}
            {testTab === "chat" && (
              <div className="flex-1 flex flex-col p-4 justify-between overflow-hidden">
                <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 scrollbar-thin">
                  {transcript.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4 text-text-muted">
                      <MessageSquare className="w-8 h-8 mb-2 opacity-40" />
                      <p className="text-xs">Type a message below to test your agent without using your mic.</p>
                    </div>
                  ) : (
                    transcript.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${
                          msg.sender === "user" ? "items-end" : "items-start"
                        }`}
                      >
                        <span className="text-[10px] text-text-muted mb-0.5 px-1">
                          {msg.sender === "user" ? "You" : agentName} · {msg.time}
                        </span>
                        <div
                          className={`max-w-[85%] px-3 py-2 rounded-2xl text-xs leading-relaxed ${
                            msg.sender === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-none"
                              : "bg-secondary text-text-primary rounded-tl-none border border-border/70"
                          }`}
                        >
                          {msg.text}
                        </div>
                      </div>
                    ))
                  )}
                  <div ref={transcriptEndRef} />
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-border/60">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                    placeholder="Type prospect reply (e.g. बोला, सांगा)..."
                    className="flex-1 px-3 py-2 rounded-xl text-xs bg-secondary/50 border border-border focus:border-primary focus:outline-none text-text-primary"
                  />
                  <button
                    onClick={handleSendChat}
                    className="p-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Test Tab: PHONE MODE */}
            {testTab === "phone" && (
              <div className="flex-1 p-5 flex flex-col justify-center space-y-4 text-center">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mx-auto">
                  <Phone className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-text-primary">Call Your Real Phone</h4>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    Test this agent live on your phone using your organization&apos;s assigned calling number.
                  </p>
                </div>

                <div className="space-y-3 pt-2 text-left">
                  {assignedNumbers.length > 0 ? (
                    <Select
                      label="Caller ID / Calling Number"
                      value={selectedCallingNumber}
                      onChange={(e) => setSelectedCallingNumber(e.target.value)}
                      options={assignedNumbers.map((p) => ({
                        value: p.number,
                        label: `${p.number} (${p.display_name || p.provider || "Assigned"})`,
                      }))}
                    />
                  ) : (
                    <div className="p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-500 text-xs">
                      No phone numbers assigned to your organization. Please ask an admin to assign a number.
                    </div>
                  )}

                  <div>
                    <label className="text-xs font-medium text-text-primary block mb-1">
                      Your Phone Number (Destination)
                    </label>
                    <input
                      type="tel"
                      value={outboundPhone}
                      onChange={(e) => setOutboundPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full text-center py-2.5 rounded-xl text-sm font-mono bg-secondary/50 border border-border focus:border-primary focus:outline-none text-text-primary"
                    />
                  </div>

                  <Button
                    onClick={handleDialPhone}
                    loading={dialingOutbound}
                    disabled={assignedNumbers.length === 0}
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground gap-2 text-xs"
                  >
                    <Phone className="w-4 h-4" />
                    Place Test Phone Call
                  </Button>
                </div>
              </div>
            )}

            {/* Bottom Pipeline Setup Pill */}
            <div className="px-3.5 py-2 border-t border-border/50 bg-secondary/40 text-[10px] text-text-muted flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-medium">
                <span className="text-text-muted">Pipeline:</span>
                <span
                  title={pipelineStatus.stt ? "STT: Connected" : "STT: Disconnected"}
                  className={`inline-flex items-center gap-1 font-semibold ${
                    pipelineStatus.stt ? "text-emerald-500" : "text-rose-500"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      pipelineStatus.stt ? "bg-emerald-500" : "bg-rose-500"
                    }`}
                  />
                  STT
                </span>
                <span className="text-text-muted/60">·</span>
                <span
                  title={pipelineStatus.llm ? "LLM: Connected" : "LLM: Disconnected"}
                  className={`inline-flex items-center gap-1 font-semibold ${
                    pipelineStatus.llm ? "text-emerald-500" : "text-rose-500"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      pipelineStatus.llm ? "bg-emerald-500" : "bg-rose-500"
                    }`}
                  />
                  LLM
                </span>
                <span className="text-text-muted/60">·</span>
                <span
                  title={pipelineStatus.tts ? "TTS: Connected" : "TTS: Disconnected"}
                  className={`inline-flex items-center gap-1 font-semibold ${
                    pipelineStatus.tts ? "text-emerald-500" : "text-rose-500"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      pipelineStatus.tts ? "bg-emerald-500" : "bg-rose-500"
                    }`}
                  />
                  TTS
                </span>
              </div>
              <span className="font-mono text-text-secondary">{primaryLanguage}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Translations Modal ── */}
      <Modal
        isOpen={showTranslateModal}
        onClose={() => setShowTranslateModal(false)}
        title="🌐 Multilingual Agent Translations"
      >
        <div className="space-y-4">
          <p className="text-xs text-text-muted">
            Select a target Indian language to automatically translate greeting and instructions.
          </p>

          <Select
            label="Translate To"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
          >
            <option value="hi-IN">हिन्दी (Hindi)</option>
            <option value="mr-IN">मराठी (Marathi)</option>
            <option value="en-IN">English</option>
            <option value="ta-IN">தமிழ் (Tamil)</option>
            <option value="te-IN">తెలుగు (Telugu)</option>
            <option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
            <option value="bn-IN">বাংলা (Bengali)</option>
            <option value="gu-IN">ગુજરાતી (Gujarati)</option>
            <option value="ml-IN">മലയാളം (Malayalam)</option>
            <option value="pa-IN">ਪੰਜਾਬੀ (Punjabi)</option>
          </Select>

          <div className="space-y-2 pt-1 border-t border-border/60">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-text-secondary">
              <input
                type="checkbox"
                checked={translateInstructions}
                onChange={(e) => setTranslateInstructions(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-primary"
              />
              <span>Also translate agent instructions</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-xs text-text-secondary">
              <input
                type="checkbox"
                checked={saveAsDraftOnTranslate}
                onChange={(e) => setSaveAsDraftOnTranslate(e.target.checked)}
                className="w-3.5 h-3.5 rounded text-primary"
              />
              <span className="font-medium text-text-primary">
                Store translated version directly as a new saved draft
              </span>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => setShowTranslateModal(false)}
            >
              Cancel
            </Button>
            <Button
              disabled={translating}
              loading={translating}
              onClick={async () => {
                if (!greeting.trim()) {
                  toast.error("Please write a greeting first before translating.");
                  return;
                }
                setTranslating(true);
                try {
                  const res = await api.agents.translateGreeting({
                    text: greeting,
                    target_language: targetLang,
                  });
                  const translatedGreeting = res.translated_text;
                  setGreeting(translatedGreeting);
                  setPrimaryLanguage(targetLang);

                  let translatedInst = instructions;
                  if (translateInstructions && instructions.trim()) {
                    try {
                      const instRes = await api.agents.translateGreeting({
                        text: instructions,
                        target_language: targetLang,
                      });
                      if (instRes.translated_text) {
                        translatedInst = instRes.translated_text;
                        setInstructions(translatedInst);
                      }
                    } catch (err) {
                      console.warn("Instructions translation fallback:", err);
                    }
                  }

                  if (saveAsDraftOnTranslate && id) {
                    const payload = buildConfigPayload({
                      greeting: translatedGreeting,
                      primary_language: targetLang,
                      system_prompt: translatedInst,
                    });
                    const newVer = await api.agents.versions.create(id, {
                      configuration: payload,
                      description: `Translated (${targetLang}) draft saved ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
                      auto_activate: false,
                    });
                    await loadAgent(newVer.id);
                    toast.success("Greeting translated and saved as draft version!");
                  } else {
                    toast.success("Greeting translated successfully!");
                  }

                  setShowTranslateModal(false);
                } catch (e: unknown) {
                  toast.error(
                    e instanceof Error ? e.message : "Translation failed. Please try again."
                  );
                } finally {
                  setTranslating(false);
                }
              }}
            >
              {translating ? "Translating..." : saveAsDraftOnTranslate ? "Translate & Save Draft" : "Apply Translation"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Review Agent Modal ── */}
      <Modal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        title="✨ Agent Quality & Guardrails Review"
      >
        <div className="space-y-4">
          <p className="text-xs text-text-muted">
            Evaluation against conversational voice design best practices:
          </p>

          <div className="space-y-2.5">
            {reviewTips.map((tip, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl border border-border/80 bg-secondary/30 flex items-start gap-2.5 text-xs text-text-secondary leading-relaxed"
              >
                <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>{tip}</span>
              </div>
            ))}
          </div>

          <div className="flex justify-end pt-2">
            <Button onClick={() => setShowReviewModal(false)}>
              Got it
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}
