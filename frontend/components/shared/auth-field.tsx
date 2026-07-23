"use client";

import { useState } from "react";

type IconProps = { size?: number };

function MailIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

function LockIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <rect x="4" y="11" width="16" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function UserIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </svg>
  );
}

function BuildingIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <rect x="4" y="3" width="16" height="18" rx="1" />
      <path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 21v-4h6v4" />
    </svg>
  );
}

function EyeIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ size = 17 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
      <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-3.22 4.36M6.4 6.4C3.5 8.3 1 11.5 1 12s4 8 11 8a10.6 10.6 0 0 0 5.6-1.6M1 1l22 22" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
    </svg>
  );
}

const ICONS = { mail: MailIcon, lock: LockIcon, user: UserIcon, building: BuildingIcon };

export function AuthField({
  icon,
  label,
  error,
  type = "text",
  ...props
}: {
  icon: keyof typeof ICONS;
  label: string;
  error?: string;
  type?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  const Icon = ICONS[icon];
  const isPassword = type === "password";
  const resolvedType = isPassword ? (show ? "text" : "password") : type;

  return (
    <div>
      <label className="text-[12.5px] font-semibold" style={{ color: "var(--neuron-text-dim)" }}>
        {label}
      </label>
      <div className="relative mt-1.5">
        <span
          className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2"
          style={{ color: "var(--neuron-text-faint)" }}
        >
          <Icon />
        </span>
        <input
          type={resolvedType}
          className="h-12 w-full rounded-xl pr-4 pl-10.5 text-[13.5px] outline-none transition-all focus:ring-3"
          style={
            {
              border: `1px solid ${error ? "var(--neuron-red)" : "var(--neuron-border)"}`,
              background: "#fff",
              "--tw-ring-color": "rgba(108,92,231,0.15)",
            } as React.CSSProperties
          }
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--neuron-primary)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = error ? "var(--neuron-red)" : "var(--neuron-border)")}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute top-1/2 right-3.5 -translate-y-1/2"
            style={{ color: "var(--neuron-text-faint)" }}
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-[12px]" style={{ color: "var(--neuron-red)" }}>
          {error}
        </p>
      )}
    </div>
  );
}
