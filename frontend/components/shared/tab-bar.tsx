"use client";

import { motion } from "framer-motion";

/**
 * Shared tab bar with a sliding active-underline (framer-motion layoutId) — the same
 * spring-slide treatment as the sidebar's active-nav-pill, reused here instead of each
 * page hand-rolling its own static border-bottom.
 */
export function TabBar<T extends string>({
  tabs,
  active,
  onChange,
  counts,
  layoutId,
}: {
  tabs: readonly T[];
  active: T;
  onChange: (tab: T) => void;
  counts?: Partial<Record<T, number>>;
  layoutId: string;
}) {
  return (
    <div className="flex gap-5 border-b" style={{ borderColor: "var(--neuron-border)" }}>
      {tabs.map((t) => {
        const isActive = active === t;
        const count = counts?.[t];
        return (
          <button
            key={t}
            onClick={() => onChange(t)}
            className="relative pb-2.5 text-[13px] font-semibold"
            style={{ color: isActive ? "var(--neuron-primary)" : "var(--neuron-text-faint)" }}
          >
            {t}
            {count !== undefined && ` (${count})`}
            {isActive && (
              <motion.div
                layoutId={layoutId}
                className="absolute bottom-0 left-0 right-0 h-0.5"
                style={{ background: "var(--neuron-primary)" }}
                transition={{ type: "spring", stiffness: 500, damping: 35 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
