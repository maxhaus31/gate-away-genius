import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

interface Segment {
  label: string;
  minutes: number;
  kind: "buffer" | "transport" | "city";
  detail?: string;
}

export const Timeline = ({ plan, arrival, departure }: { plan: PlanResult; arrival: string; departure: string }) => {
  const transport = plan.airport.transportToCityMin;
  const cityTime = plan.cityTimeMinutes;

  const segments: Segment[] = [
    { label: "Disembark + immigration", minutes: 25 + plan.immigrationBuffer, kind: "buffer" },
  ];
  if (cityTime > 0) {
    segments.push({ label: `Train to ${plan.airport.city}`, minutes: transport, kind: "transport", detail: plan.airport.transportLabel });
    segments.push({ label: `Time in ${plan.airport.city}`, minutes: cityTime, kind: "city" });
    segments.push({ label: "Train back to airport", minutes: transport, kind: "transport" });
  } else {
    const stayMin = Math.max(0, plan.usableMinutes);
    if (stayMin > 0) segments.push({ label: "Time airside (terminal)", minutes: stayMin, kind: "city" });
  }
  segments.push({ label: "Re-entry security", minutes: plan.airport.reentrySecurityMin, kind: "buffer" });
  segments.push({ label: "Walk to gate", minutes: plan.airport.walkToGateMin, kind: "buffer" });
  segments.push({ label: "Boarding cutoff", minutes: plan.airport.checkinCutoffMin, kind: "buffer" });

  const total = segments.reduce((s, x) => s + x.minutes, 0) || 1;

  return (
    <div className="rounded-3xl border border-border bg-gradient-card p-6 shadow-card animate-fade-up sm:p-8" style={{ animationDelay: "80ms" }}>
      <div className="flex items-center justify-between">
        <h3 className="font-display text-2xl text-foreground">Your timeline</h3>
        <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {arrival || "--:--"} → {departure || "--:--"}
        </div>
      </div>

      <div className="mt-6 flex h-3 w-full overflow-hidden rounded-full bg-secondary/60">
        {segments.map((s, i) => {
          const w = (s.minutes / total) * 100;
          const cls =
            s.kind === "city"
              ? "bg-gradient-accent"
              : s.kind === "transport"
                ? "bg-primary/40"
                : "bg-muted-foreground/30";
          return <div key={i} className={cls} style={{ width: `${w}%` }} title={`${s.label} · ${formatDuration(s.minutes)}`} />;
        })}
      </div>

      <ol className="mt-6 space-y-3">
        {segments.map((s, i) => (
          <li key={i} className="flex items-start gap-4 rounded-xl border border-border/60 bg-background/30 px-4 py-3">
            <div className="mt-1 flex h-2.5 w-2.5 shrink-0 items-center justify-center">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  s.kind === "city"
                    ? "bg-primary shadow-[0_0_0_4px_hsl(var(--primary)/0.18)]"
                    : s.kind === "transport"
                      ? "bg-primary/60"
                      : "bg-muted-foreground/60"
                }`}
              />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-3">
                <p className="truncate text-sm font-medium text-foreground">{s.label}</p>
                <p className="shrink-0 text-sm tabular-nums text-muted-foreground">{formatDuration(s.minutes)}</p>
              </div>
              {s.detail && <p className="mt-0.5 text-xs text-muted-foreground">{s.detail}</p>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};