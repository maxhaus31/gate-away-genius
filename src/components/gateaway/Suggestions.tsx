import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

export const Suggestions = ({ plan }: { plan: PlanResult }) => {
  if (plan.verdict === "stay") {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <h3 className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground">
          Make the most of {plan.airport.name}
        </h3>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-foreground">
          Skip the city — there isn't enough runway. A long shower, a real meal, and a quiet
          corner near your gate is the smart play.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground">
          What you can actually do
        </h3>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {String(plan.suggestions.length).padStart(2, "0")}
        </span>
      </div>

      <ol className="mt-5 divide-y divide-border border-t border-border">
        {plan.suggestions.map((s, i) => (
          <li key={s.title} className="flex items-start gap-5 py-5">
            <span className="font-mono text-xs tabular-nums text-muted-foreground pt-1">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-4">
                <h4 className="text-lg font-medium leading-tight text-foreground">
                  {s.title}
                </h4>
                <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                  {formatDuration(s.minTimeNeeded)}+
                </span>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{s.blurb}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};