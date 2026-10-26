"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { marked } from "marked";
import {
  Sparkles,
  Columns,
  Eye,
  Edit3,
  List,
  ListOrdered,
  Bold,
  Italic,
  Strikethrough,
  Code,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  Plus,
  Trash2,
  ChevronDown,
  Layers,
  FileCode,
  Sliders,
  HelpCircle,
  Copy,
  Check,
  RotateCcw,
  BookOpen,
  ArrowUp,
  ArrowDown,
  Info,
} from "lucide-react";
import toast from "react-hot-toast";

export interface StructuredInstructionEditorProps {
  value: string;
  onChange: (val: string) => void;
  availableVariables?: Record<string, string>;
  agentName?: string;
  onReviewAgent?: () => void;
  onImproveWithGenie?: () => void;
  genieLoading?: boolean;
}

interface ConversationPhase {
  id: string;
  name: string;
  trigger: string;
  action: string;
}

interface ObjectionItem {
  id: string;
  objection: string;
  response: string;
}

interface StructuredState {
  role: string;
  partnerRepresentation: string;
  tone: string;
  languageAndScript: string;
  aiDisclosure: string;
  maxWordsPerTurn: string;
  rules: string[];
  phases: ConversationPhase[];
  objections: ObjectionItem[];
  additionalNotes: string;
}

const TEMPLATES: Record<
  string,
  { label: string; description: string; markdown: string }
