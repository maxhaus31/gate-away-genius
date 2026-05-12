import { PlanPersona } from "@/api/client";

const PERSONA_ICONS: Record<string, string> = {
  coffee_lover: "☕",
  culture_seeker: "🏛️",
  fast_traveler: "⚡",
  relaxed_discoverer: "🌿",
};

export const PersonaSelector = ({
  personas,
  selected,
  onSelect,
}: {
  personas: PlanPersona[];
  selected: string | null;
  onSelect: (key: string) => void;
}) => {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-2">
        What kind of traveller are you?
      </p>
      <p className="mb-5 text-sm text-muted-foreground">Pick one — we'll tailor your plan.</p>

      <div className="grid grid-cols-2 gap-3">
        {personas.map((persona) => {
          const isSelected = selected === persona.key;
          return (
            <button
              key={persona.key}
              type="button"
              onClick={() => onSelect(persona.key)}
              className={`flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/10 ring-1 ring-primary"
                  : "border-border bg-card hover:border-primary/40 hover:bg-secondary/40"
              }`}
            >
              <span className="text-2xl">{PERSONA_ICONS[persona.key] ?? "✈️"}</span>
              <span className="text-sm font-semibold text-foreground">{persona.label}</span>
              <span className="text-xs text-muted-foreground">{persona.description}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
