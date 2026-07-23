/**
 * Grid pattern + floating gradient orbs, used behind the landing hero and the auth
 * branding panel. Pure CSS animation (see globals.css's neuron-orb and neuron-grid-bg) —
 * no JS needed for something this ambient, and it respects prefers-reduced-motion.
 */
export function AnimatedBackground({ dark = false }: Readonly<{ dark?: boolean }>) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className={`absolute inset-0 neuron-grid-bg ${dark ? "opacity-20" : "opacity-60"}`} />
      <div
        className="neuron-orb-1 absolute -top-24 -left-24 h-96 w-96 rounded-full blur-3xl"
        style={{ background: "radial-gradient(circle,rgba(139,124,246,0.35),transparent 70%)" }}
      />
      <div
        className="neuron-orb-2 absolute top-1/3 -right-24 h-[28rem] w-[28rem] rounded-full blur-3xl"
        style={{
          background: dark
            ? "radial-gradient(circle,rgba(46,125,209,0.3),transparent 70%)"
            : "radial-gradient(circle,rgba(46,125,209,0.25),transparent 70%)",
        }}
      />
      <div
        className="neuron-orb-1 absolute -bottom-32 left-1/3 h-80 w-80 rounded-full blur-3xl"
        style={{
          background: dark
            ? "radial-gradient(circle,rgba(90,72,216,0.3),transparent 70%)"
            : "radial-gradient(circle,rgba(90,72,216,0.2),transparent 70%)",
        }}
      />
    </div>
  );
}
