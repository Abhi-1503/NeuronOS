"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/shared/avatar";
import { SearchIcon } from "@/components/shared/nav-icons";
import { Shell } from "@/components/shared/shell";
import { TabBar } from "@/components/shared/tab-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getStoredAuth, type AuthResult } from "@/lib/auth";
import { createCustomer, listCustomers, type CustomerSummary } from "@/lib/customers";

const TABS = ["All Customers", "Active", "At Risk", "Inactive"] as const;
type Tab = (typeof TABS)[number];

function scoreTone(score: number | null): { bg: string; fg: string; label: string } {
  if (score === null) return { bg: "var(--neuron-border)", fg: "var(--neuron-text-faint)", label: "No score yet" };
  if (score >= 90) return { bg: "var(--neuron-green-tint)", fg: "var(--neuron-green)", label: "Excellent" };
  if (score >= 75) return { bg: "var(--neuron-green-tint)", fg: "var(--neuron-green)", label: "Very Good" };
  if (score >= 50) return { bg: "var(--neuron-amber-tint)", fg: "var(--neuron-amber)", label: "Good" };
  if (score >= 35) return { bg: "var(--neuron-red-tint)", fg: "var(--neuron-red)", label: "At Risk" };
  return { bg: "var(--neuron-red-tint)", fg: "var(--neuron-red)", label: "High Risk" };
}

function formatINR(value: number): string {
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  return `₹${value.toLocaleString("en-IN")}`;
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="neuron-hover-lift rounded-2xl p-4"
      style={{ background: "var(--neuron-card)", border: "1px solid var(--neuron-border)", boxShadow: "var(--neuron-shadow)" }}
    >
      <div className="text-[11px] font-semibold" style={{ color: "var(--neuron-text-faint)" }}>
        {label}
      </div>
      <div className="mt-1 text-[20px] font-bold">{value}</div>
    </div>
  );
}

function matchesTab(c: CustomerSummary, tab: Tab): boolean {
  if (tab === "All Customers") return true;
  if (tab === "Active") return c.status === "active";
  if (tab === "At Risk") return c.status === "at_risk";
  return c.status === "inactive" || c.status === "churned";
}

