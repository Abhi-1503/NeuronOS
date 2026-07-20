"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/shared/shell";
import { getStoredAuth, type AuthResult } from "@/lib/auth";

const ONBOARDING_PATHS = [
  {
    key: "integration" as const,
    title: "Connect an integration",
    description:
      "Connect Gmail (or another supported provider) and NeuronOS syncs recent email only — not your full mailbox history — to get to a first insight in minutes.",
    availability: "Available once Integrations ship (Phase 2)",
  },
  {
    key: "documents" as const,
    title: "Upload your key documents",
    description:
      "Upload 3–5 documents — a customer list, a contract, a proposal. One document is enough to generate a real AI summary.",
    availability: "Available once Knowledge ships (Phase 1)",
  },
  {
    key: "manual_customers" as const,
    title: "Add your top customers",
    description:
      "Add name + last contact date for your 5 most important customers — no processing wait at all.",
    availability: "Available once Customers ships (Phase 1)",
  },
];

/**
 * Pulse's first-run state (Blueprint §4.4, Onboarding Spec §3.1): a brand-new
 * organization sees this path selector directly as Pulse's actual content — not a blank
 * or meaningless Business Health score, and not a separate wizard bolted in front of
 * "the real product." Each path's backend (POST /customers, POST /documents, the
 * integration OAuth flow) is Phase 1/2 scope per the Roadmap, so the cards are real and
 * fully designed but their actions are inert until that module ships — this is the
 * honest Phase 0 state, not a functional onboarding flow yet.
 */
export default function PulsePage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  if (!auth) return null;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name}>
      <div className="mx-auto max-w-2xl">
        <h1 className="text-[22px] font-bold tracking-tight">How do you want to get started?</h1>
        <p className="mt-2 text-[13.5px]" style={{ color: "var(--neuron-text-dim)" }}>
          Pick one — you can add the others later. NeuronOS surfaces one real, specific insight
          from whatever you provide, usually within minutes.
        </p>

        <div className="mt-6 flex flex-col gap-3">
          {ONBOARDING_PATHS.map((path) => (
            <div
              key={path.key}
              className="rounded-2xl p-5"
              style={{
                background: "var(--neuron-card)",
                border: "1px solid var(--neuron-border)",
                boxShadow: "var(--neuron-shadow)",
              }}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-[14px] font-bold">{path.title}</h2>
                  <p className="mt-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
                    {path.description}
                  </p>
                </div>
                <button
                  disabled
                  className="shrink-0 rounded-lg px-3 py-1.5 text-[12.5px] font-semibold"
                  style={{
                    background: "var(--neuron-border)",
                    color: "var(--neuron-text-faint)",
                    cursor: "not-allowed",
                  }}
                >
                  Start
                </button>
              </div>
              <div className="mt-3 text-[11px] font-medium" style={{ color: "var(--neuron-text-faint)" }}>
                {path.availability}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
