"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatedBackground } from "@/components/shared/animated-background";
import {
  AIActionsIcon,
  AIWorkspaceIcon,
  AutomationsIcon,
  CustomersIcon,
  KnowledgeIcon,
  PulseIcon,
  ReportsIcon,
  SettingsIcon,
  ShieldIcon,
} from "@/components/shared/nav-icons";
import { NeuronMarkBadge } from "@/components/shared/neuron-mark";
import { TiltCard } from "@/components/shared/tilt-card";
import { getStoredAuth } from "@/lib/auth";

type Category = "All" | "Intelligence" | "Automation" | "Trust";

const SOLUTIONS: {
  icon: typeof PulseIcon;
  category: Category;
  title: string;
  tag: string;
  description: string;
  points: string[];
}[] = [
  {
    icon: PulseIcon,
    category: "Intelligence",
    title: "Pulse",
    tag: "Daily briefing",
    description: "A single-glance view of the business — health, priorities, and the one insight that matters most today.",
    points: ["Business health score & trend", "Today's Focus ranked by urgency", "Quick-ask AI question box"],
  },
  {
    icon: CustomersIcon,
    category: "Intelligence",
    title: "Customers",
    tag: "Relationship intelligence",
    description: "Every relationship scored and ranked, so you always know who needs attention — and exactly why.",
    points: ["Rule-based relationship scoring", "Deal & revenue tracking", "Full timeline of every interaction"],
  },
  {
    icon: KnowledgeIcon,
    category: "Intelligence",
    title: "Knowledge",
    tag: "Document intelligence",
    description: "Upload contracts and proposals — NeuronOS reads, summarizes, and connects them to the right customer.",
    points: ["Auto-summarize contracts & proposals", "Keyword search across every document", "Auto-linked to the customer it mentions"],
  },
  {
    icon: ReportsIcon,
    category: "Intelligence",
    title: "Reports",
    tag: "Real analytics",
    description: "Revenue trends, pipeline health, and top performers — real numbers pulled from your own data.",
    points: ["Revenue trend & by-source breakdown", "Top customer performance", "Real numbers, not vanity metrics"],
  },
  {
    icon: AIActionsIcon,
    category: "Automation",
    title: "AI Actions",
    tag: "Approve-first automation",
    description: "Every suggestion shows its reasoning and confidence up front. You approve — nothing sends itself.",
    points: ["Reasoning & confidence shown inline", "Severity-gated confirmation on risk", "One click to approve or reject"],
  },
  {
    icon: AutomationsIcon,
    category: "Automation",
    title: "Automations",
    tag: "Trust-graduated workflows",
    description: "Repetitive follow-ups earn trust in stages — dry run, then supervised, then live. Never a surprise.",
    points: ["Dry run → Graduating → Live stages", "Real run history & success rate", "A rejection resets trust to zero"],
  },
  {
    icon: AIWorkspaceIcon,
    category: "Automation",
    title: "AI Workspace",
    tag: "Conversational Q&A",
    description: "Ask anything about your business in plain language — answers cite exactly what they're based on.",
    points: ["Ask anything, plain language", "Citations to real documents & customers", "Full conversation history kept"],
  },
  {
    icon: SettingsIcon,
    category: "Trust",
    title: "Team & Access",
    tag: "Governance",
    description: "Role-based access for your whole team, with account controls that respect you, not trap you.",
    points: ["Owner / Admin / Member roles", "Org profile & preferences", "Real two-step account deletion"],
  },
  {
    icon: ShieldIcon,
    category: "Trust",
    title: "Security & Architecture",
    tag: "Foundation",
    description: "The properties every other module inherits — enforced at the database layer, not just the UI.",
    points: ["Row-level data isolation per org", "Approve-first enforced server-side", "Honest AI degradation, never fake data"],
  },
];

const CATEGORIES: Category[] = ["All", "Intelligence", "Automation", "Trust"];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <NeuronMarkBadge size={32} />
      <span className="text-[17px] font-bold tracking-tight" style={{ fontFamily: "var(--font-heading)" }}>
        NeuronOS
      </span>
    </Link>
  );
}

