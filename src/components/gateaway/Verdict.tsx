import { CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

const VERDICT_MAP = {
  safe: { Icon: CheckCircle2, badge: "🟢 Safe to leave", token: "success" },
  tight: { Icon: AlertTriangle, badge: "🟡 Tight but possible", token: "warning" },
  stay: { Icon: ShieldAlert, badge: "🔴 Stay in the airport", token: "danger" },
} as const;

export const Verdict = ({ plan }: { plan: PlanResult }) => {
  const v = VERDICT_MAP[plan.verdict];
  const ringClass =
    plan.verdict === "safe"
      ? "from-success/30 via-success/10 to-transparent"
      : plan.verdict === "tight"
        ? "from-warning/30 via-warning/10 to-transparent"
        : "from-danger/30 via-danger/10 to-transparent";
  const badgeClass =
    plan.verdict === "safe"
      ? "bg-success/15 text-success"
      : plan.verdict === "tight"
        ? "bg-warning/15 text-warning"
        : "bg-danger/15 text-danger";

  return (
    <div className="relative overflow-hidden rounded-3xl border border-border bg-gradient-card p-8 shadow-card animate-fade-up">
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${ringClass}`} aria-hidden />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-3">
          <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${badgeClass}`}>
            <v.Icon className="h-3.5 w-3.5" />
            {v.badge}
          </span>
          <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            {plan.airport.flag} {plan.airport.city} · layover {formatDuration(plan.totalMinutes)}
          </span>
        </div>

        <h2 className="mt-5 font-display text-4xl leading-[1.05] text-foreground sm:text-5xl">
          {plan.headline}
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          {plan.message}
        </p>

        <div className="mt-7 grid grid-cols-3 gap-3">
          <Stat label="Total layover" value={formatDuration(plan.totalMinutes)} />
          <Stat label="Airport buffers" value={`–${formatDuration(plan.bufferMinutes)}`} muted />
          <Stat label="Time in the city" value={formatDuration(plan.cityTimeMinutes)} accent />
        </div>
      </div>
    </div>
  );
};

const Stat = ({ label, value, accent, muted }: { label: string; value: string; accent?: boolean; muted?: boolean }) => (
  <div className="rounded-2xl border border-border bg-background/40 p-4">
    <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
    <div className={`mt-1 font-display text-2xl sm:text-3xl ${accent ? "text-primary" : muted ? "text-muted-foreground" : "text-foreground"}`}>
      {value}
    </div>
  </div>
);