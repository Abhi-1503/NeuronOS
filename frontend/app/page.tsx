"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
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
} from "@/components/shared/nav-icons";
import { NeuronMark, NeuronMarkBadge } from "@/components/shared/neuron-mark";
import { getStoredAuth } from "@/lib/auth";

const ROTATING_WORDS = ["Every Business", "Your Customers", "Your Team", "Your Pipeline"];

const INTEGRATIONS = ["Gmail", "Google Calendar", "Slack", "WhatsApp", "HubSpot", "QuickBooks"];

const FEATURES = [
  {
    icon: PulseIcon,
    title: "Pulse",
    description: "A single-glance daily briefing — business health, today's priorities, and the one insight that matters most.",
  },
  {
    icon: CustomersIcon,
    title: "Customers",
    description: "Every relationship scored and ranked, so you always know who needs attention and why.",
  },
  {
    icon: KnowledgeIcon,
    title: "Knowledge",
    description: "Upload contracts and proposals — NeuronOS reads, summarizes, and connects them to the right customer automatically.",
  },
  {
    icon: AIActionsIcon,
    title: "AI Actions",
    description: "Every suggestion shows its reasoning and confidence up front. You approve — nothing sends itself, ever.",
  },
  {
    icon: AutomationsIcon,
    title: "Automations",
    description: "Repetitive follow-ups earn trust in stages — dry run, then supervised, then live. Never a surprise.",
  },
  {
    icon: ReportsIcon,
    title: "Reports",
    description: "Revenue trends, pipeline health, and team performance — real numbers, not vanity dashboards.",
  },
  {
    icon: AIWorkspaceIcon,
    title: "AI Workspace",
    description: "Ask anything about your business in plain language — answers cite the document or customer they're based on.",
  },
  {
    icon: SettingsIcon,
    title: "Settings & Team",
    description: "Role-based access, org profile, and a real two-step account deletion flow — no dark patterns.",
  },
];

const VALUE_PILLARS = [
  {
    title: "Reasoning shown, not hidden",
    description: "Every AI conclusion comes with its confidence score and the specific evidence behind it — visible inline, never behind a \"why?\" click.",
  },
  {
    title: "Nothing sends without you",
    description: "Suggested actions wait for your approval. High-severity or irreversible actions require an explicit, hard-to-misclick confirmation.",
  },
  {
    title: "Automations earn trust in stages",
    description: "Every automation starts in dry run, graduates to supervised, and only runs unsupervised after a track record — earned, not assumed.",
  },
  {
    title: "One system, not ten tabs",
    description: "Customers, documents, automations, and reports all read from the same underlying data — no re-entering the same facts twice.",
  },
];

const TRUST_CARDS = [
  { title: "Approve-First by Design", description: "No AI action executes without your explicit approval — it's enforced server-side, not just a UI convention." },
  { title: "Severity-Gated Confirmation", description: "Irreversible or financial actions require a distinct, deliberate confirmation step — not the same click as a routine task." },
  { title: "Row-Level Data Isolation", description: "Every request is scoped by database-level row security, not application code alone — one tenant's data cannot leak into another's." },
  { title: "Honest AI Degradation", description: "No configured AI key means real extracted data with clear labeling — never a fabricated response dressed up as an answer." },
];

const STEPS = [
  { step: "01", title: "Add your data", description: "Add your top customers or upload a few key documents — no integration required to start." },
  { step: "02", title: "Get your first insight", description: "NeuronOS surfaces one real, specific finding from what you provided, usually within minutes." },
  { step: "03", title: "Approve what matters", description: "Review AI-suggested actions with full reasoning shown, and approve only what you want to happen." },
];

const FAQS = [
  {
    q: "Does AI ever act without my approval?",
    a: "No. Every AI-suggested action — sending an email, generating an invoice, anything — waits for your explicit approval before it happens. Automations only run unsupervised after they've earned trust through a graduated dry-run process.",
  },
  {
    q: "Is my organization's data isolated from others?",
    a: "Yes. Every request is scoped by row-level security enforced at the database layer, not just application-level checks — one organization's data cannot be queried by another's session.",
  },
  {
    q: "What happens if I don't configure an AI API key?",
    a: "Every AI feature degrades honestly. Document summaries fall back to real extracted text, and the AI Workspace shows exactly what matched your question — never a fabricated response.",
  },
  {
    q: "Do I need to connect every tool to get value?",
    a: "No — adopt one module (like Customers) and expand later. The value compounds as NeuronOS connects more of your business together, but it's useful from day one with just one.",
  },
  {
    q: "Can I delete my account and data?",
    a: "Yes, anytime, from Settings — a real two-step confirmation flow, not a support ticket you have to wait on.",
  },
];

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <NeuronMarkBadge size={32} />
      <span className="text-[17px] font-bold tracking-tight" style={{ fontFamily: "var(--font-heading)" }}>
        NeuronOS
      </span>
    </div>
  );
}

