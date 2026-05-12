interface RouteData {
  itinerary: Array<{
    sequence: number;
    type: "travel" | "activity";
    from?: string;
    to?: string;
    place?: string;
    duration_minutes: number;
    distance_meters?: number;
  }>;
  timing_summary: {
    total_travel_minutes: number;
    total_activity_minutes: number;
    total_used_minutes: number;
    available_minutes: number;
    remaining_minutes: number;
  };
}

interface Props {
  routeData: RouteData;
}

const formatDuration = (minutes: number): string => {
  if (minutes === 0) return "0 min";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
};

const formatDistance = (meters?: number): string => {
  if (!meters) return "-";
  if (meters < 1000) return `${meters}m`;
  const km = (meters / 1000).toFixed(1);
  return `${km}km`;
};

export const TravelTimesBreakdown = ({ routeData }: Props) => {
  const itinerary = routeData?.itinerary || [];
  const timingSummary = routeData?.timing_summary;

  return (
    <div className="space-y-6">
      {/* Main Summary */}
      {timingSummary && (
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2">
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Travel Time
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums sm:text-4xl text-foreground">
              {formatDuration(timingSummary.total_travel_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Activity Time
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums sm:text-4xl text-primary">
              {formatDuration(timingSummary.total_activity_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Total Used
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums sm:text-4xl text-foreground">
              {formatDuration(timingSummary.total_used_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Time Remaining
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums sm:text-4xl text-muted-foreground">
              {formatDuration(timingSummary.remaining_minutes)}
            </div>
          </div>
        </div>
      )}

      {/* Itinerary Details */}
      {itinerary.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-foreground">Trip Breakdown</h3>
          <div className="space-y-2">
            {itinerary.map((item, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-4 rounded-lg border p-4 ${
                  item.type === "travel"
                    ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950"
                    : "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
                }`}
              >
                <div className="flex-1">
                  <div className="text-sm font-semibold text-foreground">
                    {item.type === "travel" ? "🚌" : "📍"}{" "}
                    {item.type === "travel"
                      ? `${item.from} → ${item.to}`
                      : item.place}
                  </div>
                  {item.distance_meters && item.type === "travel" && (
                    <div className="text-xs text-muted-foreground">
                      Distance: {formatDistance(item.distance_meters)}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className="font-semibold text-foreground">
                    {formatDuration(item.duration_minutes)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {item.type === "travel" ? "travel" : "visit"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
