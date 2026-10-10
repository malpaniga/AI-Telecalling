"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { api, BusinessTemplate, VoiceProfile } from "@/lib/api";

const TONE_OPTIONS = [
  { value: "warm_professional", label: "Warm Professional" },
  { value: "formal", label: "Formal" },
  { value: "casual", label: "Casual" },
  { value: "energetic", label: "Energetic" },
];

const LANGUAGE_OPTIONS = [
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi" },
  { value: "mr-IN", label: "Marathi" },
  { value: "gu-IN", label: "Gujarati" },
  { value: "ta-IN", label: "Tamil" },
  { value: "te-IN", label: "Telugu" },
  { value: "kn-IN", label: "Kannada" },
  { value: "ml-IN", label: "Malayalam" },
];

type Step = 1 | 2 | 3;

export default function NewAgentPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [submitting, setSubmitting] = useState(false);

  // Data
  const [templates, setTemplates] = useState<BusinessTemplate[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // Step 1 fields
  const [name, setName] = useState("");
  const [templateSlug, setTemplateSlug] = useState("");
  const [description, setDescription] = useState("");

  // Step 2 fields
  const [voiceProfileId, setVoiceProfileId] = useState("");
  const [voiceProfileVersion, setVoiceProfileVersion] = useState(1);

  // Step 3 fields
  const [goal, setGoal] = useState("");
  const [tone, setTone] = useState("warm_professional");
  const [greeting, setGreeting] = useState("");
  const [language, setLanguage] = useState("en-IN");

  useEffect(() => {
    Promise.all([api.agents.templates(), api.voiceProfiles.list()])
      .then(([t, vp]) => {
        setTemplates(t);
        setVoiceProfiles(vp);
        if (t.length > 0) setTemplateSlug(t[0].slug);
        if (vp.length > 0) {
          setVoiceProfileId(vp[0].id);
          setVoiceProfileVersion(vp[0].active_version ?? 1);
        }
      })
      .catch((e: unknown) =>
        toast.error(e instanceof Error ? e.message : "Failed to load options")
      )
      .finally(() => setLoadingData(false));
  }, []);

  async function handleSubmit() {
    if (!name.trim()) {
      toast.error("Agent name is required");
      return;
    }
    if (!voiceProfileId) {
      toast.error("Select a voice profile");
      return;
    }
    setSubmitting(true);
    try {
      const agent = await api.agents.create({
        name,
        template_slug: templateSlug,
        voice_profile_id: voiceProfileId,
        voice_profile_version: voiceProfileVersion,
        description,
      });
      const configuration: Record<string, unknown> = {
        goal: goal || undefined,
        tone,
        greeting: greeting || undefined,
        primary_language: language,
      };
      await api.agents.versions.create(agent.id, {
        configuration,
        description: "Initial version",
        auto_activate: true,
      });
      toast.success("Agent created");
      router.push(`/agents/${agent.id}`);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to create agent");
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingData) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  const STEPS = [
    { n: 1, label: "Basic Info" },
    { n: 2, label: "Voice Profile" },
    { n: 3, label: "Configuration" },
  ] as const;

  return (
    <div className="max-w-xl space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-3">
        <Link href="/agents">
          <Button variant="ghost" size="sm" className="gap-1">
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <h2 className="text-lg font-semibold text-text-primary">New Agent</h2>
      </div>

      {/* Step indicators */}
      <div className="flex gap-3">
        {STEPS.map(({ n, label }) => (
          <div
            key={n}
            className={`flex items-center gap-2 text-sm ${
              step === n
                ? "text-accent font-semibold"
                : step > n
                ? "text-text-secondary"
                : "text-text-muted"
            }`}
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                step === n
                  ? "bg-accent text-white"
                  : step > n
                  ? "bg-surface-subtle text-text-secondary"
                  : "bg-surface-subtle text-text-muted"
              }`}
            >
              {n}
            </span>
            {label}
          </div>
        ))}
      </div>

      {/* Step 1 */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Basic Information
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="Agent Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Priya Sales Agent"
              required
            />
            <Select
              label="Business Template"
              value={templateSlug}
              onChange={(e) => setTemplateSlug(e.target.value)}
              options={templates.map((t) => ({
                value: t.slug,
                label: t.name,
              }))}
            />
            <Input
              label="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of what this agent does"
            />
            <div className="flex justify-end pt-2">
              <Button
                onClick={() => {
                  if (!name.trim()) {
                    toast.error("Enter an agent name");
                    return;
                  }
                  setStep(2);
                }}
              >
                Continue
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Step 2 */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Voice Profile
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            {voiceProfiles.length === 0 ? (
              <p className="text-sm text-text-muted">
                No voice profiles available. Ask your platform admin to create
                one.
              </p>
            ) : (
              <>
                <Select
                  label="Voice Profile"
                  value={voiceProfileId}
                  onChange={(e) => {
                    const vp = voiceProfiles.find(
                      (v) => v.id === e.target.value
                    );
                    setVoiceProfileId(e.target.value);
                    setVoiceProfileVersion(vp?.active_version ?? 1);
                  }}
                  options={voiceProfiles.map((vp) => ({
                    value: vp.id,
                    label: `${vp.display_name} (${vp.language})`,
                  }))}
                />
                {voiceProfileId && (
                  <p className="text-xs text-text-muted">
                    Using active version{" "}
                    {voiceProfiles.find((v) => v.id === voiceProfileId)
                      ?.active_version ?? "—"}
                  </p>
                )}
              </>
            )}
            <div className="flex justify-between pt-2">
              <Button variant="secondary" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button onClick={() => setStep(3)}>Continue</Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Step 3 */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-text-primary">
              Configuration
            </h3>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="Goal (optional)"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. Qualify leads for home loans"
            />
            <Select
              label="Tone"
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              options={TONE_OPTIONS}
            />
            <Select
              label="Primary Language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              options={LANGUAGE_OPTIONS}
            />
            <Input
              label="Greeting (optional)"
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              placeholder="Hello! I'm calling from..."
            />
            <div className="flex justify-between pt-2">
              <Button variant="secondary" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button loading={submitting} onClick={handleSubmit}>
                Create Agent
              </Button>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
