export type AirportCode = "LIS" | "AMS" | "SIN";
export type PassportRegion = "EU" | "US" | "OTHER";

export interface AirportInfo {
  code: AirportCode;
  city: string;
  name: string;
  country: string;
  flag: string;
  transportToCityMin: number;
  transportLabel: string;
  reentrySecurityMin: number;
  walkToGateMin: number;
  checkinCutoffMin: number;
  vibe: string;
}

export const AIRPORTS: Record<AirportCode, AirportInfo> = {
  LIS: {
    code: "LIS",
    city: "Lisbon",
    name: "Humberto Delgado",
    country: "Portugal",
    flag: "🇵🇹",
    transportToCityMin: 35,
    transportLabel: "Metro Red Line → Baixa-Chiado",
    reentrySecurityMin: 20,
    walkToGateMin: 10,
    checkinCutoffMin: 45,
    vibe: "tile-lined alleys, pastéis de nata, golden-hour viewpoints",
  },
  AMS: {
    code: "AMS",
    city: "Amsterdam",
    name: "Schiphol",
    country: "Netherlands",
    flag: "🇳🇱",
    transportToCityMin: 20,
    transportLabel: "Direct train → Centraal (every 10 min)",
    reentrySecurityMin: 30,
    walkToGateMin: 10,
    checkinCutoffMin: 45,
    vibe: "canal rings, brown cafés, bikes everywhere",
  },
  SIN: {
    code: "SIN",
    city: "Singapore",
    name: "Changi",
    country: "Singapore",
    flag: "🇸🇬",
    transportToCityMin: 30,
    transportLabel: "MRT East-West → Marina Bay",
    reentrySecurityMin: 25,
    walkToGateMin: 10,
    checkinCutoffMin: 45,
    vibe: "hawker centres, skyline gardens, late-night neon",
  },
};

export interface Suggestion {
  emoji: string;
  title: string;
  blurb: string;
  minTimeNeeded: number; // in minutes, of usable city time
}

export const SUGGESTIONS: Record<AirportCode, Suggestion[]> = {
  LIS: [
    {
      emoji: "🥐",
      title: "Pastel de Nata at Manteigaria",
      blurb: "Quick metro hop, one perfect custard tart, back before your gate even opens.",
      minTimeNeeded: 60,
    },
    {
      emoji: "🌅",
      title: "Miradouro de Santa Catarina",
      blurb: "Tiled streets, a glass of vinho verde and the best Tagus view in the city.",
      minTimeNeeded: 120,
    },
    {
      emoji: "🚋",
      title: "Tram 28 + Alfama wander",
      blurb: "Ride the iconic yellow tram, get lost in Alfama, taste a real bifana.",
      minTimeNeeded: 180,
    },
  ],
  AMS: [
    {
      emoji: "☕",
      title: "Coffee on the Singel canal",
      blurb: "Direct train to Centraal, a flat white by the water, easy turnaround.",
      minTimeNeeded: 60,
    },
    {
      emoji: "🚲",
      title: "Jordaan stroll + bitterballen",
      blurb: "Wander the prettiest neighbourhood, snack on something fried and Dutch.",
      minTimeNeeded: 120,
    },
    {
      emoji: "🖼️",
      title: "Rijksmuseum highlights tour",
      blurb: "Skip-the-line, see the Vermeer and the Rembrandt, you've earned it.",
      minTimeNeeded: 180,
    },
  ],
  SIN: [
    {
      emoji: "🌳",
      title: "Jewel Changi rainforest",
      blurb: "Don't even leave — the world's tallest indoor waterfall is right here.",
      minTimeNeeded: 45,
    },
    {
      emoji: "🍜",
      title: "Hawker lunch at Lau Pa Sat",
      blurb: "MRT downtown, satay and laksa under colonial iron, back in a flash.",
      minTimeNeeded: 120,
    },
    {
      emoji: "🌃",
      title: "Marina Bay + Gardens skyline",
      blurb: "Supertrees, the light show, a cocktail 57 floors up. Singapore in one bite.",
      minTimeNeeded: 180,
    },
  ],
};

