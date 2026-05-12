import type { SportMode } from "./api";

/** Display names for each sport key the backend understands. Single source
 * of truth on the frontend so badges, page titles, and nav all agree. */
const SPORT_DISPLAY_NAMES: Record<string, string> = {
  soccer: "Soccer",
  nfl: "NFL",
  nba: "NBA",
  mlb: "MLB",
  nhl: "NHL",
  ufc: "UFC",
};

export function sportDisplayName(sport: string): string {
  return SPORT_DISPLAY_NAMES[sport] ?? sport.toUpperCase();
}

/** Visual treatment for each engagement mode. Keep these in lock-step with
 * the SportMode enum on the backend (active/passive/off). */
export function sportModeBadgeClass(mode: SportMode): string {
  switch (mode) {
    case "active":
      return "bg-profit/20 text-profit";
    case "passive":
      return "bg-accent/15 text-accent-light";
    case "off":
      return "bg-zinc-700/40 text-zinc-400";
  }
}

export function sportModeLabel(mode: SportMode): string {
  switch (mode) {
    case "active":
      return "Active";
    case "passive":
      return "Passive";
    case "off":
      return "Off";
  }
}