export default function CustomersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [auth, setAuth] = useState<AuthResult | null>(null);
  const [tab, setTab] = useState<Tab>("All Customers");
  const [search, setSearch] = useState("");
  const [addingOpen, setAddingOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newLastContact, setNewLastContact] = useState("");

  useEffect(() => {
    const stored = getStoredAuth();
    if (!stored) {
      router.replace("/login");
      return;
    }
    setAuth(stored);
  }, [router]);

  const { data: customers, isLoading } = useQuery({
    queryKey: ["customers"],
    queryFn: () => listCustomers(auth!.token),
    enabled: !!auth,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createCustomer(
        {
          name: newName,
          last_contact_at: newLastContact ? new Date(newLastContact).toISOString() : undefined,
        },
        auth!.token,
      ),
    onSuccess: () => {
      setNewName("");
      setNewLastContact("");
      setAddingOpen(false);
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });

  if (!auth) return null;

  const totalCustomers = customers?.length ?? 0;
  const atRiskCount = customers?.filter((c) => c.status === "at_risk").length ?? 0;
  const totalRevenue = customers?.reduce((sum, c) => sum + c.revenue_total, 0) ?? 0;
  const scored = customers?.filter((c) => c.relationship_score !== null) ?? [];
  const avgScore =
    scored.length > 0
      ? Math.round(scored.reduce((sum, c) => sum + (c.relationship_score ?? 0), 0) / scored.length)
      : null;

  const searched = customers?.filter((c) => c.name.toLowerCase().includes(search.toLowerCase())) ?? [];
  const visible = searched.filter((c) => matchesTab(c, tab));
  const tabCount = (t: Tab) => searched.filter((c) => matchesTab(c, t)).length;

  return (
    <Shell organizationName={auth.organization.name} userName={auth.user.name} token={auth.token}>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-bold tracking-tight">Customers</h1>
            <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
              All your customers and relationship insights in one place.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <div
              className="flex items-center gap-2 rounded-lg px-3 py-2"
              style={{ background: "#fff", border: "1px solid var(--neuron-border)" }}
            >
              <span style={{ color: "var(--neuron-text-faint)" }}>
                <SearchIcon size={14} />
              </span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search customers…"
                className="w-37.5 bg-transparent text-[13px] outline-none"
              />
            </div>
            <Button onClick={() => setAddingOpen((v) => !v)}>+ Add Customer</Button>
          </div>
        </div>

        {addingOpen && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) createMutation.mutate();
            }}
            className="mt-4 flex items-end gap-3 rounded-2xl p-4"
            style={{
              background: "var(--neuron-card)",
              border: "1px solid var(--neuron-border)",
              boxShadow: "var(--neuron-shadow)",
            }}
          >
            <div className="flex-1">
              <label className="text-[12px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
                Customer name
              </label>
              <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="ABC Ltd" />
            </div>
            <div className="flex-1">
              <label className="text-[12px] font-medium" style={{ color: "var(--neuron-text-dim)" }}>
                Last contact date (optional)
              </label>
              <Input
                type="date"
                value={newLastContact}
                onChange={(e) => setNewLastContact(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={!newName.trim() || createMutation.isPending}>
              {createMutation.isPending ? "Adding…" : "Save"}
            </Button>
          </form>
        )}

        {totalCustomers > 0 && (
          <div className="mt-5 grid grid-cols-4 gap-3">
            <StatTile label="Total Customers" value={String(totalCustomers)} />
            <StatTile label="At Risk" value={String(atRiskCount)} />
            <StatTile label="Total Revenue" value={formatINR(totalRevenue)} />
            <StatTile label="Avg Relationship Score" value={avgScore !== null ? String(avgScore) : "—"} />
          </div>
        )}

        <div className="mt-5">
          <TabBar
            tabs={TABS}
            active={tab}
            onChange={setTab}
            layoutId="customers-tab"
            counts={{ Active: tabCount("Active"), "At Risk": tabCount("At Risk"), Inactive: tabCount("Inactive") }}
          />
        </div>

        <div className="mt-4 flex flex-col gap-2">
          {isLoading && (
            <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
              Loading…
            </p>
          )}
          {!isLoading && visible.length === 0 && (
            <p className="text-[13px]" style={{ color: "var(--neuron-text-faint)" }}>
              {totalCustomers === 0 ? "No customers yet — add your first one above." : "No customers match this view."}
            </p>
          )}
          {visible.map((c: CustomerSummary, i) => {
            const tone = scoreTone(c.relationship_score);
            return (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.04 }}
              >
              <Link
                href={`/customers/${c.id}`}
                className="neuron-hover-lift flex items-center justify-between rounded-xl p-4"
                style={{
                  background: "var(--neuron-card)",
                  border: "1px solid var(--neuron-border)",
                }}
              >
                <div className="flex items-center gap-3">
                  <Avatar name={c.name} shape="square" size={36} />
                  <div>
                    <div className="text-[13.5px] font-bold">{c.name}</div>
                    <div className="mt-0.5 text-[12px]" style={{ color: "var(--neuron-text-faint)" }}>
                      {c.last_contact_at
                        ? `Last contact ${new Date(c.last_contact_at).toLocaleDateString()}`
                        : "No contact logged yet"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[12.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
                    {formatINR(c.revenue_total)}
                  </span>
                  <div className="text-right">
                    <div className="text-[15px] font-bold" style={{ color: tone.fg }}>
                      {c.relationship_score ?? "—"}
                    </div>
                    <div className="text-[10.5px] font-semibold" style={{ color: tone.fg }}>
                      {tone.label}
                    </div>
                  </div>
                </div>
              </Link>
              </motion.div>
            );
          })}
        </div>
      </div>
    </Shell>
  );
}