function RotatingWord() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % ROTATING_WORDS.length), 2600);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="relative inline-grid">
      <AnimatePresence mode="wait">
        <motion.span
          key={ROTATING_WORDS[index]}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -14 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="neuron-gradient-text col-start-1 row-start-1 italic"
          style={{
            background: "linear-gradient(135deg,#8B7CF6,#2E7DD1,#8B7CF6)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          {ROTATING_WORDS[index]}
        </motion.span>
      </AnimatePresence>
      {/* Invisible longest-word placeholder reserves layout width so the crossfade never reflows the page. */}
      <span className="invisible col-start-1 row-start-1 italic">
        {ROTATING_WORDS.reduce((a, b) => (a.length > b.length ? a : b))}
      </span>
    </span>
  );
}

function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, ease: "easeOut", delay }}
    >
      {children}
    </motion.div>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="neuron-hover-lift rounded-xl p-5"
      style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
    >
      <button onClick={() => setOpen((v) => !v)} className="flex w-full items-center justify-between text-left">
        <span className="text-[14px] font-bold">{q}</span>
        <motion.span
          animate={{ rotate: open ? 45 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[14px] font-bold text-white"
          style={{ background: "var(--neuron-primary)" }}
        >
          +
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <p className="mt-3 text-[13px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
              {a}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const featuresRef = useRef<HTMLDivElement>(null);
  const howRef = useRef<HTMLDivElement>(null);
  const faqRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (getStoredAuth()) {
      router.replace("/pulse");
      return;
    }
    setChecked(true);
  }, [router]);

  if (!checked) return null;

  function scrollTo(ref: React.RefObject<HTMLDivElement | null>) {
    ref.current?.scrollIntoView({ behavior: "smooth" });
  }

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
            <button onClick={() => scrollTo(featuresRef)} className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              Product
            </button>
            <Link href="/solutions" className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              Solutions
            </Link>
            <button onClick={() => scrollTo(howRef)} className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              How it works
            </button>
            <button onClick={() => scrollTo(faqRef)} className="text-[13.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
              FAQ
            </button>
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
      <section className="relative overflow-hidden px-6 pt-20 pb-20 text-center">
        <AnimatedBackground />
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="relative mx-auto inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[12px] font-semibold"
          style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
        >
          🛡️ Approve-first AI — nothing acts without you
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative mx-auto mt-6 max-w-2xl text-[46px] leading-[1.15] font-bold tracking-tight"
        >
          The Intelligence Layer for <RotatingWord />
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="relative mx-auto mt-5 max-w-lg text-[16px] leading-relaxed"
          style={{ color: "var(--neuron-text-dim)" }}
        >
          Your AI Chief of Staff that understands your business and helps you win — reasoning
          shown, nothing automated without your say.
        </motion.p>
        <p className="relative mx-auto mt-2 max-w-lg text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
          Built for founders, agencies, and growing teams who need clarity, not more dashboards.
        </p>

        <div className="relative mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
          <span>✓ No credit card required</span>
          <span>✓ Approve-first, always</span>
          <span>✓ Delete your data anytime</span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="relative mt-8 flex items-center justify-center gap-3"
        >
          <Link
            href="/signup"
            className="neuron-press rounded-lg px-6 py-3 text-[14px] font-bold text-white shadow-lg"
            style={{ background: "var(--neuron-primary)", boxShadow: "0 8px 24px rgba(108,92,231,0.35)" }}
          >
            Get Started Free
          </Link>
          <button
            onClick={() => scrollTo(howRef)}
            className="neuron-press rounded-lg px-6 py-3 text-[14px] font-semibold"
            style={{ border: "1px solid var(--neuron-border)", background: "#fff" }}
          >
            See how it works
          </button>
        </motion.div>

        <div className="relative mt-14">
          <div className="text-[11px] font-bold tracking-wide uppercase" style={{ color: "var(--neuron-text-faint)" }}>
            Built to connect with the tools you already use
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5">
            {INTEGRATIONS.map((name, i) => (
              <motion.span
                key={name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.4 + i * 0.05 }}
                className="neuron-hover-lift rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold"
                style={{ background: "#fff", border: "1px solid var(--neuron-border)", color: "var(--neuron-text-dim)" }}
              >
                {name}
              </motion.span>
            ))}
          </div>
        </div>
      </section>

      {/* Value pillars (replaces fabricated customer testimonials — NeuronOS has none yet) */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <Reveal className="text-center text-[12px] font-bold tracking-wide uppercase" delay={0}>
          <span style={{ color: "var(--neuron-primary-dark)" }}>Why teams choose NeuronOS</span>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="mt-2 text-center text-[26px] font-bold tracking-tight">
            Trust is earned by what the system shows you
          </h2>
        </Reveal>
        <div className="mt-10 grid grid-cols-2 gap-5">
          {VALUE_PILLARS.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.08}>
              <div
                className="neuron-hover-lift h-full rounded-2xl p-5"
                style={{ background: "var(--neuron-bg)", border: "1px solid var(--neuron-border)" }}
              >
                <h3 className="text-[14.5px] font-bold">{p.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
                  {p.description}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Features */}
      <section ref={featuresRef} className="mx-auto max-w-5xl scroll-mt-24 px-6 py-20">
        <Reveal className="text-center text-[12px] font-bold tracking-wide uppercase">
          <span style={{ color: "var(--neuron-primary-dark)" }}>Built for real growth</span>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="mt-2 text-center text-[26px] font-bold tracking-tight">One system, every part of the business</h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="mx-auto mt-2 max-w-lg text-center text-[14px]" style={{ color: "var(--neuron-text-dim)" }}>
            Adopt one module or all of them — the value compounds as NeuronOS connects more of your
            business together.
          </p>
        </Reveal>
        <div className="mt-10 grid grid-cols-4 gap-5">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={(i % 4) * 0.06}>
              <div
                className="neuron-hover-lift group h-full rounded-2xl p-5"
                style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-110"
                  style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
                >
                  <f.icon size={19} />
                </div>
                <h3 className="mt-3 text-[14.5px] font-bold">{f.title}</h3>
                <p className="mt-1 text-[12.5px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
                  {f.description}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* See it in action */}
      <section ref={howRef} className="mx-auto max-w-5xl scroll-mt-24 px-6 py-20">
        <div className="grid grid-cols-2 items-center gap-12">
          <Reveal>
            <div>
              <div className="text-[12px] font-bold tracking-wide uppercase" style={{ color: "var(--neuron-primary-dark)" }}>
                See it in action
              </div>
              <h2 className="mt-3 text-[30px] leading-[1.15] font-bold tracking-tight">
                An insight surfaces. <span style={{ color: "var(--neuron-primary)" }}>NeuronOS shows its work.</span>
              </h2>
              <p className="mt-4 text-[14px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
                The moment a customer goes quiet or an invoice runs overdue, NeuronOS surfaces it —
                with the exact reasoning and confidence behind the call. You decide what happens
                next.
              </p>
              <div className="mt-5 flex flex-col gap-2 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
                <span>✓ Reasoning shown inline, never hidden</span>
                <span>✓ Confidence score on every suggestion</span>
                <span>✓ You approve — nothing sends itself</span>
              </div>
              <Link
                href="/signup"
                className="neuron-press mt-6 inline-block rounded-lg px-5 py-2.5 text-[13.5px] font-bold text-white"
                style={{ background: "var(--neuron-primary)" }}
              >
                Get Started Free →
              </Link>
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <motion.div
              whileHover={{ y: -4 }}
              transition={{ duration: 0.25 }}
              className="rounded-2xl p-5"
              style={{ background: "var(--neuron-bg)", border: "1px solid var(--neuron-border)" }}
            >
              <div className="rounded-xl p-4" style={{ background: "#fff", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}>
                <div className="flex items-center justify-between">
                  <div className="text-[11px] font-bold tracking-wide uppercase" style={{ color: "var(--neuron-text-faint)" }}>
                    NeuronOS Insight
                  </div>
                  <div
                    className="flex h-6 w-6 items-center justify-center rounded-full"
                    style={{ background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
                  >
                    <NeuronMark size={13} variant="mono" color="#fff" />
                  </div>
                </div>
                <p className="mt-3 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>You are about to lose</p>
                <div className="text-[24px] font-bold" style={{ color: "var(--neuron-red)" }}>₹3,20,000</div>
                <div className="mt-2 text-[10.5px] font-bold tracking-wide uppercase" style={{ color: "var(--neuron-text-faint)" }}>
                  Reason
                </div>
                <p className="mt-1 text-[13px] font-semibold">No follow-up with 3 important customers</p>
                <p className="mt-1 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>
                  Proposal sent 6 days ago, no reply logged since.
                </p>
                <div className="mt-3 flex gap-2">
                  <span className="rounded-lg px-3 py-1.5 text-[12px] font-semibold" style={{ background: "var(--neuron-border)", color: "var(--neuron-text-dim)" }}>
                    Ignore
                  </span>
                  <span className="rounded-lg px-3 py-1.5 text-[12px] font-bold text-white" style={{ background: "var(--neuron-primary)" }}>
                    Approve
                  </span>
                </div>
              </div>
            </motion.div>
          </Reveal>
        </div>
      </section>

      {/* Security band (dark) */}
      <section className="relative overflow-hidden px-6 py-20" style={{ background: "linear-gradient(160deg,#14151d,#1b1d3a)" }}>
        <AnimatedBackground dark />
        <div className="relative mx-auto max-w-5xl">
          <Reveal className="text-center text-[12px] font-bold tracking-wide uppercase">
            <span style={{ color: "#a396f8" }}>Trust &amp; architecture</span>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="mt-2 text-center text-[26px] font-bold text-white">
              Enterprise-grade <span className="italic" style={{ color: "#a396f8" }}>trust</span> by default
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mx-auto mt-2 max-w-lg text-center text-[14px] text-white/70">
              These are real architectural properties of the system, not marketing claims.
            </p>
          </Reveal>
          <div className="mt-10 grid grid-cols-4 gap-5">
            {TRUST_CARDS.map((c, i) => (
              <Reveal key={c.title} delay={i * 0.08}>
                <div
                  className="neuron-hover-lift h-full rounded-2xl p-5"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
                >
                  <h3 className="text-[14px] font-bold text-white">{c.title}</h3>
                  <p className="mt-1.5 text-[12.5px] leading-relaxed text-white/70">{c.description}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 3 steps */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <Reveal>
          <h2 className="text-center text-[26px] font-bold tracking-tight">
            3 easy steps. <span style={{ color: "var(--neuron-primary)" }}>Full clarity.</span>
          </h2>
        </Reveal>
        <div className="mt-10 grid grid-cols-3 gap-5">
          {STEPS.map((s, i) => (
            <Reveal key={s.step} delay={i * 0.1}>
              <div
                className="neuron-hover-lift relative h-full rounded-2xl p-6"
                style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
              >
                <span
                  className="inline-block rounded-full px-2.5 py-1 text-[10.5px] font-bold text-white"
                  style={{ background: "var(--neuron-primary)" }}
                >
                  STEP {s.step}
                </span>
                <h3 className="mt-4 text-[16px] font-bold">{s.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed" style={{ color: "var(--neuron-text-dim)" }}>
                  {s.description}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section ref={faqRef} className="mx-auto max-w-3xl scroll-mt-24 px-6 py-20">
        <Reveal className="text-center text-[12px] font-bold tracking-wide uppercase">
          <span style={{ color: "var(--neuron-primary-dark)" }}>FAQ</span>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="mt-2 text-center text-[26px] font-bold tracking-tight">All your questions, answered</h2>
        </Reveal>
        <div className="mt-8 flex flex-col gap-3">
          {FAQS.map((f, i) => (
            <Reveal key={f.q} delay={i * 0.05}>
              <FaqItem q={f.q} a={f.a} />
            </Reveal>
          ))}
        </div>
      </section>

      {/* Final CTA band (dark) */}
      <section className="px-6 pb-10">
        <Reveal>
          <div
            className="neuron-gradient-text mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 rounded-2xl px-10 py-10 text-center md:flex-row md:text-left"
            style={{ background: "linear-gradient(120deg,#8B7CF6,#5A48D8,#8B7CF6)", backgroundSize: "200% 200%" }}
          >
            <div>
              <span className="inline-block rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold text-white uppercase">
                Free to start
              </span>
              <h2 className="mt-3 text-[24px] font-bold text-white">Ready to see your business clearly?</h2>
              <p className="mt-1 text-[13.5px] text-white/80">No credit card required — live in minutes.</p>
            </div>
            <Link
              href="/signup"
              className="neuron-press shrink-0 rounded-lg px-6 py-3 text-[14px] font-bold whitespace-nowrap"
              style={{ background: "#fff", color: "var(--neuron-primary-dark)" }}
            >
              Get Started Free
            </Link>
          </div>
        </Reveal>
      </section>

      {/* Footer */}
      <footer className="border-t px-6 py-10" style={{ borderColor: "var(--neuron-border)" }}>
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
          <Logo />
          <nav className="flex items-center gap-6">
            <button onClick={() => scrollTo(featuresRef)} className="text-[12.5px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
              Product
            </button>
            <Link href="/solutions" className="text-[12.5px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
              Solutions
            </Link>
            <button onClick={() => scrollTo(howRef)} className="text-[12.5px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
              How it works
            </button>
            <button onClick={() => scrollTo(faqRef)} className="text-[12.5px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
              FAQ
            </button>
          </nav>
          <p className="text-[12.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            © {new Date().getFullYear()} NeuronOS. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
