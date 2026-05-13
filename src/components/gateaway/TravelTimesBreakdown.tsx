import { useState } from "react";

interface RouteData {
  itinerary: Array<{
    sequence: number;
    type: "travel" | "activity";
    from?: string;
    to?: string;
    place?: string;
    duration_minutes: number;
    distance_meters?: number;
    transit_details?: {
      summary?: string;
      line_color?: string;
      line_text_color?: string;
      departure_stop?: string;
      arrival_stop?: string;
      segments?: Array<{
        line_name?: string;
        line_color?: string;
        line_text_color?: string;
        vehicle_name?: string;
        vehicle_type?: string;
        departure_stop?: string;
        arrival_stop?: string;
        headsign?: string;
      }>;
    };
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
  const [expandedTripIndex, setExpandedTripIndex] = useState<number | null>(null);

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
          <h3 className="text-base font-semibold text-white">Trip Breakdown</h3>
          <div className="space-y-2">
            {itinerary.map((item, idx) => {
              const isTravel = item.type === "travel";
              const isExpanded = expandedTripIndex === idx;
              const transitDetails = item.transit_details;

              return (
                <div key={idx}>
                  <button
                    type="button"
                    onClick={() => {
                      if (!isTravel) return;
                      setExpandedTripIndex(isExpanded ? null : idx);
                    }}
                    className={`flex w-full items-center gap-4 rounded-lg border p-4 text-left transition-colors ${
                      isTravel
                        ? "border-blue-200 bg-blue-50 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950 dark:hover:bg-blue-900/60"
                        : "cursor-default border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
                    }`}
                  >
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-black">
                        {item.type === "travel" ? "🚌" : "📍"}{" "}
                        {item.type === "travel"
                          ? `${item.from} → ${item.to}`
                          : item.place}
                      </div>
                      {item.distance_meters && item.type === "travel" && (
                        <div className="text-xs text-black">
                          Distance: {formatDistance(item.distance_meters)}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-black">
                        {formatDuration(item.duration_minutes)}
                      </div>
                      <div className="text-xs text-black">
                        {item.type === "travel" ? "tap for route" : "visit"}
                      </div>
                    </div>
                  </button>

                  {isTravel && isExpanded && (
                    <div className="mt-2 rounded-lg border border-border bg-card p-4 text-sm text-foreground">
                      {transitDetails ? (
                        <>
                          <div className="flex items-center gap-2 font-semibold text-foreground">
                            <span
                              className="inline-block h-3 w-3 rounded-full"
                              style={{ backgroundColor: transitDetails.line_color || "#ef4444" }}
                            />
                            <span>{transitDetails.summary || "Transit route"}</span>
                          </div>
                          <div className="mt-3 space-y-2 text-sm text-foreground/90">
                            {transitDetails.departure_stop && transitDetails.arrival_stop && (
                              <div className="rounded-md bg-muted/40 px-3 py-2">
                                {transitDetails.departure_stop} → {transitDetails.arrival_stop}
                              </div>
                            )}
                            <div className="space-y-2">
                              {(transitDetails.segments || []).map((segment, segmentIndex) => (
                                <div key={segmentIndex} className="rounded-md border border-border bg-background px-3 py-2">
                                  <div className="font-medium text-foreground">
                                    <span
                                      className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                                      style={{ backgroundColor: segment.line_color || transitDetails.line_color || "#ef4444" }}
                                    />
                                    {segment.line_name || segment.vehicle_name || "Transit"}
                                  </div>
                                  {(segment.departure_stop || segment.arrival_stop) && (
                                    <div className="mt-1 text-xs text-muted-foreground">
                                      {segment.departure_stop || "Start"} → {segment.arrival_stop || "End"}
                                    </div>
                                  )}
                                  {segment.headsign && (
                                    <div className="mt-1 text-xs text-muted-foreground">
                                      Headsign: {segment.headsign}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="text-muted-foreground">
                          Travel details are not available for this leg yet.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
