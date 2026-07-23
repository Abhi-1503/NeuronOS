/**
 * The NeuronOS mark (docs/mockups/neuronos_brand_concept.html, §01 "The Mark") — three
 * input signals (Gmail, CRM, calendar; drawn as dendrites, not straight lines, since real
 * business data never arrives in clean geometry) converge on one node and leave as a
 * single output signal. Not decorative node-cluster art — it's a diagram of what the
 * product actually does.
 *
 * `variant="mono"` is the single-color cutout (white or currentColor) for placement on a
 * colored/gradient background — the sidebar badge, the auth panel, chat bubbles.
 * `variant="color"` is the full palette (violet inputs, indigo node, cyan output) for
 * placement on light surfaces — the landing page wordmark, the favicon backdrop.
 */
export function NeuronMark({
  size = 24,
  variant = "mono",
  color = "#fff",
}: {
  size?: number;
  variant?: "mono" | "color";
  color?: string;
}) {
  if (variant === "color") {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="7" cy="6" r="1.4" fill="#8B7CF6" />
        <circle cx="4" cy="12" r="1.4" fill="#8B7CF6" />
        <circle cx="7" cy="18" r="1.4" fill="#8B7CF6" />
        <path d="M7,6 C9,8 10,10 12,12" stroke="#8B7CF6" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M4,12 L12,12" stroke="#8B7CF6" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M7,18 C9,16 10,14 12,12" stroke="#8B7CF6" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M13,12 C16,11 18,10 21,8" stroke="#6EE7F9" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="12" r="2" fill="#5A48D8" />
        <circle cx="21" cy="8" r="1" fill="#6EE7F9" />
      </svg>
    );
  }

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="7" cy="6" r="1.4" fill={color} opacity="0.85" />
      <circle cx="4" cy="12" r="1.4" fill={color} opacity="0.85" />
      <circle cx="7" cy="18" r="1.4" fill={color} opacity="0.85" />
      <path d="M7,6 C9,8 10,10 12,12" stroke={color} strokeWidth="1.4" strokeLinecap="round" opacity="0.85" />
      <path d="M4,12 L12,12" stroke={color} strokeWidth="1.4" strokeLinecap="round" opacity="0.85" />
      <path d="M7,18 C9,16 10,14 12,12" stroke={color} strokeWidth="1.4" strokeLinecap="round" opacity="0.85" />
      <path d="M13,12 C16,11 18,10 21,8" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="12" r="2" fill={color} />
      <circle cx="21" cy="8" r="1" fill={color} />
    </svg>
  );
}

/** The badge wrapper used everywhere the mark sits on its own gradient tile (sidebar,
 * auth panel, chat avatar) — centralized so the gradient/radius/size stay in sync. */
export function NeuronMarkBadge({ size = 28 }: { size?: number }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-lg"
      style={{ width: size, height: size, background: "linear-gradient(135deg,#8B7CF6,#5A48D8)" }}
    >
      <NeuronMark size={Math.round(size * 0.6)} variant="mono" color="#fff" />
    </div>
  );
}
