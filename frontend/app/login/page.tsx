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
import { login, storeAuth } from "@/lib/auth";

const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      const result = await login(values);
      storeAuth(result);
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
        <h1 className="text-[20px] font-bold tracking-tight">Log in to NeuronOS</h1>

        <div className="mt-6 flex flex-col gap-4">
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
          {isSubmitting ? "Logging in…" : "Log in"}
        </Button>

        <p className="mt-4 text-center text-[12.5px]" style={{ color: "var(--neuron-text-dim)" }}>
          Need an organization?{" "}
          <Link href="/signup" className="font-medium" style={{ color: "var(--neuron-primary)" }}>
            Create one
          </Link>
        </p>
      </form>
    </div>
  );
}
