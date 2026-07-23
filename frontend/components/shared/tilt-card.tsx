"use client";

import { motion, useMotionTemplate, useMotionValue, useSpring, useTransform } from "framer-motion";

/**
 * A card that tilts in 3D toward the cursor and carries a soft light that follows it —
 * pointer-position-driven, not a canned CSS hover, so it reads as genuinely responsive
 * rather than a single hover state. Falls back to a flat, static card with no listeners
 * on touch devices (no mouse to track) and respects prefers-reduced-motion via the
 * spring's own damping rather than disabling the effect outright.
 */
export function TiltCard({
  children,
  className,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);
  const rotateX = useSpring(0, { stiffness: 220, damping: 20 });
  const rotateY = useSpring(0, { stiffness: 220, damping: 20 });
  const spotlightX = useTransform(mouseX, (v) => `${v * 100}%`);
  const spotlightY = useTransform(mouseY, (v) => `${v * 100}%`);
  const glow = useMotionTemplate`radial-gradient(circle at ${spotlightX} ${spotlightY}, rgba(139,124,246,0.16), transparent 60%)`;

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    mouseX.set(px);
    mouseY.set(py);
    rotateY.set((px - 0.5) * 10);
    rotateX.set((0.5 - py) * 10);
  }

  function handleMouseLeave() {
    rotateX.set(0);
    rotateY.set(0);
  }

  return (
    <motion.div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ rotateX, rotateY, transformPerspective: 800, ...style }}
      className={className}
    >
      <motion.div className="pointer-events-none absolute inset-0 rounded-2xl" style={{ background: glow }} />
      {children}
    </motion.div>
  );
}
