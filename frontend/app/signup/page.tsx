"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { acceptTerms, signup, storeAuth } from "@/lib/auth";

// The current Terms of Service version an org's Owner accepts on signup (Blueprint §17.8,
// Database Spec §1.1's `terms_accepted_version`) — bumped whenever a materially changed
// ToS is published. Hardcoded here since there's no ToS-versioning admin surface yet.
const CURRENT_TERMS_VERSION = "2026-07-01";

const signupSchema = z.object({
  organization_name: z.string().min(1, "Required").max(200),
  name: z.string().min(1, "Required").max(200),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
});

type SignupForm = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({ resolver: zodResolver(signupSchema) });

  async function onSubmit(values: SignupForm) {
    setServerError(null);
    try {
      const result = await signup(values);
      storeAuth(result);
      // Blocking step per Blueprint §17.8 / API Spec §1 — the Owner accepts terms as
      // part of signup, not as a separate optional screen the org can skip past.
      const organization = await acceptTerms(CURRENT_TERMS_VERSION, result.token);
      storeAuth({ ...result, organization });
      router.push("/pulse");
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ background: "var(--neuron-bg)" }}
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm rounded-2xl p-8"
        style={{
          background: "var(--neuron-card)",
          border: "1px solid var(--neuron-border)",
          boxShadow: "var(--neuron-shadow)",
        }}
      >
        <h1 className="text-[20px] font-bold tracking-tight">Create your organization</h1>
        <p className="mt-1 text-[13px]" style={{ color: "var(--neuron-text-dim)" }}>
          You&apos;ll be the Owner — you can invite your team next.
        </p>

        <div className="mt-6 flex flex-col gap-4">
          <div>
            <Label htmlFor="organization_name">Organization name</Label>
            <Input id="organization_name" {...register("organization_name")} />
            {errors.organization_name && (
              <p className="mt-1 text-[12px] text-red-600">{errors.organization_name.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="name">Your name</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="mt-1 text-[12px] text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" {...register("email")} />
            {errors.email && <p className="mt-1 text-[12px] text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register("password")} />
            {errors.password && (
              <p className="mt-1 text-[12px] text-red-600">{errors.password.message}</p>
            )}
          </div>
        </div>

        {serverError && <p className="mt-4 text-[12.5px] text-red-600">{serverError}</p>}

        <Button type="submit" disabled={isSubmitting} className="mt-6 w-full">
          {isSubmitting ? "Creating…" : "Create organization"}
        </Button>

        <p className="mt-4 text-center text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
          Already have an account?{" "}
          <Link href="/login" className="font-medium" style={{ color: "var(--neuron-primary)" }}>
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