> = {
  solar: {
    label: "Rooftop Solar Consultation (Bilingual Marathi / English)",
    description: "PM Surya Ghar subsidy, bill discovery, rooftop evaluation, free site survey & WhatsApp info dispatch.",
    markdown: `# Role & Persona
- **Agent Name**: {salesRepName}
- **Role**: Warm, consultative rooftop solar advisor at {partnerName} calling homeowners and business owners in Maharashtra, India.
- **Tone**: Warm, polite, consultative, curious. Discovery is 70% listening, 30% talking.
- **Language**: Always speak natural, fluent Marathi (मराठी) in Devanagari script. Keep industry terms natural (kW, subsidy, WhatsApp, solar panel).
- **Identity Disclosure**: If asked whether you are AI, state clearly: "मी {partnerName} कडून एआय सोलर असिस्टंट आहे" and continue seamlessly.

## Conversational Rules
1. **Never Re-Greet**: The greeting was already spoken. NEVER say 'नमस्कार' or re-introduce yourself mid-call.
2. **Under 25 Words Per Turn**: Keep all turns short, snappy, and conversational. Talk; do not read essays.
3. **Strictly One Question Per Turn**: A turn may carry a short acknowledgment plus exactly ONE question. Never ask two questions at once.
4. **Acknowledge Before You Ask**: After each answer, reflect it back in 3-5 words first, then ask the next question.

## Conversation Flow
- **Phase 1 (Frame Call & Value Proposition)**: When caller says 'बोला', 'हो बोला', 'सांगा', 'काय काम आहे' or listens: State value proposition: 'पंतप्रधान सूर्य घर योजनेअंतर्गत ₹७८,००० पर्यंत सरकारी सबसिडी मिळवून तुम्ही {productCategory} बसवून वीज बिल ८० ते ९०% कमी करू शकता.' Then ask: 'सध्या तुमचं महिन्याचं सरासरी वीज बिल किती येतं?'
- **Phase 2 (Discover Bill & Annual Math)**: When they state their bill (e.g. ₹2,000): Calculate annual savings: 'दोन हजार म्हणजे वर्षाला तुमचे जवळपास ₹२४,००० विजेवर खर्च होतात! २ kW सोलरने हे बिल जवळपास शून्य होईल आणि ₹७८,००० सबसिडीही मिळेल.' Then ask: 'तुमच्या छतावर स्वतःची मोकळी जागा आहे का, जिथे चांगलं ऊन असतं?'
- **Phase 3 (Free Site Survey Offer)**: When they confirm rooftop space / sunlight: Offer free evaluation: 'छान! मग आमच्या कंपनीकडून एका इंजिनिअरला तुमच्या घरी मोफत साईट व्हिजिटसाठी पाठवू का, जेणेकरून ते येऊन नेमका अंदाज सांगू शकतील?'
- **Phase 4 (Zero-Pressure WhatsApp Offer on Refusal)**: If they decline a site visit ('नाही', 'नको'): DO NOT HANG UP OR ARGUE. Offer a zero-pressure WhatsApp calculation: 'काही हरकत नाही! मी कोणताही आग्रह करत नाही. तुमच्या याच नंबरवर व्हॉट्सॲप आहे का? मी २ मिनिटांत २ kW सोलरचा खर्च, सबसिडी आणि बचतीची संपूर्ण माहिती पाठवून देते, जेणेकरून तुम्ही निवांत पाहू शकाल.'
- **Phase 5 (Farewell & Wrap-up)**: When caller agrees to WhatsApp ('हो', 'पाठवा', 'ठीक आहे') OR firmly rejects everything ('काही नको', 'फोन ठेवा'): Conclude warmly: 'नक्कीच, मी लगेच व्हॉट्सॲपवर माहिती पाठवते. {partnerName} शी बोलल्याबद्दल धन्यवाद, तुमचा दिवस शुभ जावो! [HANGUP]'.

## Objection Handling & Edge Cases
- **Already has solar**: "खूप छान! तुमच्या अनुभवाबद्दल ऐकून आनंद झाला. धन्यवाद आणि तुमचा दिवस शुभ जावो!"
- **Caller is busy**: "काही हरकत नाही! मी तुम्हाला नंतर कधी फोन करू, किंवा व्हॉट्सॲपवर माहिती पाठवून देऊ?"
- **Cost / Price inquiry**: "२ kW सिस्टीमचा एकूण खर्च साधारण ₹१,२०,००० येतो, पण ₹७८,००० थेट सरकारी सबसिडी वजा जाता तुम्हाला फक्त ₹४२,००० भरावे लागतात."`,
  },
  realestate: {
    label: "Real Estate Site-Visit Booking (Kavya)",
    description: "Property consultation, budget qualification, locality preference, and VIP site visit booking.",
    markdown: `# Role & Persona
- **Agent Name**: {salesRepName}
- **Role**: Warm property consultation specialist at {partnerName} in India.
- **Tone**: Enthusiastic, polite, attentive. Makes buyers feel excited about finding their dream home.
- **Language**: English with culturally warm phrasing or natural Hinglish.
- **Identity Disclosure**: If asked, confirm you are an AI assistant helping schedule viewing appointments for {partnerName}.

## Conversational Rules
1. **Under 25 Words Per Turn**: Keep replies crisp and engaging.
2. **Strictly One Question Per Turn**: Focus on one detail at a time (budget, timeline, or configuration).
3. **Acknowledge Enthusiastically**: React warmly to their preferences before asking the next question.
4. **Never Speak Formatting**: No asterisks, markdown bullets, or emojis in spoken output.

## Conversation Flow
- **Phase 1 (Requirement Discovery)**: Learn whether they are looking for personal residence or investment, and preferred configuration ({productCategory}).
- **Phase 2 (Budget & Timeline)**: Clarify budget bracket (in ₹ Lakhs/Crores) and expected move-in timeline (ready-to-move vs under-construction).
- **Phase 3 (Location Match)**: Match preferred Indian locality/sector with current inventory and highlight key amenities.
- **Phase 4 (Site Visit Call-to-Action)**: Propose a weekend site visit or virtual tour walkthrough: 'We have sample flats available for viewing this Saturday. Would morning or afternoon suit you better?'
- **Phase 5 (Confirmation & Close)**: Reiterate appointment time, confirm location pin will be shared on WhatsApp, and wrap up warmly.

## Objection Handling & Edge Cases
- **Too expensive**: "I completely understand! We also have flexible milestone-linked payment plans and special bank pre-approved offers."
- **Just looking around**: "That's wonderful! Visiting the site gives the best feel of the layout and daylight with zero pressure to book."`,
  },
  insurance: {
    label: "Health Insurance Policy Renewal (Riya)",
    description: "No-claim bonus reminder, coverage enhancement, and instant payment link dispatch.",
    markdown: `# Role & Persona
- **Agent Name**: {salesRepName}
- **Role**: Trusted policy advisor at {partnerName}.
- **Tone**: Professional, empathetic, reassuring.
- **Language**: Hindi / Hinglish in clear conversational style.

## Conversational Rules
1. **Never Re-Greet**: Don't say Namaste again after the initial greeting.
2. **Under 25 Words Per Turn**: Clear, calm sentences without jargon.
3. **One Question Per Turn**: Keep decision making simple for the policyholder.

## Conversation Flow
- **Phase 1 (Highlight Benefit)**: Remind them of accumulated No-Claim Bonus (NCB) and cashless hospital network coverage.
- **Phase 2 (Check Claim Experience)**: Inquire if they need any modifications or top-ups for family members.
- **Phase 3 (Instant Renewal)**: Offer to trigger the secure one-click renewal link directly to their WhatsApp/SMS.
- **Phase 4 (Graceful Farewell)**: Confirm receipt and wish them good health.`,
  },
  b2b_saas: {
    label: "B2B SaaS Inbound Qualification",
    description: "Speed-to-lead agent for inbound inquiries, qualifying team size, tech stack, and booking demo.",
    markdown: `# Role & Persona
- **Agent Name**: {salesRepName}
- **Role**: Solutions specialist at {partnerName}.
- **Tone**: Sharp, knowledgeable, respectful of customer time.
- **Language**: Professional conversational English.

## Conversational Rules
1. **Under 20 Words Per Turn**: Executive brevity.
2. **Strictly One Question Per Turn**: Never overwhelm the caller.
3. **Reflect Pain Points**: Mirror the customer's use-case.

## Conversation Flow
- **Phase 1 (Problem Discovery)**: Understand the core challenge that prompted them to evaluate {productCategory}.
- **Phase 2 (Team & Scale)**: Discover current team size and systems currently in place.
- **Phase 3 (Demo Booking)**: Propose a 20-minute tailored executive demo with our solutions architect.
- **Phase 4 (Calendar Confirmation)**: Confirm email calendar invite dispatch.`,
  },
};

