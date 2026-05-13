import { PlanBufferBreakdown } from "@/api/client";
import { formatDuration } from "@/lib/gateaway-data";

const ROWS: { key: keyof PlanBufferBreakdown; label: string }[] = [
  { key: "exit_time_min", label: "Exit airport + immigration" },
  { key: "security_reentry_min", label: "Security re-entry" },
  { key: "walk_to_gate_min", label: "Walk to gate" },
  { key: "checkin_cutoff_min", label: "Check-in cutoff" },
];

export const BufferBreakdown = ({
  breakdown,
  usableMinutes,
}: {
  breakdown: PlanBufferBreakdown;
  usableMinutes: number;
}) => {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-5">
        How your time breaks down
      </p>

      <div className="space-y-2">
        {ROWS.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between py-1">
            <span className="text-sm text-muted-foreground">{label}</span>
            <span className="text-sm font-medium tabular-nums text-foreground">
              −{breakdown[key]} min
            </span>
          </div>
        ))}

        <div className="my-2 border-t border-border" />

        <div className="flex items-center justify-between py-1">
          <span className="text-sm font-medium text-foreground">Total buffer</span>
          <span className="text-sm font-semibold tabular-nums text-foreground">
            {formatDuration(breakdown.total_buffer_min)}
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between rounded-xl bg-primary/10 px-4 py-3">
          <span className="text-sm font-medium text-foreground">Yours to use</span>
          <span className="text-2xl font-medium tabular-nums text-primary">
            {formatDuration(usableMinutes)}
          </span>
        </div>
      </div>
    </div>
  );
};
