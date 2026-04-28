export function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }

  return value
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

export function formatRelativeTime(value: string): string {
  const date = new Date(value);
  const deltaMs = date.getTime() - Date.now();
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
