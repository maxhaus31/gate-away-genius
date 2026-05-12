import { PlanFlightOverview } from "@/api/client";
import { formatDuration } from "@/lib/gateaway-data";

const STATUS_STYLES: Record<string, string> = {
  landed: "bg-success/20 text-success-foreground",
  scheduled: "bg-secondary text-muted-foreground",
  delayed: "bg-warning/20 text-warning-foreground",
  cancelled: "bg-danger/20 text-danger-foreground",
};

function formatDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function statusLabel(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const FlightOverview = ({ overview }: { overview: PlanFlightOverview }) => {
  const { inbound, outbound, layover_duration_minutes } = overview;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-5">
        Your flights
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Inbound */}
        <div className="rounded-xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
                Arriving
              </p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-foreground">
                {inbound.flight_number}
              </p>
              <p className="text-sm text-muted-foreground">{formatDate(inbound.date)}</p>
            </div>
            <span
              className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${
                STATUS_STYLES[inbound.status] ?? STATUS_STYLES.scheduled
              }`}
            >
              {statusLabel(inbound.status)}
            </span>
          </div>

          <div className="space-y-1 text-sm">
            {inbound.scheduled_arrival && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scheduled</span>
                <span className="font-medium tabular-nums">{inbound.scheduled_arrival}</span>
              </div>
            )}
            {inbound.actual_arrival && inbound.actual_arrival !== inbound.scheduled_arrival && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Actual</span>
                <span
                  className={`font-medium tabular-nums ${
                    (inbound.delay_minutes ?? 0) > 0 ? "text-warning-foreground" : ""
                  }`}
                >
                  {inbound.actual_arrival}
                  {(inbound.delay_minutes ?? 0) > 0 && (
                    <span className="ml-1 text-xs">(+{inbound.delay_minutes}m)</span>
                  )}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Terminal / Pier</span>
              <span className="font-medium">
                {inbound.terminal} · {inbound.pier}
              </span>
            </div>
          </div>
        </div>

        {/* Outbound */}
        <div className="rounded-xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
                Departing
              </p>
              <p className="mt-1 text-2xl font-medium tracking-tight text-foreground">
                {outbound.flight_number}
              </p>
              <p className="text-sm text-muted-foreground">{formatDate(outbound.date)}</p>
            </div>
            <span
              className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${
                STATUS_STYLES[outbound.status] ?? STATUS_STYLES.scheduled
              }`}
            >
              {statusLabel(outbound.status)}
            </span>
          </div>

          <div className="space-y-1 text-sm">
            {outbound.scheduled_departure && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scheduled</span>
                <span className="font-medium tabular-nums">{outbound.scheduled_departure}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Terminal / Pier</span>
              <span className="font-medium">
                {outbound.terminal} · {outbound.pier}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Layover duration banner */}
      <div className="mt-4 flex items-center justify-center gap-2 rounded-xl border border-border bg-secondary/40 py-3">
        <span className="text-sm text-muted-foreground">Total layover</span>
        <span className="text-sm font-semibold text-foreground">
          {formatDuration(layover_duration_minutes)}
        </span>
      </div>
    </div>
  );
};
