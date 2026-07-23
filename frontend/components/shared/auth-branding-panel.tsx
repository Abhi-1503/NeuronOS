"use client";

import { motion } from "framer-motion";
import { AnimatedBackground } from "@/components/shared/animated-background";
import {
  AIActionsIcon,
  AutomationsIcon,
  CustomersIcon,
  KnowledgeIcon,
  PulseIcon,
} from "@/components/shared/nav-icons";
import { NeuronMark } from "@/components/shared/neuron-mark";

const NOTIFICATIONS = [
  {
    icon: KnowledgeIcon,
    tint: "#F0EDFF",
    fg: "#5A48D8",
    title: "Contract summarized",
    body: "3 key terms extracted",
    cta: "Review →",
  },
  {
    icon: CustomersIcon,
    tint: "#FDECEC",
    fg: "#E14B4B",
    title: "XYZ Solutions flagged",
    body: "Relationship score dropped to 48",
    cta: "View customer →",
  },
  {
    icon: AIActionsIcon,
    tint: "#FFF4E0",
    fg: "#E58A00",
    title: "Approval needed",
    body: "Invoice reminder ready to send",
    cta: "Review & approve →",
  },
];

const FLOW_STEPS = [
  { label: "Signal comes in", icon: PulseIcon },
  { label: "AI reasons", icon: KnowledgeIcon },
  { label: "Draft prepared", icon: AIActionsIcon },
  { label: "You approve", icon: AutomationsIcon },
];

const FEATURES = [
  { icon: PulseIcon, label: "Daily briefing" },
  { icon: CustomersIcon, label: "Relationship scoring" },
  { icon: KnowledgeIcon, label: "Auto-summarize" },
  { icon: AIActionsIcon, label: "Approve-first" },
];

export function AuthBrandingPanel() {
  return (
    <div
      className="relative flex h-full flex-col justify-between overflow-hidden p-10"
      style={{ background: "linear-gradient(160deg,#171034,#0F0B24)" }}
    >
      <AnimatedBackground dark />

      <motion.div
        className="relative flex items-center gap-2"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
          <NeuronMark size={19} variant="mono" color="#fff" />
        </div>
        <span className="text-[17px] font-bold tracking-tight text-white" style={{ fontFamily: "var(--font-heading)" }}>
          NeuronOS
        </span>
      </motion.div>

      {/* Live notification stack — real product moments, not decoration */}
      <div className="relative flex flex-col gap-2.5">
        {NOTIFICATIONS.map((n, i) => (
          <motion.div
            key={n.title}
            initial={{ opacity: 0, x: 24, rotate: i % 2 === 0 ? -2 : 2 }}
            animate={{ opacity: 1, x: 0, rotate: 0 }}
            whileHover={{ x: -4, transition: { duration: 0.2 } }}
            transition={{ duration: 0.45, delay: 0.15 + i * 0.12, ease: "easeOut" }}
            className="flex items-center gap-3 rounded-xl p-3"
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
              style={{ background: n.tint, color: n.fg }}
            >
              <n.icon size={16} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[12.5px] font-semibold text-white">{n.title}</div>
              <div className="text-[11px] text-white/60">{n.body}</div>
            </div>
            <span className="shrink-0 text-[11px] font-semibold" style={{ color: "#a396f8" }}>
              {n.cta}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Approve-first flow */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="relative flex items-center justify-between rounded-xl p-4"
        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}
      >
        {FLOW_STEPS.map((s, i) => (
          <div key={s.label} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1.5 text-center">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white">
                <s.icon size={14} />
              </div>
              <span className="text-[10px] leading-tight text-white/70">{s.label}</span>
            </div>
            {i < FLOW_STEPS.length - 1 && (
              <div className="mx-1 mb-4 h-px flex-1" style={{ background: "linear-gradient(90deg,rgba(255,255,255,0.3),rgba(110,231,249,0.5))" }} />
            )}
          </div>
        ))}
      </motion.div>

      <div className="relative">
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="max-w-sm text-[26px] leading-[1.15] font-bold text-white"
        >
          Every signal. <span style={{ color: "#6EE7F9" }}>One clear decision.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-2.5 max-w-sm text-[13.5px] leading-relaxed text-white/70"
        >
          NeuronOS reads what&apos;s already happening in your business and prepares the next
          best action — reasoning shown, you decide what happens.
        </motion.p>

        <div className="mt-5 flex flex-wrap gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.4 + i * 0.06 }}
              className="flex items-center gap-1.5 text-white/80"
            >
              <f.icon size={13} />
              <span className="text-[11.5px]">{f.label}</span>
            </motion.div>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <span className="rounded-full px-2.5 py-1 text-[10.5px] font-semibold text-white/80" style={{ background: "rgba(255,255,255,0.08)" }}>
            Approve-First AI
          </span>
          <span className="rounded-full px-2.5 py-1 text-[10.5px] font-semibold text-white/80" style={{ background: "rgba(255,255,255,0.08)" }}>
            Row-Level Security
          </span>
        </div>
      </div>

      <p className="relative text-[12px] text-white/50">© {new Date().getFullYear()} NeuronOS. All rights reserved.</p>
    </div>
  );
}
