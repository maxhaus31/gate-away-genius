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