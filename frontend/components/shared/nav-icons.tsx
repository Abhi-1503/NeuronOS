/**
 * Exact SVG paths copied from docs/mockups/*.html — these are the mockup's own hand-drawn
 * nav icons, not a library substitute, so the sidebar matches pixel-for-pixel.
 */
type IconProps = { size?: number };

function Icon({ size = 16, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export function PulseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M13 2 3 14h7l-1 8 10-12h-7z" />
    </Icon>
  );
}

export function CustomersIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="9" cy="7" r="4" />
      <path d="M2 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2" />
      <circle cx="19" cy="8" r="2.5" />
    </Icon>
  );
}

export function KnowledgeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 4h11l5 5v11H4z" />
      <path d="M14 4v6h6" />
    </Icon>
  );
}

export function AIActionsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" />
    </Icon>
  );
}

export function AutomationsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 4h16v4H4zM4 10h16v10H4z" />
      <path d="M9 14h6" />
    </Icon>
  );
}

export function ReportsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 3v18h18M7 15l4-5 3 3 5-7" />
    </Icon>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </Icon>
  );
}

// AI Workspace isn't in the original mockup's nav (it ships as a Pulse quick-ask + a
// dedicated screen per this Roadmap phase) — a chat-bubble glyph in the same hand-drawn
// stroke style as the rest of this set, not a lucide import, to match visually.
export function AIWorkspaceIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 4h16v12H8l-4 4z" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </Icon>
  );
}

export function ShieldIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 2 4 5v6c0 5 3.5 8.5 8 11 4.5-2.5 8-6 8-11V5z" />
      <path d="m9 12 2 2 4-4" />
    </Icon>
  );
}
