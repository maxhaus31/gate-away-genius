import { PlanPersona } from "@/api/client";

const PERSONAS: PlanPersona[] = [
  { key: "food_lover", label: "Food Lover", description: "Travels to discover local cuisine, cafés, markets, and memorable dining experiences." },
  { key: "culture_seeker", label: "Culture Seeker", description: "Enjoys museums, history, traditions, architecture, and authentic local experiences." },
  { key: "nature_wanderer", label: "Nature Wanderer", description: "Prefers outdoor adventures, scenic landscapes, and peaceful escapes in nature." },
  { key: "checklist_traveler", label: "Checklist Traveler", description: "Focuses on visiting iconic landmarks and must-see attractions efficiently." },
];

const PERSONA_ICONS: Record<string, string> = {
  food_lover: "🍜",
  culture_seeker: "🏛️",
  nature_wanderer: "🌿",
  checklist_traveler: "✅",
};

export const PersonaSelector = ({
  selected,
  onSelect,
}: {
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
        {PERSONAS.map((persona) => {
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
