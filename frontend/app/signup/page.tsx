"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthBrandingPanel } from "@/components/shared/auth-branding-panel";
import { AuthField } from "@/components/shared/auth-field";
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
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({ resolver: zodResolver(signupSchema) });

  const password = watch("password") ?? "";
  const passwordLongEnough = password.length >= 8;

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
    <div className="grid min-h-screen grid-cols-2" style={{ background: "#fff" }}>
      <AuthBrandingPanel />
      <div className="flex items-center justify-center p-8">
        <motion.form
          onSubmit={handleSubmit(onSubmit)}
          className="w-full max-w-sm"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1 className="text-[34px] leading-[1.1] font-bold tracking-tight">
            Create your <span style={{ color: "var(--neuron-primary)" }} className="italic">account.</span>
          </h1>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            Already have one?{" "}
            <Link href="/login" className="font-semibold" style={{ color: "var(--neuron-primary)" }}>
              Sign in
            </Link>
          </p>
          <p className="mt-3 text-[12.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            You&apos;ll be the Owner — you can invite your team next.
          </p>

          <div className="mt-6 flex flex-col gap-4">
            <AuthField
              icon="building"
              label="Organization name"
              placeholder="Acme Inc"
              {...register("organization_name")}
            />
            {errors.organization_name && (
              <p className="-mt-3 text-[12px] text-red-600">{errors.organization_name.message}</p>
            )}

            <AuthField icon="user" label="Full name" placeholder="Jane Founder" {...register("name")} />
            {errors.name && <p className="-mt-3 text-[12px] text-red-600">{errors.name.message}</p>}

            <AuthField icon="mail" label="Email" type="email" placeholder="you@example.com" {...register("email")} />
            {errors.email && <p className="-mt-3 text-[12px] text-red-600">{errors.email.message}</p>}

            <AuthField icon="lock" label="Password" type="password" placeholder="At least 8 characters" {...register("password")} />

            <div className="-mt-2 flex items-center gap-1.5 text-[12px]" style={{ color: passwordLongEnough ? "var(--neuron-green)" : "var(--neuron-text-faint)" }}>
              <span
                className="flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white"
                style={{ background: passwordLongEnough ? "var(--neuron-green)" : "var(--neuron-border)" }}
              >
                {passwordLongEnough ? "✓" : ""}
              </span>
              At least 8 characters
            </div>
          </div>

          {serverError && <p className="mt-4 text-[12.5px] text-red-600">{serverError}</p>}

          <motion.button
            type="submit"
            disabled={isSubmitting}
            whileTap={{ scale: 0.98 }}
            className="mt-6 h-12 w-full rounded-xl text-[14px] font-bold text-white shadow-lg disabled:opacity-60"
            style={{ background: "linear-gradient(135deg,var(--neuron-primary),var(--neuron-primary-dark))", boxShadow: "0 10px 24px rgba(108,92,231,0.3)" }}
          >
            {isSubmitting ? "Creating…" : "Create free account"}
          </motion.button>

          <p className="mt-5 text-center text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            No credit card required — you decide what NeuronOS is allowed to do, always.
          </p>
        </motion.form>
      </div>
    </div>
  );
}
