const AVATAR_COLORS = [
  "#6C5CE7",
  "#2E7DD1",
  "#1DAE6E",
  "#E58A00",
  "#E14B4B",
  "#9B59B6",
];

function colorForName(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
    hash |= 0;
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function initialsForName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({
  name,
  size = 28,
  shape = "circle",
}: {
  name: string;
  size?: number;
  shape?: "circle" | "square";
}) {
  return (
    <div
      className="flex shrink-0 items-center justify-center font-bold text-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        background: colorForName(name),
        borderRadius: shape === "circle" ? "50%" : size * 0.28,
      }}
      title={name}
    >
      {initialsForName(name)}
    </div>
  );
}
