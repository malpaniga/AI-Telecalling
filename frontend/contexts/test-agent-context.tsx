"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export interface TestAgentOptions {
  language?: string;
  agentName?: string;
  greeting?: string;
  systemPrompt?: string;
  scenarioId?: string;
}

interface TestAgentContextValue {
  isOpen: boolean;
  openTestAgent: (options?: TestAgentOptions) => void;
  closeTestAgent: () => void;
  options: TestAgentOptions | null;
}

const TestAgentContext = createContext<TestAgentContextValue | null>(null);

export function TestAgentProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<TestAgentOptions | null>(null);

  const openTestAgent = useCallback((opts?: TestAgentOptions) => {
    if (opts) {
      setOptions(opts);
    }
    setIsOpen(true);
  }, []);

  const closeTestAgent = useCallback(() => {
    setIsOpen(false);
  }, []);

  return (
    <TestAgentContext.Provider
      value={{
        isOpen,
        openTestAgent,
        closeTestAgent,
        options,
      }}
    >
      {children}
    </TestAgentContext.Provider>
  );
}

export function useTestAgent() {
  const ctx = useContext(TestAgentContext);
  if (!ctx) {
    // Return a safe fallback if used outside provider
    return {
      isOpen: false,
      openTestAgent: () => {},
      closeTestAgent: () => {},
      options: null,
    };
  }
  return ctx;
}
