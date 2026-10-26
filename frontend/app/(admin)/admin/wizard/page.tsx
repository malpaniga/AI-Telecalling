"use client";

import React from "react";
import { ModelSetupWizard } from "@/components/model-directory/ModelSetupWizard";

export default function AdminWizardPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <ModelSetupWizard />
    </div>
  );
}