export default function SolutionsPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [category, setCategory] = useState<Category>("All");

  useEffect(() => {
    if (getStoredAuth()) {
      router.replace("/pulse");
      return;
    }
    setChecked(true);
  }, [router]);

  if (!checked) return null;

  const visible = category === "All" ? SOLUTIONS : SOLUTIONS.filter((s) => s.category === category);

  return (
    <div style={{ background: "#fff", color: "var(--neuron-text)" }}>
      {/* Nav */}
      <motion.div
        className="sticky top-4 z-10 mx-auto max-w-5xl px-6"
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <header
          className="flex items-center justify-between rounded-2xl px-5 py-3 backdrop-blur"
          style={{ background: "rgba(255,255,255,0.85)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
        >
          <Logo />
          <nav className="flex items-center gap-6">
            <Link href="/#" className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              Product
            </Link>
            <span className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-primary)" }}>
              Solutions
            </span>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              Log in
            </Link>
            <Link
              href="/signup"
              className="neuron-press rounded-lg px-4 py-2 text-[13.5px] font-bold text-white"
              style={{ background: "var(--neuron-primary)" }}
            >
              Get Started
            </Link>
          </div>
        </header>
      </motion.div>

      {/* Hero */}
      <section className="relative overflow-hidden px-6 pt-20 pb-14 text-center">
        <AnimatedBackground />
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative text-[12px] font-bold tracking-[0.2em] uppercase"
          style={{ color: "var(--neuron-primary)" }}
        >
          Solutions
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative mx-auto mt-4 max-w-2xl text-[46px] leading-[1.15] font-bold tracking-tight"
        >
          One system,{" "}
          <span
            className="neuron-gradient-text italic"
            style={{
              background: "linear-gradient(135deg,#8B7CF6,#2E7DD1,#8B7CF6)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            every outcome.
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="relative mx-auto mt-5 max-w-lg text-[16px] leading-relaxed"
          style={{ color: "var(--neuron-text-dim)" }}
        >
          From the first customer you add to the report you send at month end — see how every
          NeuronOS module fits together, reasoning shown at every step.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="relative mt-8 flex items-center justify-center gap-2"
        >
          {CATEGORIES.map((c) => {
            const isActive = category === c;
            return (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className="relative rounded-full px-4 py-2 text-[13px] font-semibold"
                style={{ color: isActive ? "#fff" : "var(--neuron-text-dim)" }}
              >
                {isActive && (
                  <motion.div
                    layoutId="solutions-category-pill"
                    className="absolute inset-0 rounded-full"
                    style={{ background: "var(--neuron-primary)" }}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
                <span className="relative">{c}</span>
              </button>
            );
          })}
        </motion.div>
      </section>

      {/* Solutions grid */}
      <section className="mx-auto max-w-5xl px-6 pb-20">
        <motion.div layout className="grid grid-cols-3 gap-5">
          {visible.map((s, i) => (
            <motion.div
              key={s.title}
              layout
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, delay: i * 0.05 }}
            >
              <TiltCard
                className="relative flex h-full flex-col overflow-hidden rounded-2xl p-6"
                style={{ background: "#fff", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
              >
                <div
                  className="relative flex h-11 w-11 items-center justify-center rounded-xl"
                  style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
                >
                  <s.icon size={21} />
                </div>
                <div
                  className="relative mt-4 text-[10.5px] font-bold tracking-wide uppercase"
                  style={{ color: "var(--neuron-text-faint)" }}
                >
                  {s.tag}
                </div>
                <h3 className="relative mt-1 text-[17px] font-bold">{s.title}</h3>
                <p className="relative mt-2 text-[13px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
                  {s.description}
                </p>
                <div className="relative mt-4 flex flex-col gap-2">
                  {s.points.map((point) => (
                    <div key={point} className="flex items-center gap-2 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
                      <span
                        className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full"
                        style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
                      >
                        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                          <path d="M20 6 9 17l-5-5" />
                        </svg>
                      </span>
                      {point}
                    </div>
                  ))}
                </div>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* CTA band */}
      <section className="px-6 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 rounded-2xl px-10 py-10 text-center md:flex-row md:text-left"
          style={{ background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
        >
          <div>
            <h2 className="text-[24px] font-bold text-white">Every module, one approve-first system.</h2>
            <p className="mt-1 text-[13.5px] text-white/80">No credit card required — live in minutes.</p>
          </div>
          <Link
            href="/signup"
            className="neuron-press shrink-0 rounded-lg px-6 py-3 text-[14px] font-bold whitespace-nowrap"
            style={{ background: "#fff", color: "var(--neuron-primary-dark)" }}
          >
            Get Started Free
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t px-6 py-10" style={{ borderColor: "var(--neuron-border)" }}>
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
          <Logo />
          <p className="text-[12.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            © {new Date().getFullYear()} NeuronOS. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
