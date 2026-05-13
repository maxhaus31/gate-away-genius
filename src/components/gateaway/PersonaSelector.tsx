import { PlanPersona } from "@/api/client";

const PERSONAS: PlanPersona[] = [
  { key: "food_lover", label: "Food Lover", description: "Travels to discover local cuisine, cafés, markets, and memorable dining experiences." },
  { key: "culture_seeker", label: "Culture Seeker", description: "Enjoys museums, history, traditions, architecture, and authentic local experiences." },
  { key: "nature_wanderer", label: "Nature Wanderer", description: "Prefers outdoor adventures, scenic landscapes, and peaceful escapes in nature." },
  { key: "checklist_traveler", label: "Checklist Traveler", description: "Focuses on visiting iconic landmarks and must-see attractions efficiently." },
];

const PERSONA_ICONS: Record<string, string> = {
  food_lover: "/avatars/foodlover1.png",
  culture_seeker: "/avatars/cultureseeker1.png",
  nature_wanderer: "/avatars/naturewanderer1.png",
  checklist_traveler: "/avatars/checklisttraveler1.png",
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
              className={`flex flex-row items-center gap-4 rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/10 ring-1 ring-primary"
                  : "border-border bg-card hover:border-primary/40 hover:bg-secondary/40"
              }`}
            >
              <img 
                src={PERSONA_ICONS[persona.key]} 
                alt={persona.label}
                className="w-20 h-20 flex-shrink-0 object-cover rounded"
              />
              <div className="flex-1 flex flex-col gap-1">
                <span className="text-sm font-semibold text-foreground">{persona.label}</span>
                <span className="text-xs text-muted-foreground">{persona.description}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
