import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

type SegKind = "arrival" | "transport" | "city" | "security";

interface Segment {
  label: string;
  minutes: number;
  kind: SegKind;
  detail?: string;
}

const SEG_BG: Record<SegKind, string> = {
  arrival: "bg-muted-foreground/40",
  transport: "bg-primary",
  city: "bg-success",
  security: "bg-danger",
};

const SEG_DOT: Record<SegKind, string> = {
  arrival: "bg-muted-foreground/60",
  transport: "bg-primary",
  city: "bg-success",
  security: "bg-danger",
};

const SEG_LABEL: Record<SegKind, string> = {
  arrival: "Arrival buffer",
  transport: "Travel time",
  city: "City time",
  security: "Security & gate",
};

export const Timeline = ({
  plan,
  arrival,
  departure,
}: {
  plan: PlanResult;
  arrival: string;
  departure: string;
}) => {
  const transport = plan.airport.transportToCityMin;
  const cityTime = plan.cityTimeMinutes;

  const segments: Segment[] = [
    { label: "Disembark + immigration", minutes: 25 + plan.immigrationBuffer, kind: "arrival" },
  ];
  if (cityTime > 0) {
    segments.push({
      label: `Train to ${plan.airport.city}`,
      minutes: transport,
      kind: "transport",
      detail: plan.airport.transportLabel,
    });
    segments.push({ label: `Time in ${plan.airport.city}`, minutes: cityTime, kind: "city" });
    segments.push({ label: "Train back to airport", minutes: transport, kind: "transport" });
  } else {
    const stayMin = Math.max(0, plan.usableMinutes);
    if (stayMin > 0)
      segments.push({ label: "Time airside (terminal)", minutes: stayMin, kind: "city" });
  }
  segments.push({
    label: "Re-entry security",
    minutes: plan.airport.reentrySecurityMin,
    kind: "security",
  });
  segments.push({ label: "Walk to gate", minutes: plan.airport.walkToGateMin, kind: "security" });
  segments.push({
    label: "Boarding cutoff",
    minutes: plan.airport.checkinCutoffMin,
    kind: "security",
  });

  const total = segments.reduce((s, x) => s + x.minutes, 0) || 1;
  const legendKinds: SegKind[] = ["arrival", "transport", "city", "security"];

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground">
          Your timeline
        </h3>
        <div className="font-mono text-xs tabular-nums text-muted-foreground">
          {arrival || "--:--"} → {departure || "--:--"}
        </div>
      </div>

      {/* The bar — flat, segmented, no animation */}
      <div className="mt-5 flex h-2.5 w-full overflow-hidden rounded-full bg-secondary">
        {segments.map((s, i) => {
          const w = (s.minutes / total) * 100;
          return (
            <div
              key={i}
              className={SEG_BG[s.kind]}
              style={{ width: `${w}%` }}
              title={`${s.label} · ${formatDuration(s.minutes)}`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2">
        {legendKinds.map((k) => (
          <div key={k} className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${SEG_DOT[k]}`} />
            <span className="text-xs text-muted-foreground">{SEG_LABEL[k]}</span>
          </div>
        ))}
      </div>

      {/* Detailed breakdown */}
      <ol className="mt-7 divide-y divide-border border-t border-border">
        {segments.map((s, i) => (
          <li key={i} className="flex items-start gap-4 py-3.5">
            <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${SEG_DOT[s.kind]}`} />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-3">
                <p className="truncate text-sm text-foreground">{s.label}</p>
                <p className="shrink-0 font-mono text-sm tabular-nums text-muted-foreground">
                  {formatDuration(s.minutes)}
                </p>
              </div>
              {s.detail && (
                <p className="mt-0.5 text-xs text-muted-foreground">{s.detail}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};