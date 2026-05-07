import { useState } from "react";
import { AIRPORTS, AirportCode, PassportRegion, PASSPORT_LABELS } from "@/lib/gateaway-data";
import { Loader2, AlertCircle } from "lucide-react";

interface Props {
  arrival: string;
  departure: string;
  airport: AirportCode;
  passport: PassportRegion;
  flightNumber?: string;
  transportMode?: "transit" | "driving";
  onChange: (patch: Partial<{ arrival: string; departure: string; airport: AirportCode; passport: PassportRegion; flightNumber?: string; transportMode?: "transit" | "driving" }>) => void;
  onSubmit: () => void;
}

export const PlannerForm = ({ arrival, departure, airport, passport, flightNumber, transportMode = "transit", onChange, onSubmit }: Props) => {
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const handleFlightLookup = async () => {
    if (!flightNumber || !airport) {
      setLookupError("Please enter a flight number and select an airport");
      return;
    }

    setLookupLoading(true);
    setLookupError(null);

    try {
      const response = await fetch(
        `/api/flights/lookup?flight_number=${encodeURIComponent(flightNumber)}&airport_code=${encodeURIComponent(airport)}`
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Flight not found");
      }

      const data = await response.json();
      
      // Auto-populate arrival time if found
      if (data.arrival) {
        onChange({ arrival: data.arrival });
        setLookupError(null);
      }
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : "Failed to look up flight");
    } finally {
      setLookupLoading(false);
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
        <Field label="Flight number (optional)">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              placeholder="e.g., BA 284"
              value={flightNumber || ""}
              onChange={(e) => onChange({ flightNumber: e.target.value })}
              className="flex-1 bg-transparent text-3xl font-medium tracking-tight text-foreground outline-none [color-scheme:dark]"
            />
            <button
              type="button"
              onClick={handleFlightLookup}
              disabled={!flightNumber || lookupLoading}
              className="px-3 py-2 text-sm bg-secondary text-foreground rounded hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
            >
              {lookupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Look up"}
            </button>
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