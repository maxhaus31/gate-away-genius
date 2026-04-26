import { ArrowUpRight, Clock } from "lucide-react";
import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

export const Suggestions = ({ plan }: { plan: PlanResult }) => {
  if (plan.verdict === "stay") {
    return (
      <div
        className="rounded-3xl border border-border bg-gradient-card p-6 shadow-card animate-fade-up sm:p-8"
        style={{ animationDelay: "160ms" }}
      >
        <h3 className="font-display text-2xl text-foreground">Make the most of {plan.airport.name}</h3>
        <p className="mt-2 text-muted-foreground">
          Skip the city — there isn't enough runway. A long shower, a real meal, and a quiet
          corner near your gate is the smart play.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-3xl border border-border bg-gradient-card p-6 shadow-card animate-fade-up sm:p-8"
      style={{ animationDelay: "160ms" }}
    >
      <div className="flex items-end justify-between">
        <h3 className="font-display text-2xl text-foreground">What you can actually do</h3>
        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {plan.suggestions.length} ideas
        </span>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {plan.suggestions.map((s) => (
          <article
            key={s.title}
            className="group relative overflow-hidden rounded-2xl border border-border bg-background/40 p-5 transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-glow"
          >
            <div className="text-3xl">{s.emoji}</div>
            <h4 className="mt-3 font-display text-xl leading-tight text-foreground">{s.title}</h4>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.blurb}</p>
            <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                {formatDuration(s.minTimeNeeded)} sweet spot
              </span>
              <ArrowUpRight className="h-4 w-4 text-primary opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
};