export function StructuredInstructionEditor({
  value,
  onChange,
  availableVariables = {},
  agentName = "Voice Agent",
  onReviewAgent,
  onImproveWithGenie,
  genieLoading = false,
}: StructuredInstructionEditorProps) {
  // Mode: "structured" (Guided form builder) vs "markdown" (Raw markdown editor & preview)
  const [mode, setMode] = useState<"structured" | "markdown">("markdown");

  // Markdown Subview: "write" | "split" | "preview"
  const [view, setView] = useState<"write" | "split" | "preview">("split");

  // Template dropdown modal state
  const [showTemplatesModal, setShowTemplatesModal] = useState(false);
  const [showVariablesDropdown, setShowVariablesDropdown] = useState(false);
  const [showSnippetsDropdown, setShowSnippetsDropdown] = useState(false);

  // Copy indicator
  const [copied, setCopied] = useState(false);

  // Textarea ref for inserting formatting
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // ---------------------------------------------------------------------------
  // Markdown <-> Structured State Conversion
  // ---------------------------------------------------------------------------
  const [structured, setStructured] = useState<StructuredState>(() =>
    parseMarkdownToStructured(value)
  );

  const structuredRef = useRef<StructuredState>(structured);
  useEffect(() => {
    structuredRef.current = structured;
  }, [structured]);

  // Whenever external value changes significantly from outside, update structured
  useEffect(() => {
    // Only re-parse if not actively typing or if mode changes
    const currentCompiled = compileStructuredToMarkdown(structuredRef.current);
    if (value.trim() !== currentCompiled.trim()) {
      setStructured(parseMarkdownToStructured(value));
    }
  }, [value]);

  // Synchronize Structured changes back to parent markdown
  function updateStructured(updater: (prev: StructuredState) => StructuredState) {
    setStructured((prev) => {
      const next = updater(prev);
      const compiled = compileStructuredToMarkdown(next);
      onChange(compiled);
      return next;
    });
  }

  // ---------------------------------------------------------------------------
  // Parse Markdown to Structured State (Zero Data Loss)
  // ---------------------------------------------------------------------------
  function parseMarkdownToStructured(md: string): StructuredState {
    if (!md || !md.trim()) {
      return {
        role: "",
        partnerRepresentation: "{partnerName}",
        tone: "Warm, polite, conversational",
        languageAndScript: "",
        aiDisclosure: "",
        maxWordsPerTurn: "Under 25 words",
        rules: [
          "Under 25 words per turn.",
          "Strictly one question per turn.",
          "Acknowledge before asking.",
        ],
        phases: [
          {
            id: "p1",
            name: "Phase 1: Framing & Discovery",
            trigger: "Prospect responds or listens",
            action: "State purpose and ask the first discovery question.",
          },
        ],
        objections: [],
        additionalNotes: "",
      };
    }

    const lines = md.split("\n");
    let currentSection = "root";

    let role = "";
    let partnerRepresentation = "";
    let tone = "";
    let languageAndScript = "";
    let aiDisclosure = "";
    let maxWordsPerTurn = "Under 25 words";
    const rules: string[] = [];
    const phases: ConversationPhase[] = [];
    const objections: ObjectionItem[] = [];
    const otherNotes: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const lower = line.toLowerCase();
      if (lower.startsWith("# role") || lower.startsWith("## role") || lower.startsWith("# persona")) {
        currentSection = "role";
        continue;
      } else if (lower.startsWith("## conversational rule") || lower.startsWith("# conversational rule") || lower.startsWith("## rule")) {
        currentSection = "rules";
        continue;
      } else if (lower.startsWith("## conversation flow") || lower.startsWith("# conversation flow") || lower.startsWith("## flow") || lower.startsWith("## stages") || lower.startsWith("## phases")) {
        currentSection = "phases";
        continue;
      } else if (lower.startsWith("## objection") || lower.startsWith("# objection")) {
        currentSection = "objections";
        continue;
      } else if (line.startsWith("#")) {
        currentSection = "other";
      }

      if (currentSection === "role") {
        if (line.includes("**Agent Name**") || line.includes("Agent Name:")) {
          // ignore or parse
        } else if (line.includes("**Role**") || line.includes("Role:")) {
          role = line.replace(/^[*-]\s*(\*\*Role\*\*|Role:)\s*/i, "").trim();
        } else if (line.includes("**Tone**") || line.includes("Tone:")) {
          tone = line.replace(/^[*-]\s*(\*\*Tone\*\*|Tone:)\s*/i, "").trim();
        } else if (line.includes("**Language**") || line.includes("Language:")) {
          languageAndScript = line.replace(/^[*-]\s*(\*\*Language\*\*|Language:)\s*/i, "").trim();
        } else if (line.includes("Identity Disclosure") || line.includes("AI:")) {
          aiDisclosure = line.replace(/^[*-]\s*(\*\*Identity Disclosure\*\*|Identity Disclosure:)\s*/i, "").trim();
        } else if (line.includes("Representation") || line.includes("Partner")) {
          partnerRepresentation = line.replace(/^[*-]\s*.*:\s*/i, "").trim();
        } else {
          if (!role && line.length > 3) role = line.replace(/^[*-]\s*/, "");
          else otherNotes.push(line);
        }
      } else if (currentSection === "rules") {
        const cleanedRule = line.replace(/^(\d+\.|[*-])\s*/, "").trim();
        if (cleanedRule) {
          rules.push(cleanedRule);
        }
      } else if (currentSection === "phases") {
        const matchPhase = line.match(/^[*-]\s*\*\*(Phase\s*\d+[^:*]*)\*\*\s*:\s*(.*)$/i) ||
                           line.match(/^[*-]\s*\*\*([^*]+)\*\*\s*:\s*(.*)$/);
        if (matchPhase) {
          phases.push({
            id: Math.random().toString(),
            name: matchPhase[1].trim(),
            trigger: "Prospect responds or listens",
            action: matchPhase[2].trim(),
          });
        } else {
          phases.push({
            id: Math.random().toString(),
            name: line.slice(0, 30),
            trigger: "",
            action: line.slice(30).replace(/^:\s*/, ""),
          });
        }
      } else if (currentSection === "objections") {
        const matchObj = line.match(/^[*-]\s*\*\*([^*]+)\*\*\s*:\s*(.*)$/);
        if (matchObj) {
          objections.push({
            id: Math.random().toString(),
            objection: matchObj[1].trim(),
            response: matchObj[2].trim(),
          });
        } else {
          otherNotes.push(line);
        }
      } else {
        otherNotes.push(line);
      }
    }

    return {
      role: role || "",
      partnerRepresentation: partnerRepresentation || "{partnerName}",
      tone: tone || "",
      languageAndScript: languageAndScript || "",
      aiDisclosure: aiDisclosure || "",
      maxWordsPerTurn: maxWordsPerTurn || "Under 25 words",
      rules,
      phases,
      objections,
      additionalNotes: otherNotes.join("\n"),
    };
  }

  // ---------------------------------------------------------------------------
  // Compile Structured State to Clean Markdown
  // ---------------------------------------------------------------------------
  function compileStructuredToMarkdown(s: StructuredState): string {
    const parts: string[] = [];

    // Persona Section
    parts.push("# Role & Persona");
    parts.push(`- **Agent Name**: {salesRepName}`);
    if (s.role) parts.push(`- **Role**: ${s.role}`);
    if (s.tone) parts.push(`- **Tone**: ${s.tone}`);
    if (s.languageAndScript) parts.push(`- **Language**: ${s.languageAndScript}`);
    if (s.aiDisclosure) parts.push(`- **Identity Disclosure**: ${s.aiDisclosure}`);

    // Rules Section
    parts.push("\n## Conversational Rules");
    if (s.rules && s.rules.length > 0) {
      s.rules.forEach((r, idx) => {
        parts.push(`${idx + 1}. ${r}`);
      });
    }

    // Phases Section
    if (s.phases && s.phases.length > 0) {
      parts.push("\n## Conversation Flow");
      s.phases.forEach((p) => {
        parts.push(`- **${p.name}**: ${p.action}`);
      });
    }

    // Objections Section
    if (s.objections && s.objections.length > 0) {
      parts.push("\n## Objection Handling & Edge Cases");
      s.objections.forEach((o) => {
        parts.push(`- **${o.objection}**: "${o.response}"`);
      });
    }

    // Additional notes
    if (s.additionalNotes && s.additionalNotes.trim()) {
      parts.push(`\n## Guardrails & Notes\n${s.additionalNotes.trim()}`);
    }

    return parts.join("\n");
  }

  // ---------------------------------------------------------------------------
  // Markdown Toolbar Helpers
  // ---------------------------------------------------------------------------
  function wrapSelection(prefix: string, suffix: string = prefix, defaultPlaceholder: string = "text") {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const selected = el.value.substring(start, end) || defaultPlaceholder;
    const replacement = `${prefix}${selected}${suffix}`;
    const nextVal = el.value.substring(0, start) + replacement + el.value.substring(end);
    onChange(nextVal);
    setTimeout(() => {
      el.focus();
      el.setSelectionRange(start + prefix.length, start + prefix.length + selected.length);
    }, 10);
  }

  function insertPrefix(prefix: string) {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const before = el.value.substring(0, start);
    const after = el.value.substring(start);
    const needsNewline = before.length > 0 && !before.endsWith("\n");
    const replacement = `${needsNewline ? "\n" : ""}${prefix}`;
    const nextVal = before + replacement + after;
    onChange(nextVal);
    setTimeout(() => {
      el.focus();
      const pos = start + replacement.length;
      el.setSelectionRange(pos, pos);
    }, 10);
  }

  function insertVariable(varName: string) {
    wrapSelection(`{${varName}}`, "", "");
    setShowVariablesDropdown(false);
  }

  function insertSnippet(content: string) {
    insertPrefix(`\n${content}\n`);
    setShowSnippetsDropdown(false);
  }

  function handleLoadTemplate(tplKey: string) {
    const tpl = TEMPLATES[tplKey];
    if (!tpl) return;
    onChange(tpl.markdown);
    setStructured(parseMarkdownToStructured(tpl.markdown));
    setShowTemplatesModal(false);
    toast.success(`Loaded template: ${tpl.label}`);
  }

  function handleCopyMarkdown() {
    navigator.clipboard.writeText(value);
    setCopied(true);
    toast.success("Markdown instructions copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  }

  // ---------------------------------------------------------------------------
  // Live Markdown HTML rendering with Highlighted Variables
  // ---------------------------------------------------------------------------
  const renderedHtml = useMemo(() => {
    try {
      const rawHtml = marked.parse(value || "*No instructions defined yet.*", {
        breaks: true,
        gfm: true,
      }) as string;

      // Highlight {variableName} as modern interactive chips
      const withChips = rawHtml.replace(
        /\{([a-zA-Z0-9_]+)\}/g,
        `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-semibold bg-primary/15 text-primary border border-primary/25 cursor-help" title="Dynamic variable replaced per call">{$1}</span>`
      );

      return withChips;
    } catch (e) {
      return `<p class="text-red-400">Markdown rendering error: ${String(e)}</p>`;
    }
  }, [value]);

  // Telemetry metrics
  const wordCount = useMemo(() => (value.trim() ? value.trim().split(/\s+/).length : 0), [value]);
  const charCount = value.length;
  const tokenEstimate = Math.round(charCount / 3.8);

  return (
    <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
      {/* ── Top Header & Mode Toggle ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/60 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-text-primary">Agent Instructions</h3>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              {mode === "structured" ? "Structured Builder" : "Markdown Prompt"}
            </span>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Define role, persona, conversation stages, objection handling, and voice guardrails.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mode Switcher */}
          <div className="inline-flex p-1 bg-secondary/80 rounded-xl border border-border">
            <button
              type="button"
              onClick={() => {
                setStructured(parseMarkdownToStructured(value));
                setMode("structured");
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                mode === "structured"
                  ? "bg-card text-text-primary shadow-xs border border-border/80"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              <Sliders className="w-3.5 h-3.5 text-primary" />
              Structured Builder
            </button>
            <button
              type="button"
              onClick={() => setMode("markdown")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                mode === "markdown"
                  ? "bg-card text-text-primary shadow-xs border border-border/80"
                  : "text-text-muted hover:text-text-primary"
              }`}
            >
              <FileCode className="w-3.5 h-3.5 text-primary" />
              Markdown Editor
            </button>
          </div>

          {/* Templates Library button */}
          <button
            type="button"
            onClick={() => setShowTemplatesModal(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-secondary hover:bg-secondary/80 text-text-secondary hover:text-text-primary border border-border transition-colors"
            title="Load ready-made structured templates"
          >
            <BookOpen className="w-3.5 h-3.5 text-primary" />
            <span className="hidden sm:inline">Templates</span>
          </button>

          {/* Review Tips button */}
          {onReviewAgent && (
            <button
              type="button"
              onClick={onReviewAgent}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/20 transition-all shadow-xs"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Review</span>
            </button>
          )}

          {/* Genie Optimizer */}
          {onImproveWithGenie && (
            <button
              type="button"
              onClick={onImproveWithGenie}
              disabled={genieLoading}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-600 hover:bg-amber-500/20 border border-amber-500/30 transition-colors shadow-xs"
              title="Optimize with Genie LLM"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              {genieLoading ? "Optimizing..." : <span className="hidden sm:inline">Genie AI</span>}
            </button>
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* MODE 1: STRUCTURED PROMPT BUILDER                                   */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {mode === "structured" && (
        <div className="space-y-6">
          {/* Card 1: Role & Persona */}
          <div className="p-4 rounded-xl border border-border/80 bg-secondary/15 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-primary/15 text-primary font-bold text-xs flex items-center justify-center">
                  1
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Identity, Persona & Speaking Tone
                </h4>
              </div>
              <span className="text-[11px] text-text-muted">Injected as root LLM persona</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                  Advisor Role / Position
                </label>
                <input
                  type="text"
                  value={structured.role}
                  onChange={(e) =>
                    updateStructured((s) => ({ ...s, role: e.target.value }))
                  }
                  placeholder="e.g. Warm rooftop solar consultant at {partnerName}"
                  className="w-full px-3 py-2 rounded-lg text-xs bg-card border border-border focus:border-primary focus:outline-none text-text-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                  Speaking Tone & Attitude
                </label>
                <input
                  type="text"
                  value={structured.tone}
                  onChange={(e) =>
                    updateStructured((s) => ({ ...s, tone: e.target.value }))
                  }
                  placeholder="e.g. Warm, polite, consultative, 70% listening, concise"
                  className="w-full px-3 py-2 rounded-lg text-xs bg-card border border-border focus:border-primary focus:outline-none text-text-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                  Language & Native Script Rule
                </label>
                <input
                  type="text"
                  value={structured.languageAndScript}
                  onChange={(e) =>
                    updateStructured((s) => ({ ...s, languageAndScript: e.target.value }))
                  }
                  placeholder="e.g. Always speak natural Marathi in Devanagari script"
                  className="w-full px-3 py-2 rounded-lg text-xs bg-card border border-border focus:border-primary focus:outline-none text-text-primary"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-text-secondary mb-1">
                  AI Identity Disclosure (When asked &quot;Are you an AI?&quot;)
                </label>
                <input
                  type="text"
                  value={structured.aiDisclosure}
                  onChange={(e) =>
                    updateStructured((s) => ({ ...s, aiDisclosure: e.target.value }))
                  }
                  placeholder='e.g. "मी {partnerName} कडून एआय सोलर असिस्टंट आहे"'
                  className="w-full px-3 py-2 rounded-lg text-xs bg-card border border-border focus:border-primary focus:outline-none text-text-primary"
                />
              </div>
            </div>
          </div>

          {/* Card 2: Conversational Rules & Guardrails */}
          <div className="p-4 rounded-xl border border-border/80 bg-secondary/15 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-primary/15 text-primary font-bold text-xs flex items-center justify-center">
                  2
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Conversational Rules & Snappy Rhythm
                </h4>
              </div>
              <button
                type="button"
                onClick={() =>
                  updateStructured((s) => ({
                    ...s,
                    rules: [...s.rules, "New voice rule: Keep tone concise and natural."],
                  }))
                }
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
              >
                <Plus className="w-3.5 h-3.5" /> Add Rule
              </button>
            </div>

            <div className="space-y-2">
              {structured.rules.map((rule, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-card p-2 rounded-lg border border-border/70">
                  <span className="w-5 h-5 rounded-full bg-secondary text-[10px] font-bold text-text-muted flex items-center justify-center shrink-0">
                    {idx + 1}
                  </span>
                  <input
                    type="text"
                    value={rule}
                    onChange={(e) => {
                      const updated = [...structured.rules];
                      updated[idx] = e.target.value;
                      updateStructured((s) => ({ ...s, rules: updated }));
                    }}
                    className="flex-1 px-2 py-1 text-xs bg-transparent border-0 focus:outline-none text-text-primary font-medium"
                    placeholder="Conversational guideline..."
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const updated = structured.rules.filter((_, i) => i !== idx);
                      updateStructured((s) => ({ ...s, rules: updated }));
                    }}
                    className="text-text-muted hover:text-red-500 p-1 transition-colors"
                    title="Delete rule"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Conversation Flow & Stages */}
          <div className="p-4 rounded-xl border border-border/80 bg-secondary/15 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-primary/15 text-primary font-bold text-xs flex items-center justify-center">
                  3
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Conversation Stages & Flow
                </h4>
              </div>
              <button
                type="button"
                onClick={() =>
                  updateStructured((s) => ({
                    ...s,
                    phases: [
                      ...s.phases,
                      {
                        id: Math.random().toString(),
                        name: `Phase ${s.phases.length + 1}: Custom Stage`,
                        trigger: "When prospect confirms",
                        action: "What the agent should ask or communicate next.",
                      },
                    ],
                  }))
                }
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
              >
                <Plus className="w-3.5 h-3.5" /> Add Stage
              </button>
            </div>

            <div className="space-y-3">
              {structured.phases.map((phase, idx) => (
                <div
                  key={phase.id}
                  className="p-3.5 rounded-xl border border-border/80 bg-card shadow-xs space-y-2.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <input
                      type="text"
                      value={phase.name}
                      onChange={(e) => {
                        const updated = [...structured.phases];
                        updated[idx].name = e.target.value;
                        updateStructured((s) => ({ ...s, phases: updated }));
                      }}
                      className="font-bold text-xs text-text-primary bg-secondary/40 px-2.5 py-1 rounded-md border border-border/60 focus:border-primary focus:outline-none w-2/3"
                      placeholder="Stage Name (e.g. Phase 1: Frame Call)"
                    />
                    <div className="flex items-center gap-1">
                      {idx > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            const updated = [...structured.phases];
                            const temp = updated[idx];
                            updated[idx] = updated[idx - 1];
                            updated[idx - 1] = temp;
                            updateStructured((s) => ({ ...s, phases: updated }));
                          }}
                          className="p-1 text-text-muted hover:text-text-primary"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>
                      )}
                      {idx < structured.phases.length - 1 && (
                        <button
                          type="button"
                          onClick={() => {
                            const updated = [...structured.phases];
                            const temp = updated[idx];
                            updated[idx] = updated[idx + 1];
                            updated[idx + 1] = temp;
                            updateStructured((s) => ({ ...s, phases: updated }));
                          }}
                          className="p-1 text-text-muted hover:text-text-primary"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          const updated = structured.phases.filter((_, i) => i !== idx);
                          updateStructured((s) => ({ ...s, phases: updated }));
                        }}
                        className="p-1 text-text-muted hover:text-red-500"
                        title="Delete phase"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
                      Agent Goal, Script & Next Question
                    </label>
                    <textarea
                      rows={2}
                      value={phase.action}
                      onChange={(e) => {
                        const updated = [...structured.phases];
                        updated[idx].action = e.target.value;
                        updateStructured((s) => ({ ...s, phases: updated }));
                      }}
                      className="w-full p-2.5 rounded-lg text-xs bg-secondary/20 border border-border focus:border-primary focus:outline-none text-text-primary resize-y"
                      placeholder="e.g. State value proposition and ask average monthly bill..."
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Card 4: Objection Handling & FAQs */}
          <div className="p-4 rounded-xl border border-border/80 bg-secondary/15 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-lg bg-primary/15 text-primary font-bold text-xs flex items-center justify-center">
                  4
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  Objection Handling & Common Hesitations
                </h4>
              </div>
              <button
                type="button"
                onClick={() =>
                  updateStructured((s) => ({
                    ...s,
                    objections: [
                      ...s.objections,
                      {
                        id: Math.random().toString(),
                        objection: "Call back later",
                        response: "Understood! When would be a convenient time for us to connect?",
                      },
                    ],
                  }))
                }
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
              >
                <Plus className="w-3.5 h-3.5" /> Add Objection
              </button>
            </div>

            <div className="space-y-3">
              {structured.objections.map((obj, idx) => (
                <div
                  key={obj.id}
                  className="p-3.5 rounded-xl border border-border/80 bg-card shadow-xs space-y-2"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="w-1/2">
                      <label className="block text-[10px] font-semibold text-text-muted mb-1">
                        When caller says / raises:
                      </label>
                      <input
                        type="text"
                        value={obj.objection}
                        onChange={(e) => {
                          const updated = [...structured.objections];
                          updated[idx].objection = e.target.value;
                          updateStructured((s) => ({ ...s, objections: updated }));
                        }}
                        className="w-full px-2.5 py-1.5 rounded-lg text-xs bg-secondary/40 border border-border/70 focus:border-primary focus:outline-none text-text-primary font-medium"
                        placeholder="e.g. Too expensive / Not interested"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        const updated = structured.objections.filter((_, i) => i !== idx);
                        updateStructured((s) => ({ ...s, objections: updated }));
                      }}
                      className="p-1 text-text-muted hover:text-red-500 mt-4"
                      title="Delete objection"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div>
                    <label className="block text-[10px] font-semibold text-text-muted mb-1">
                      Agent Empathetic Response:
                    </label>
                    <textarea
                      rows={2}
                      value={obj.response}
                      onChange={(e) => {
                        const updated = [...structured.objections];
                        updated[idx].response = e.target.value;
                        updateStructured((s) => ({ ...s, objections: updated }));
                      }}
                      className="w-full p-2.5 rounded-lg text-xs bg-secondary/20 border border-border focus:border-primary focus:outline-none text-text-primary resize-y"
                      placeholder="e.g. Acknowledge with warmth, then offer low-pressure solution..."
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* MODE 2: MARKDOWN-FORMATTED AGENT INSTRUCTIONS                      */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {mode === "markdown" && (
        <div className="space-y-3">
          {/* Markdown Formatting Toolbar */}
          <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-secondary/30 border border-border flex-wrap">
            {/* Left formatting buttons */}
            <div className="flex items-center gap-1 flex-wrap">
              {/* Headings */}
              <button
                type="button"
                onClick={() => insertPrefix("# ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary text-xs font-bold"
                title="Heading 1 (#)"
              >
                <Heading1 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => insertPrefix("## ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary text-xs font-bold"
                title="Heading 2 (##)"
              >
                <Heading2 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => insertPrefix("### ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary text-xs font-bold"
                title="Heading 3 (###)"
              >
                <Heading3 className="w-3.5 h-3.5" />
              </button>

              <div className="w-px h-4 bg-border mx-1" />

              {/* Bold, Italic, Strikethrough, Code */}
              <button
                type="button"
                onClick={() => wrapSelection("**", "**", "bold text")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Bold (**text**)"
              >
                <Bold className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => wrapSelection("*", "*", "italic text")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Italic (*text*)"
              >
                <Italic className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => wrapSelection("~~", "~~", "strikethrough text")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Strikethrough"
              >
                <Strikethrough className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => wrapSelection("`", "`", "code")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Inline Code"
              >
                <Code className="w-3.5 h-3.5" />
              </button>

              <div className="w-px h-4 bg-border mx-1" />

              {/* Lists & Quotes */}
              <button
                type="button"
                onClick={() => insertPrefix("- ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Bullet List (- )"
              >
                <List className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => insertPrefix("1. ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Numbered List (1. )"
              >
                <ListOrdered className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => insertPrefix("> ")}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Quote (> )"
              >
                <Quote className="w-3.5 h-3.5" />
              </button>

              <div className="w-px h-4 bg-border mx-1" />

              {/* Dynamic Variables dropdown */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowVariablesDropdown(!showVariablesDropdown)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-medium bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20"
                  title="Insert dynamic input variable"
                >
                  &#123; Variable &#125; <ChevronDown className="w-3 h-3" />
                </button>
                {showVariablesDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-card border border-border rounded-xl shadow-lg p-1.5 z-30 space-y-0.5">
                    <span className="block px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted">
                      Available Variables
                    </span>
                    {Object.keys(availableVariables).length === 0 ? (
                      <span className="block px-2 py-1.5 text-xs text-text-muted italic">
                        No variables defined
                      </span>
                    ) : (
                      Object.keys(availableVariables).map((v) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => insertVariable(v)}
                          className="w-full text-left px-2 py-1.5 rounded-lg text-xs font-mono text-text-primary hover:bg-secondary flex items-center justify-between"
                        >
                          <span>&#123;{v}&#125;</span>
                          <span className="text-[10px] text-primary font-sans">insert</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Ready-made Section Snippets */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowSnippetsDropdown(!showSnippetsDropdown)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-secondary text-text-secondary hover:text-text-primary border border-border"
                  title="Insert prompt section snippet"
                >
                  <Layers className="w-3 h-3 text-primary" />
                  + Section <ChevronDown className="w-3 h-3" />
                </button>
                {showSnippetsDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-56 bg-card border border-border rounded-xl shadow-lg p-1.5 z-30 space-y-0.5">
                    <button
                      type="button"
                      onClick={() =>
                        insertSnippet(
                          `## 🎭 Role & Persona\n- **Agent Name**: {salesRepName}\n- **Role**: Advisor at {partnerName}\n- **Tone**: Warm, helpful, concise\n`
                        )
                      }
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-text-primary hover:bg-secondary"
                    >
                      🎭 Role & Persona
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        insertSnippet(
                          `## 🛡️ Conversational Rules\n1. Under 25 words per turn.\n2. Strictly one question at a time.\n3. Never re-greet mid call.\n`
                        )
                      }
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-text-primary hover:bg-secondary"
                    >
                      🛡️ Conversational Rules
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        insertSnippet(
                          `## 🚦 Conversation Flow\n- **Phase 1 (Framing)**: State value proposition and ask qualification question.\n- **Phase 2 (Action)**: Propose appointment or WhatsApp information dispatch.\n`
                        )
                      }
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-text-primary hover:bg-secondary"
                    >
                      🚦 Conversation Flow
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        insertSnippet(
                          `## 💡 Objection Handling\n- **Busy right now**: "No problem! When may I call you back, or can I send details on WhatsApp?"\n`
                        )
                      }
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-text-primary hover:bg-secondary"
                    >
                      💡 Objection Handling
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Right: View Switcher (Write / Split / Preview) & Copy */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleCopyMarkdown}
                className="p-1.5 rounded hover:bg-card text-text-secondary hover:text-text-primary"
                title="Copy Markdown"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>

              <div className="inline-flex p-0.5 bg-secondary rounded-lg border border-border">
                <button
                  type="button"
                  onClick={() => setView("write")}
                  className={`p-1.5 rounded-md text-xs transition-all ${
                    view === "write"
                      ? "bg-card text-text-primary shadow-xs"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                  title="Write Mode (Raw Markdown)"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setView("split")}
                  className={`p-1.5 rounded-md text-xs transition-all ${
                    view === "split"
                      ? "bg-card text-text-primary shadow-xs"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                  title="Split View (Side-by-side)"
                >
                  <Columns className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setView("preview")}
                  className={`p-1.5 rounded-md text-xs transition-all ${
                    view === "preview"
                      ? "bg-card text-text-primary shadow-xs"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                  title="Preview Mode"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Editor Canvas */}
          <div
            className={`grid gap-4 ${
              view === "split"
                ? "grid-cols-1 lg:grid-cols-2"
                : "grid-cols-1"
            }`}
          >
            {/* Left: Raw Markdown Editor */}
            {(view === "write" || view === "split") && (
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  rows={20}
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  className="w-full p-4 rounded-xl text-xs leading-relaxed bg-secondary/20 border border-border focus:border-primary focus:outline-none text-text-primary resize-y font-mono"
                  placeholder="# Role & Persona&#10;- Agent Name: {salesRepName}&#10;&#10;## Conversational Rules&#10;1. Under 25 words per turn...&#10;&#10;## Conversation Flow..."
                />
              </div>
            )}

            {/* Right: Live Markdown Preview */}
            {(view === "preview" || view === "split") && (
              <div className="p-5 rounded-xl border border-border bg-card/60 overflow-y-auto max-h-[500px]">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/50">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                    Live Formatted Preview
                  </span>
                  <span className="text-[10px] text-text-muted">
                    Variables appear as <span className="text-primary font-mono font-semibold">&#123;chips&#125;</span>
                  </span>
                </div>

                <div
                  className="prose prose-sm max-w-none text-xs text-text-primary leading-relaxed space-y-3
                    [&>h1]:text-sm [&>h1]:font-bold [&>h1]:text-text-primary [&>h1]:border-b [&>h1]:border-border/60 [&>h1]:pb-1.5 [&>h1]:mt-4 [&>h1]:first:mt-0
                    [&>h2]:text-xs [&>h2]:font-bold [&>h2]:text-text-primary [&>h2]:mt-4 [&>h2]:mb-2 [&>h2]:uppercase [&>h2]:tracking-wider [&>h2]:text-primary
                    [&>h3]:text-xs [&>h3]:font-bold [&>h3]:text-text-primary [&>h3]:mt-3
                    [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:space-y-1.5
                    [&>ol]:list-decimal [&>ol]:pl-5 [&>ol]:space-y-1.5
                    [&>blockquote]:border-l-2 [&>blockquote]:border-primary/50 [&>blockquote]:bg-primary/5 [&>blockquote]:p-2.5 [&>blockquote]:rounded-r-lg [&>blockquote]:italic
                    [&>p]:leading-relaxed
                    [&>hr]:border-border/60 [&>hr]:my-4"
                  dangerouslySetInnerHTML={{ __html: renderedHtml }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Telemetry & Prompt Diagnostics Bar ── */}
      <div className="flex items-center justify-between pt-2 border-t border-border/50 text-[11px] text-text-muted">
        <div className="flex items-center gap-4">
          <span>
            Words: <strong className="text-text-primary font-mono">{wordCount}</strong>
          </span>
          <span>
            Characters: <strong className="text-text-primary font-mono">{charCount}</strong>
          </span>
          <span>
            Est. LLM Tokens:{" "}
            <strong className="text-text-primary font-mono">{tokenEstimate}</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Prompt ready for voice runtime
          </span>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────────── */}
      {/* TEMPLATE PICKER MODAL                                               */}
      {/* ─────────────────────────────────────────────────────────────────── */}
      {showTemplatesModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-primary" />
                  Structured Agent Instructions Library
                </h3>
                <p className="text-xs text-text-muted mt-0.5">
                  Select an industry-optimized structured prompt template.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowTemplatesModal(false)}
                className="text-text-muted hover:text-text-primary text-sm p-1"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto space-y-3 pr-1 divide-y divide-border/40">
              {Object.entries(TEMPLATES).map(([key, tpl]) => (
                <div key={key} className="pt-3 first:pt-0 flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-text-primary">{tpl.label}</h4>
                    <p className="text-xs text-text-muted leading-relaxed">{tpl.description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleLoadTemplate(key)}
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xs"
                  >
                    Load Template
                  </button>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-border/60 flex justify-end">
              <button
                type="button"
                onClick={() => setShowTemplatesModal(false)}
                className="px-4 py-1.5 rounded-lg text-xs font-medium bg-secondary text-text-secondary hover:text-text-primary border border-border"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
