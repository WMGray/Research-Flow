import type { ReactNode, SVGProps } from "react";

export type AppIconName =
  | "alert"
  | "arrow-right"
  | "book"
  | "calendar"
  | "check"
  | "close"
  | "clock"
  | "document"
  | "download"
  | "filter"
  | "folder"
  | "help"
  | "home"
  | "image"
  | "list"
  | "play"
  | "search"
  | "settings"
  | "spark"
  | "sun";

type AppIconProps = SVGProps<SVGSVGElement> & {
  name: AppIconName;
  size?: number;
  strokeWidth?: number;
};

export function AppIcon({
  name,
  size = 20,
  strokeWidth = 1.9,
  ...props
}: AppIconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      {renderIcon(name)}
    </svg>
  );
}

function renderIcon(name: AppIconName): ReactNode {
  switch (name) {
    case "alert":
      return (
        <>
          <path d="M12 4 20 18H4L12 4Z" />
          <path d="M12 9.5V13.5" />
          <path d="M12 17H12.01" />
        </>
      );
    case "arrow-right":
      return (
        <>
          <path d="M5 12H19" />
          <path d="m13 6 6 6-6 6" />
        </>
      );
    case "book":
      return (
        <>
          <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H19v15H6.5A2.5 2.5 0 0 0 4 21z" />
          <path d="M8 7h7" />
          <path d="M8 11h7" />
          <path d="M8 15h4" />
        </>
      );
    case "calendar":
      return (
        <>
          <rect height="15" rx="2.5" width="16" x="4" y="5" />
          <path d="M8 3v4" />
          <path d="M16 3v4" />
          <path d="M4 10h16" />
        </>
      );
    case "check":
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="m8.7 12.3 2.1 2.1 4.6-4.8" />
        </>
      );
    case "close":
      return (
        <>
          <path d="M6 6 18 18" />
          <path d="M18 6 6 18" />
        </>
      );
    case "clock":
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v4.5l3 1.8" />
        </>
      );
    case "document":
      return (
        <>
          <path d="M8 3h6l4 4v14H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
          <path d="M14 3v5h5" />
          <path d="M9 12h6" />
          <path d="M9 16h6" />
        </>
      );
    case "download":
      return (
        <>
          <path d="M12 4v10" />
          <path d="m8 10 4 4 4-4" />
          <path d="M5 18h14" />
        </>
      );
    case "filter":
      return (
        <>
          <path d="M4 6h16" />
          <path d="M7 12h10" />
          <path d="M10 18h4" />
        </>
      );
    case "folder":
      return (
        <>
          <path d="M3.5 7.5A2.5 2.5 0 0 1 6 5h4l2 2h6a2.5 2.5 0 0 1 2.5 2.5V17A2.5 2.5 0 0 1 18 19.5H6A2.5 2.5 0 0 1 3.5 17Z" />
        </>
      );
    case "help":
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="M9.7 9.5a2.3 2.3 0 1 1 4.3 1.2c-.5.7-1.5 1.3-1.9 2.1" />
          <path d="M12 16.8h.01" />
        </>
      );
    case "home":
      return (
        <>
          <path d="m4 11 8-6 8 6" />
          <path d="M6.5 10.5V19h11v-8.5" />
        </>
      );
    case "image":
      return (
        <>
          <rect height="14" rx="2" width="16" x="4" y="5" />
          <path d="m7 16 3.2-3.2 2.3 2.3 2.1-2.1L18 16" />
          <circle cx="9" cy="9" r="1.2" />
        </>
      );
    case "list":
      return (
        <>
          <path d="M9 7h10" />
          <path d="M9 12h10" />
          <path d="M9 17h10" />
          <path d="M5 7h.01" />
          <path d="M5 12h.01" />
          <path d="M5 17h.01" />
        </>
      );
    case "play":
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="m10 8 6 4-6 4Z" />
        </>
      );
    case "search":
      return (
        <>
          <circle cx="11" cy="11" r="6" />
          <path d="m20 20-4.2-4.2" />
        </>
      );
    case "settings":
      return (
        <>
          <circle cx="12" cy="12" r="2.8" />
          <path d="M19 12a7 7 0 0 0-.1-1.1l2-1.5-2-3.4-2.3.8A7.7 7.7 0 0 0 15 5.3L14.6 3H9.4L9 5.3c-.6.2-1.1.5-1.6.9l-2.3-.8-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.1l-2 1.5 2 3.4 2.3-.8c.5.4 1 .7 1.6.9l.4 2.3h5.2l.4-2.3c.6-.2 1.1-.5 1.6-.9l2.3.8 2-3.4-2-1.5c.1-.3.1-.7.1-1.1Z" />
        </>
      );
    case "spark":
      return (
        <>
          <path d="m12 4 1.8 4.2L18 10l-4.2 1.8L12 16l-1.8-4.2L6 10l4.2-1.8L12 4Z" />
          <path d="m18.5 4.5.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7.7-1.6Z" />
        </>
      );
    case "sun":
      return (
        <>
          <circle cx="12" cy="12" r="3.5" />
          <path d="M12 2.5v2.2" />
          <path d="M12 19.3v2.2" />
          <path d="m5.3 5.3 1.5 1.5" />
          <path d="m17.2 17.2 1.5 1.5" />
          <path d="M2.5 12h2.2" />
          <path d="M19.3 12h2.2" />
          <path d="m5.3 18.7 1.5-1.5" />
          <path d="m17.2 6.8 1.5-1.5" />
        </>
      );
  }
}
