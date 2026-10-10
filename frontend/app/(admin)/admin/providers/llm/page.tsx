"use client";

import React from "react";
import { ProviderConfigPanel } from "@/components/model-directory/ProviderConfigPanel";

export default function AdminProvidersLLMPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary">
          LLM Provider Configuration
        </h2>
        <p className="text-sm text-text-secondary mt-0.5">
          Configure the large language model provider for the call pipeline.
        </p>
      </div>

      <ProviderConfigPanel capability="llm" />
    </div>
  );
}
