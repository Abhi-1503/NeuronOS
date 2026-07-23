"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/shared/avatar";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import {
  getOverview,
  getRevenueBySource,
  getRevenueTrend,
  getTopCustomers,
  type RevenueTrendPoint,
} from "@/lib/reports";

const TABS = ["Overview", "Sales", "Finance", "Operations", "Team"] as const;

function formatINR(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function StatTile({ label, value, delta }: { label: string; value: string; delta?: number }) {
  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
    >
      <div className="text-[11px] font-semibold" style={{ color: "var(--neuron-text-faint)" }}>
        {label}
      </div>
      <div className="mt-1 text-[22px] font-bold">{value}</div>
      {delta !== undefined && (
        <div
          className="mt-1 text-[11px] font-semibold"
          style={{ color: delta >= 0 ? "var(--neuron-green)" : "var(--neuron-red)" }}
        >
          {delta >= 0 ? "+" : ""}
          {delta}%
        </div>
      )}
    </div>
  );
}

// A minimal, dependency-free line chart: thin 2px lines, a muted comparison series,
// a legend (required once there are ≥2 series), and a hover crosshair+tooltip
// (dataviz skill — interaction is not optional for a line chart).
function TrendChart({ points }: { points: RevenueTrendPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  if (points.length === 0) return null;

  const width = 600;
  const height = 180;
  const padding = 24;
  const maxValue = Math.max(1, ...points.map((p) => Math.max(p.this_period, p.last_period ?? 0)));

  function xAt(i: number) {
    return padding + (i / Math.max(1, points.length - 1)) * (width - padding * 2);
  }
  function yAt(v: number) {
    return height - padding - (v / maxValue) * (height - padding * 2);
  }

  function pathFor(key: "this_period" | "last_period") {
    const pts = points
      .map((p, i) => ({ x: xAt(i), y: p[key] === null ? null : yAt(p[key] as number) }))
      .filter((p) => p.y !== null);
    if (pts.length === 0) return "";
    return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  }

  const hovered = hoverIdx !== null ? points[hoverIdx] : null;

  return (
    <div className="relative">
      <div className="mb-2 flex items-center gap-4 text-[11px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-3 rounded-full" style={{ background: "var(--neuron-primary)" }} />
          This month
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-3 rounded-full" style={{ background: "var(--neuron-text-faint)" }} />
          Last month
        </span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        onMouseLeave={() => setHoverIdx(null)}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const relX = ((e.clientX - rect.left) / rect.width) * width;
          const idx = Math.round(((relX - padding) / (width - padding * 2)) * (points.length - 1));
          setHoverIdx(Math.min(points.length - 1, Math.max(0, idx)));
        }}
      >
        <path d={pathFor("last_period")} fill="none" stroke="var(--neuron-text-faint)" strokeWidth={2} />
        <path d={pathFor("this_period")} fill="none" stroke="var(--neuron-primary)" strokeWidth={2} strokeLinecap="round" />
        {hoverIdx !== null && (
          <line
            x1={xAt(hoverIdx)}
            x2={xAt(hoverIdx)}
            y1={padding}
            y2={height - padding}
            stroke="var(--neuron-border)"
            strokeWidth={1}
          />
        )}
      </svg>
      {hovered && (
        <div
          className="pointer-events-none absolute top-0 rounded-lg px-2 py-1 text-[11px] font-semibold"
          style={{
            left: `${(xAt(hoverIdx!) / width) * 100}%`,
            background: "var(--neuron-text)",
            color: "var(--neuron-card)",
            transform: "translateX(-50%)",
          }}
        >
          Day {hovered.day_of_period}: {formatINR(hovered.this_period)}
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: overview } = useQuery({
    queryKey: ["reports-overview"],
    queryFn: () => getOverview(auth!.token),
    enabled: !!auth,
  });
  const { data: trend } = useQuery({
    queryKey: ["reports-trend"],
    queryFn: () => getRevenueTrend(auth!.token),
    enabled: !!auth && tab === "Overview",
  });
  const { data: bySource } = useQuery({
    queryKey: ["reports-by-source"],
    queryFn: () => getRevenueBySource(auth!.token),
    enabled: !!auth && tab === "Overview",
  });
  const { data: topCustomers } = useQuery({
    queryKey: ["reports-top-customers"],
    queryFn: () => getTopCustomers(auth!.token),
    enabled: !!auth && tab === "Overview",
  });

  if (!auth) return null;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-3xl">
        <h1 className="text-[22px] font-bold tracking-tight">Reports</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          Insights and analytics for your business.
        </p>

        <div className="mt-4">
          <TabBar tabs={TABS} active={tab} onChange={setTab} layoutId="reports-tab" />
        </div>

        {tab !== "Overview" ? (
          <p className="mt-6 text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
            {comingSoonMessage(tab)}
          </p>
        ) : (
          <div className="mt-6 flex flex-col gap-6">
            {overview && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <StatTile
                  label="Total Revenue"
                  value={formatINR(overview.total_revenue)}
                  delta={overview.deltas.total_revenue}
                />
                <StatTile label="New Deals" value={String(overview.new_deals)} delta={overview.deltas.new_deals} />
                <StatTile
                  label="Revenue At Risk"
                  value={formatINR(overview.revenue_at_risk)}
                  delta={undefined}
                />
                <StatTile label="Open Invoices" value={String(overview.open_invoices)} />
              </div>
            )}

            <div
              className="rounded-2xl p-5"
              style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
            >
              <h2 className="text-[13px] font-bold">Revenue Trend</h2>
              <div className="mt-3">{trend && <TrendChart points={trend} />}</div>
            </div>

            <div
              className="rounded-2xl p-5"
              style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)" }}
            >
              <h2 className="text-[13px] font-bold">Revenue by Source</h2>
              <div className="mt-3 flex flex-col gap-2">
                {bySource?.map((slice) => (
                  <div key={slice.label} className="flex items-center gap-3">
                    <span className="w-32 shrink-0 text-[12px]" style={{ color: "var(--neuron-text-dim)" }}>
                      {slice.label}
                    </span>
                    <div className="h-2 flex-1 rounded-full" style={{ background: "var(--neuron-border)" }}>
                      <div
                        className="h-2 rounded-full"
                        style={{ width: `${slice.pct}%`, background: "var(--neuron-primary)" }}
                      />
                    </div>
                    <span className="w-12 shrink-0 text-right text-[12px] font-semibold">{slice.pct}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div
              className="rounded-2xl p-5"
              style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
            >
              <h2 className="text-[13px] font-bold">Top Performing Customers</h2>
              <table className="mt-3 w-full text-[12.5px]">
                <thead>
                  <tr className="text-left" style={{ color: "var(--neuron-text-faint)" }}>
                    <th className="pb-2 font-semibold">Customer</th>
                    <th className="pb-2 font-semibold">Revenue</th>
                    <th className="pb-2 font-semibold">Deals</th>
                    <th className="pb-2 font-semibold">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {topCustomers?.map((c) => (
                    <tr key={c.id} style={{ borderTop: "1px solid var(--neuron-border)" }}>
                      <td className="py-2 font-semibold">
                        <div className="flex items-center gap-2">
                          <Avatar name={c.name} size={22} />
                          {c.name}
                        </div>
                      </td>
                      <td className="py-2">{formatINR(c.revenue_total)}</td>
                      <td className="py-2">{c.deal_count}</td>
                      <td className="py-2">{c.relationship_score ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}

function comingSoonMessage(tab: string): string {
  return `${tab} reports aren't built yet — only Overview is real, computed data (Roadmap Phase 1 scope). Ships when there's real integrated data to report on (Phase 2).`;
}
