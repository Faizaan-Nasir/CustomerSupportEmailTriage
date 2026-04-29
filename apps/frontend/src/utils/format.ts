export function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }

  return value
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function parseUtcTimestamp(value: string): Date {
  const trimmed = value.trim();
  const normalizedFractional = trimmed.replace(/(\.\d{3})\d+/, "$1");
  const hasTimezone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(normalizedFractional);
  const normalized = hasTimezone ? normalizedFractional : `${normalizedFractional}Z`;
  return new Date(normalized);
}

export function formatRelativeTime(value: string): string {
  const date = parseUtcTimestamp(value);
  let deltaMs = date.getTime() - Date.now();

  // If the time is in the future (due to clock skew between client/server),
  // or extremely recent (less than 10 seconds ago), return "just now".
  if (deltaMs > -10000) {
    return "just now";
  }

  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

  const intervals: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 1000 * 60 * 60 * 24 * 365],
    ["month", 1000 * 60 * 60 * 24 * 30],
    ["day", 1000 * 60 * 60 * 24],
    ["hour", 1000 * 60 * 60],
    ["minute", 1000 * 60],
  ];

  for (const [unit, size] of intervals) {
    if (Math.abs(deltaMs) >= size) {
      return formatter.format(Math.round(deltaMs / size), unit);
    }
  }

  return "just now";
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
}

export function getUrgencyMeta(score: number) {
  if (score >= 0.7) {
    return {
      label: "High",
      tone: "high" as const,
    };
  }

  if (score >= 0.4) {
    return {
      label: "Med",
      tone: "medium" as const,
    };
  }

  return {
    label: "Low",
    tone: "low" as const,
  };
}

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

/**
 * Returns true if the text contains Arabic characters.
 */
export function isArabic(text: string | null | undefined): boolean {
  if (!text) return false;
  const arabicPattern = /[\u0600-\u06FF]/;
  return arabicPattern.test(text);
}

/**
 * Returns a style object with RTL direction and right alignment if Arabic is detected.
 */
export function getRtlStyle(text: string | null | undefined): React.CSSProperties {
  if (isArabic(text)) {
    return {
      direction: "rtl",
      textAlign: "right",
      fontFamily: "Source Sans Pro, Arial, sans-serif",
    };
  }
  return {};
}
