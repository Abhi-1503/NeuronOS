"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Avatar } from "@/components/shared/avatar";
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
import { NeuronMarkBadge } from "@/components/shared/neuron-mark";
import { clearStoredToken } from "@/lib/auth";
import { getOrganization } from "@/lib/organization";
import { getOrganizationScoreHistory } from "@/lib/reports";

type ShellProps = {
  organizationName: string;
  userName: string;
  token?: string;
  children: React.ReactNode;
  rightRail?: React.ReactNode;
};

const NAV_ITEMS = [
  { label: "Pulse", href: "/pulse", enabled: true, icon: PulseIcon },
  { label: "Customers", href: "/customers", enabled: true, icon: CustomersIcon },
  { label: "Knowledge", href: "/knowledge", enabled: true, icon: KnowledgeIcon },
  { label: "AI Workspace", href: "/ai-workspace", enabled: true, icon: AIWorkspaceIcon },
  { label: "AI Actions", href: "/ai-actions", enabled: true, icon: AIActionsIcon },
  { label: "Automations", href: "/automations", enabled: true, icon: AutomationsIcon },
  { label: "Reports", href: "/reports", enabled: true, icon: ReportsIcon },
  { label: "Settings", href: "/settings", enabled: true, icon: SettingsIcon },
];

function scoreTone(score: number): { color: string; tint: string; label: string } {
  if (score >= 80) return { color: "var(--neuron-green)", tint: "var(--neuron-green-tint)", label: "Excellent" };
  if (score >= 50) return { color: "var(--neuron-amber)", tint: "var(--neuron-amber-tint)", label: "Needs Attention" };
  return { color: "var(--neuron-red)", tint: "var(--neuron-red-tint)", label: "At Risk" };
}

// Exact sparkline treatment from docs/mockups (health-card .sparkline polyline) —
// a plain SVG polyline over the last N score_history points, no chart library needed
// for something this small.
function Sparkline({ points, color }: { points: number[]; color: string }) {
  if (points.length < 2) return null;
  const width = 160;
  const height = 34;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const coords = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * width;
      const y = height - ((p - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className="mt-2.5">
      <polyline points={coords} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  );
}

function BusinessHealthCard({ token }: { token: string }) {
  const { data: organization } = useQuery({
    queryKey: ["organization"],
    queryFn: () => getOrganization(token),
  });
  const { data: history } = useQuery({
    queryKey: ["organization-score-history"],
    queryFn: () => getOrganizationScoreHistory(token),
  });

  const score = organization?.business_health_score;
  if (score === null || score === undefined) return null;
  const tone = scoreTone(score);

  const points = history?.map((h) => h.score) ?? [];
  const delta = points.length >= 2 ? points[points.length - 1] - points[0] : null;

  return (
    <div
      className="neuron-hover-lift rounded-xl p-3.5"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
    >
      <div className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--neuron-text-faint)" }}>
        Business Health
      </div>
      <div className="mt-1 text-[22px] font-bold">{score}%</div>
      <span
        className="mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold"
        style={{ background: tone.tint, color: tone.color }}
      >
        {tone.label}
      </span>
      <Sparkline points={points} color={tone.color} />
      {delta !== null && (
        <div className="mt-1 text-[10.5px]" style={{ color: "var(--neuron-text-faint)" }}>
          {delta >= 0 ? "+" : ""}
          {delta}% vs last week
        </div>
      )}
    </div>
  );
}

/**
 * The shared shell (Blueprint §6.4): 220px sidebar / main / 300px right intelligence
 * rail, fixed across every screen. Only Pulse is enabled in the nav at Phase 0 — every
 * other module is Phase 1+ and shown as a disabled "coming soon" item rather than a
 * dead link, consistent with how Settings' integration cards are meant to communicate
 * status (Roadmap Phase 1 note) rather than silently omitting the module entirely.
 */
export function Shell({ organizationName, userName, token, children, rightRail }: ShellProps) {
  const router = useRouter();

  const pathname = usePathname();

  function handleSignOut() {
    clearStoredToken();
    router.push("/login");
  }

  return (
    <div
      className="grid min-h-screen"
      style={{
        gridTemplateColumns: rightRail
          ? "var(--neuron-sidebar-width) 1fr var(--neuron-rail-width)"
          : "var(--neuron-sidebar-width) 1fr",
        background: "var(--neuron-bg)",
        color: "var(--neuron-text)",
      }}
    >
      <aside
        className="flex flex-col gap-6 p-5"
        style={{ background: "var(--neuron-card)", borderRight: "1px solid var(--neuron-border)" }}
      >
        <div className="flex items-center gap-2 px-1">
          <NeuronMarkBadge size={28} />
          <span className="text-[15px] font-bold tracking-tight" style={{ fontFamily: "var(--font-heading)" }}>
            NeuronOS
          </span>
        </div>

        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) => {
            const isActive = item.enabled && pathname?.startsWith(item.href);
            const Icon = item.icon;
            return item.enabled ? (
              <Link
                key={item.label}
                href={item.href}
                className="relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] font-medium"
                style={{ color: isActive ? "var(--neuron-primary-dark)" : "var(--neuron-text-dim)" }}
              >
                {isActive && (
                  <motion.div
                    layoutId="neuron-active-nav-pill"
                    className="absolute inset-0 rounded-md"
                    style={{ background: "var(--neuron-primary-tint)" }}
                    transition={{ type: "spring", stiffness: 500, damping: 35 }}
                  />
                )}
                <span className="relative flex items-center gap-2.5">
                  <Icon size={16} />
                  {item.label}
                </span>
              </Link>
            ) : (
              <span
                key={item.label}
                className="flex items-center justify-between rounded-md px-2.5 py-2 text-[13.5px] font-medium"
                style={{ color: "var(--neuron-text-faint)" }}
                title="Ships in a later phase — see the Roadmap"
              >
                <span className="flex items-center gap-2.5">
                  <Icon size={16} />
                  {item.label}
                </span>
                <span className="text-[10px] uppercase tracking-wide">Soon</span>
              </span>
            );
          })}
        </nav>

        <div className="mt-auto flex flex-col gap-3 border-t pt-3" style={{ borderColor: "var(--neuron-border)" }}>
          {token && <BusinessHealthCard token={token} />}
          <div className="flex items-center gap-2 px-1">
            <Avatar name={userName} size={30} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-semibold">{userName}</div>
              <div className="truncate text-[11px]" style={{ color: "var(--neuron-text-faint)" }}>
                {organizationName}
              </div>
            </div>
            <button
              onClick={handleSignOut}
              className="text-[11.5px] font-medium"
              style={{ color: "var(--neuron-text-faint)" }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="relative overflow-y-auto">
        <div className="neuron-grid-bg pointer-events-none absolute inset-0 opacity-40" />
        <motion.main
          className="relative p-8"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          {children}
        </motion.main>
      </div>

      {rightRail ? (
        <aside
          className="p-6"
          style={{ background: "var(--neuron-card)", borderLeft: "1px solid var(--neuron-border)" }}
        >
          {rightRail}
        </aside>
      ) : null}
    </div>
  );
}
