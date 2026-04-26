import { Plane, PlaneLanding, PlaneTakeoff, MapPin, BookUser } from "lucide-react";
import { AIRPORTS, AirportCode, PassportRegion, PASSPORT_LABELS } from "@/lib/gateaway-data";

interface Props {
  arrival: string;
  departure: string;
  airport: AirportCode;
  passport: PassportRegion;
  onChange: (patch: Partial<{ arrival: string; departure: string; airport: AirportCode; passport: PassportRegion }>) => void;
  onSubmit: () => void;
}

export const PlannerForm = ({ arrival, departure, airport, passport, onChange, onSubmit }: Props) => {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="rounded-3xl border border-border bg-gradient-card p-6 shadow-card sm:p-8"
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <Field icon={<PlaneLanding className="h-4 w-4" />} label="You land at">
          <input
            type="time"
            required
            value={arrival}
            onChange={(e) => onChange({ arrival: e.target.value })}
            className="w-full bg-transparent text-2xl font-semibold tracking-tight text-foreground outline-none [color-scheme:dark]"
          />
        </Field>
        <Field icon={<PlaneTakeoff className="h-4 w-4" />} label="Your next flight leaves">
          <input
            type="time"
            required
            value={departure}
            onChange={(e) => onChange({ departure: e.target.value })}
            className="w-full bg-transparent text-2xl font-semibold tracking-tight text-foreground outline-none [color-scheme:dark]"
          />
        </Field>
        <Field icon={<MapPin className="h-4 w-4" />} label="Connecting through">
          <select
            value={airport}
            onChange={(e) => onChange({ airport: e.target.value as AirportCode })}
            className="w-full cursor-pointer appearance-none bg-transparent text-2xl font-semibold tracking-tight text-foreground outline-none"
          >
            {Object.values(AIRPORTS).map((a) => (
              <option key={a.code} value={a.code} className="bg-card text-foreground">
                {a.flag}  {a.city} ({a.code})
              </option>
            ))}
          </select>
        </Field>
        <Field icon={<BookUser className="h-4 w-4" />} label="Your passport">
          <select
            value={passport}
            onChange={(e) => onChange({ passport: e.target.value as PassportRegion })}
            className="w-full cursor-pointer appearance-none bg-transparent text-2xl font-semibold tracking-tight text-foreground outline-none"
          >
            {(Object.keys(PASSPORT_LABELS) as PassportRegion[]).map((p) => (
              <option key={p} value={p} className="bg-card text-foreground">
                {PASSPORT_LABELS[p].label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="mt-6 flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">{PASSPORT_LABELS[passport].note}</p>
        <button
          type="submit"
          className="group inline-flex items-center justify-center gap-2 rounded-full bg-gradient-accent px-6 py-3 text-sm font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02] active:scale-[0.99]"
        >
          <Plane className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
          Plan my layover
        </button>
      </div>
    </form>
  );
};

const Field = ({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) => (
  <label className="group relative block rounded-2xl border border-border bg-secondary/40 p-4 transition-colors duration-300 focus-within:border-primary/60 hover:border-primary/40">
    <span className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
      <span className="text-primary">{icon}</span>
      {label}
    </span>
    <div className="mt-2">{children}</div>
  </label>
);