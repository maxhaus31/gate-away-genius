import { useState } from "react";
import { AIRPORTS, AirportCode, PassportRegion, PASSPORT_LABELS } from "@/lib/gateaway-data";
import { Loader2, AlertCircle } from "lucide-react";

interface Props {
  arrival: string;
  departure: string;
  airport: AirportCode;
  passport: PassportRegion;
  arrivalFlight?: string;
  departureFlight?: string;
  transportMode?: "transit" | "driving";
  onChange: (patch: Partial<{
    arrival: string;
    departure: string;
    airport: AirportCode;
    passport: PassportRegion;
    arrivalFlight: string;
    departureFlight: string;
    transportMode: "transit" | "driving";
  }>) => void;
  onSubmit: () => void;
}

export const PlannerForm = ({ arrival, departure, airport, passport, arrivalFlight, departureFlight, transportMode = "transit", onChange, onSubmit }: Props) => {
  const [arrivalLookupLoading, setArrivalLookupLoading] = useState(false);
  const [departureLookupLoading, setDepartureLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const lookupFlight = async (flightNumber: string, direction: "arrival" | "departure") => {
    const setLoading = direction === "arrival" ? setArrivalLookupLoading : setDepartureLookupLoading;
    setLoading(true);
    setLookupError(null);
    try {
      const response = await fetch(
        `/api/flights/lookup?flight_number=${encodeURIComponent(flightNumber)}`
      );
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Flight not found");
      }
      const data = await response.json();
      const timeField = direction === "arrival" ? "scheduled_arrival" : "scheduled_departure";
      const time = data[timeField];
      if (time) {
        // Extract HH:MM from ISO string for the time picker
        const hhmm = time.slice(11, 16);
        onChange(direction === "arrival" ? { arrival: hhmm } : { departure: hhmm });
      }
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : "Failed to look up flight");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="rounded-2xl border border-border bg-card p-6 sm:p-8"
    >
      <div className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2">
        <Field label="You land at">
          <input
            type="time"
            required
            value={arrival}
            onChange={(e) => onChange({ arrival: e.target.value })}
            className="w-full bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none [color-scheme:dark]"
          />
        </Field>
        <Field label="Your next flight leaves">
          <input
            type="time"
            required
            value={departure}
            onChange={(e) => onChange({ departure: e.target.value })}
            className="w-full bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none [color-scheme:dark]"
          />
        </Field>
        <Field label="Connecting through">
          <select
            value={airport}
            onChange={(e) => onChange({ airport: e.target.value as AirportCode })}
            className="w-full cursor-pointer appearance-none bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none"
          >
            {Object.values(AIRPORTS).map((a) => (
              <option key={a.code} value={a.code} className="bg-card text-foreground">
                {a.city} ({a.code})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Your passport">
          <select
            value={passport}
            onChange={(e) => onChange({ passport: e.target.value as PassportRegion })}
            className="w-full cursor-pointer appearance-none bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none"
          >
            {(Object.keys(PASSPORT_LABELS) as PassportRegion[]).map((p) => (
              <option key={p} value={p} className="bg-card text-foreground">
                {PASSPORT_LABELS[p].label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Arrival flight (optional)">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="e.g., KL1234"
              value={arrivalFlight || ""}
              onChange={(e) => onChange({ arrivalFlight: e.target.value })}
              className="flex-1 bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none [color-scheme:dark]"
            />
            {arrivalFlight && (
              <button
                type="button"
                onClick={() => lookupFlight(arrivalFlight, "arrival")}
                disabled={arrivalLookupLoading}
                className="px-3 py-2 text-sm bg-secondary text-foreground rounded hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {arrivalLookupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Look up"}
              </button>
            )}
          </div>
        </Field>
        <Field label="Departure flight (optional)">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="e.g., TP1835"
              value={departureFlight || ""}
              onChange={(e) => onChange({ departureFlight: e.target.value })}
              className="flex-1 bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none [color-scheme:dark]"
            />
            {departureFlight && (
              <button
                type="button"
                onClick={() => lookupFlight(departureFlight, "departure")}
                disabled={departureLookupLoading}
                className="px-3 py-2 text-sm bg-secondary text-foreground rounded hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {departureLookupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Look up"}
              </button>
            )}
          </div>
          {lookupError && (
            <div className="flex gap-2 items-start mt-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{lookupError}</span>
            </div>
          )}
        </Field>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <div>
          <label className="block text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-3">
            How do you travel?
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onChange({ transportMode: "transit" })}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                transportMode === "transit"
                  ? "bg-foreground text-background"
                  : "bg-secondary text-foreground hover:bg-secondary/80"
              }`}
            >
              🚌 Public Transport
            </button>
            <button
              type="button"
              onClick={() => onChange({ transportMode: "driving" })}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-all ${
                transportMode === "driving"
                  ? "bg-foreground text-background"
                  : "bg-secondary text-foreground hover:bg-secondary/80"
              }`}
            >
              🚗 Car/Taxi
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-col-reverse items-stretch gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-relaxed text-muted-foreground">{PASSPORT_LABELS[passport].note}</p>
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-full bg-foreground px-6 py-3 text-sm font-semibold text-background transition-opacity hover:opacity-90"
        >
          Plan my layover
        </button>
      </div>
    </form>
  );
};

const Field = ({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) => (
  <label className="block bg-card p-5 transition-colors focus-within:bg-secondary/40">
    <span className="block text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
      {label}
    </span>
    <div className="mt-2">{children}</div>
  </label>
);