"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearStoredToken } from "@/lib/auth";

type ShellProps = {
  organizationName: string;
  userName: string;
  children: React.ReactNode;
  rightRail?: React.ReactNode;
};

const NAV_ITEMS = [
  { label: "Pulse", href: "/pulse", enabled: true },
  { label: "Customers", href: "#", enabled: false },
  { label: "Knowledge", href: "#", enabled: false },
  { label: "AI Actions", href: "#", enabled: false },
  { label: "Automations", href: "#", enabled: false },
  { label: "Reports", href: "#", enabled: false },
  { label: "Settings", href: "#", enabled: false },
];

/**
 * The shared shell (Blueprint §6.4): 220px sidebar / main / 300px right intelligence
 * rail, fixed across every screen. Only Pulse is enabled in the nav at Phase 0 — every
 * other module is Phase 1+ and shown as a disabled "coming soon" item rather than a
 * dead link, consistent with how Settings' integration cards are meant to communicate
 * status (Roadmap Phase 1 note) rather than silently omitting the module entirely.
 */
export function Shell({ organizationName, userName, children, rightRail }: ShellProps) {
  const router = useRouter();

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
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg text-sm font-bold text-white"
            style={{
              background: "linear-gradient(135deg,#8B7CF6,#5A48D8)",
            }}
          >
            N
          </div>
          <span className="text-[15px] font-bold tracking-tight">NeuronOS</span>
        </div>

        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) =>
            item.enabled ? (
              <Link
                key={item.label}
                href={item.href}
                className="rounded-md px-2.5 py-2 text-[13.5px] font-medium"
                style={{ background: "var(--neuron-primary-tint)", color: "var(--neuron-primary-dark)" }}
              >
                {item.label}
              </Link>
            ) : (
              <span
                key={item.label}
                className="flex items-center justify-between rounded-md px-2.5 py-2 text-[13.5px] font-medium"
                style={{ color: "var(--neuron-text-faint)" }}
                title="Ships in a later phase — see the Roadmap"
              >
                {item.label}
                <span className="text-[10px] uppercase tracking-wide">Soon</span>
              </span>
            ),
          )}
        </nav>

        <div className="mt-auto flex flex-col gap-2 border-t pt-3" style={{ borderColor: "var(--neuron-border)" }}>
          <div className="px-1 text-[12px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
            {organizationName}
          </div>
          <div className="flex items-center justify-between px-1">
            <span className="text-[13px] font-medium">{userName}</span>
            <button
              onClick={handleSignOut}
              className="text-[12px] font-medium"
              style={{ color: "var(--neuron-text-faint)" }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="p-8">{children}</main>

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
