import type { PlanResult } from "@/lib/gateaway-data";
import { formatDuration } from "@/lib/gateaway-data";

const VERDICT_COPY = {
  safe: { label: "You're good to go", dot: "bg-success", text: "text-success-foreground", bg: "bg-success" },
  tight: { label: "Tight — but doable", dot: "bg-warning", text: "text-warning-foreground", bg: "bg-warning" },
  stay: { label: "Stay inside the airport", dot: "bg-danger", text: "text-danger-foreground", bg: "bg-danger" },
} as const;

export const Verdict = ({ plan }: { plan: PlanResult }) => {
  const v = VERDICT_COPY[plan.verdict];

  return (
    <div className="rounded-2xl border border-border bg-card p-8 sm:p-10">
      {/* Hero pill — the first thing you see */}
      <div
        className={`inline-flex items-center gap-3 rounded-full px-5 py-2.5 ${v.bg} ${v.text}`}
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full bg-current opacity-50" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
        </span>
        <span className="text-sm font-semibold tracking-tight">{v.label}</span>
      </div>

      <h2 className="mt-6 max-w-2xl text-3xl font-medium leading-[1.15] tracking-tight text-foreground sm:text-4xl">
        {plan.headline}
      </h2>
      <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
        {plan.message}
      </p>

      {/* Boarding-pass stat row */}
      <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-3">
        <Stat label="Total layover" value={formatDuration(plan.totalMinutes)} />
        <Stat label="Airport buffers" value={`−${formatDuration(plan.bufferMinutes)}`} muted />
        <Stat label="Yours in the city" value={formatDuration(plan.cityTimeMinutes)} accent />
      </div>
    </div>
  );
};

const Stat = ({
  label,
  value,
  accent,
  muted,
}: {
  label: string;
  value: string;
  accent?: boolean;
  muted?: boolean;
}) => (
  <div className="bg-card p-5">
    <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
      {label}
    </div>
    <div
      className={`mt-3 text-3xl font-medium tracking-tight tabular-nums sm:text-4xl ${
        accent ? "text-primary" : muted ? "text-muted-foreground" : "text-foreground"
      }`}
    >
      {value}
    </div>
  </div>
);