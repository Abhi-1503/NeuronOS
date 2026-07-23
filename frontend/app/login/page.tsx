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
import { login, storeAuth } from "@/lib/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [remember, setRemember] = useState(true);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      const result = await login(values);
      storeAuth(result, remember);
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
            Welcome <span style={{ color: "var(--neuron-primary)" }} className="italic">back.</span>
          </h1>
          <p className="mt-2 text-[13.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            New here?{" "}
            <Link href="/signup" className="font-semibold" style={{ color: "var(--neuron-primary)" }}>
              Create an account
            </Link>
          </p>

          <div className="mt-7 flex flex-col gap-4">
            <AuthField icon="mail" label="Email" type="email" placeholder="you@example.com" {...register("email")} />
            {errors.email && <p className="-mt-3 text-[12px] text-red-600">{errors.email.message}</p>}

            <AuthField icon="lock" label="Password" type="password" placeholder="••••••••" {...register("password")} />
            {errors.password && <p className="-mt-3 text-[12px] text-red-600">{errors.password.message}</p>}
          </div>

          <label className="mt-4 flex cursor-pointer items-center gap-2 text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded accent-[var(--neuron-primary)]"
            />
            Remember me
          </label>

          {serverError && <p className="mt-4 text-[12.5px] text-red-600">{serverError}</p>}

          <motion.button
            type="submit"
            disabled={isSubmitting}
            whileTap={{ scale: 0.98 }}
            className="mt-6 h-12 w-full rounded-xl text-[14px] font-bold text-white shadow-lg disabled:opacity-60"
            style={{ background: "linear-gradient(135deg,var(--neuron-primary),var(--neuron-primary-dark))", boxShadow: "0 10px 24px rgba(108,92,231,0.3)" }}
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </motion.button>

          <p className="mt-5 text-center text-[11.5px]" style={{ color: "var(--neuron-text-faint)" }}>
            By continuing, you agree to NeuronOS&apos;s approve-first terms — nothing acts on your
            business without your say.
          </p>
        </motion.form>
      </div>
    </div>
  );
}