export const PASSPORT_LABELS: Record<PassportRegion, { label: string; note: string }> = {
  EU: {
    label: "EU / Schengen",
    note: "Frictionless re-entry at Lisbon and Amsterdam.",
  },
  US: {
    label: "United States",
    note: "Visa-free short stays — expect standard immigration queues.",
  },
  OTHER: {
    label: "Other",
    note: "Add ~15 min buffer for immigration and possible visa checks.",
  },
};

export interface PlanResult {
  totalMinutes: number;
  bufferMinutes: number;
  bufferBreakdown: { label: string; minutes: number }[];
  usableMinutes: number;
  cityTimeMinutes: number; // usable minus round-trip transport
  verdict: "safe" | "tight" | "stay";
  headline: string;
  message: string;
  suggestions: Suggestion[];
  airport: AirportInfo;
  immigrationBuffer: number;
}

function parseTimeToMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function buildPlan(
  arrival: string,
  departure: string,
  airportCode: AirportCode,
  passport: PassportRegion,
): PlanResult | null {
  if (!arrival || !departure) return null;
  const airport = AIRPORTS[airportCode];
  let total = parseTimeToMinutes(departure) - parseTimeToMinutes(arrival);
  if (total <= 0) total += 24 * 60; // overnight

  const immigrationBuffer =
    passport === "EU" && (airportCode === "LIS" || airportCode === "AMS")
      ? 0
      : passport === "OTHER"
        ? 15
        : 5;

  const breakdown = [
    { label: "Disembark + immigration", minutes: 25 + immigrationBuffer },
    { label: `Re-entry security (${airport.city})`, minutes: airport.reentrySecurityMin },
    { label: "Walk to gate", minutes: airport.walkToGateMin },
    { label: "Check-in / boarding cutoff", minutes: airport.checkinCutoffMin },
  ];
  const buffer = breakdown.reduce((s, b) => s + b.minutes, 0);
  const usable = Math.max(0, total - buffer);
  const roundTripTransport = airport.transportToCityMin * 2;
  const cityTime = Math.max(0, usable - roundTripTransport);

  let verdict: PlanResult["verdict"];
  let headline: string;
  let message: string;

  if (usable < roundTripTransport + 30) {
    verdict = "stay";
    headline = "Stay airside on this one.";
    message = `By the time you cleared immigration and rode into ${airport.city}, you'd be turning right back around. Grab a proper meal in the terminal — ${airport.name} is genuinely nice — and save the city for the next layover.`;
  } else if (cityTime < 75) {
    verdict = "tight";
    headline = `Doable — pick one thing in ${airport.city} and move.`;
    message = `You've got about ${formatDuration(cityTime)} on the ground. Enough for one good thing, not three. Set an alarm for the turnaround and keep it tight.`;
  } else {
    verdict = "safe";
    headline = `You've got a solid ${formatDuration(cityTime)} in ${airport.city}.`;
    message = `Plenty of room to ${airport.vibe.split(",")[0].trim()} and still be back at your gate without a sprint. Go.`;
  }

  const suggestions = SUGGESTIONS[airportCode]
    .filter((s) => s.minTimeNeeded <= cityTime + 15)
    .slice(-3);

  return {
    totalMinutes: total,
    bufferMinutes: buffer,
    bufferBreakdown: breakdown,
    usableMinutes: usable,
    cityTimeMinutes: cityTime,
    verdict,
    headline,
    message,
    suggestions: suggestions.length ? suggestions : SUGGESTIONS[airportCode].slice(0, 1),
    airport,
    immigrationBuffer,
  };
}

export function formatDuration(min: number): string {
  if (min <= 0) return "0 min";
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}min`;
}

export function formatTime(t: string): string {
  return t || "--:--";
}