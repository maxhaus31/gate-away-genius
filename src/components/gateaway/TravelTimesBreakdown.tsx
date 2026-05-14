import { useState } from "react";
import { PlaceOption } from "@/api/client";

interface RouteData {
  itinerary: Array<{
    sequence: number;
    type: "travel" | "activity";
    from?: string;
    to?: string;
    place?: string;
    duration_minutes: number;
    cumulative_minutes?: number;
    distance_meters?: number;
    transit_details?: {
      summary?: string;
      line_color?: string;
      line_text_color?: string;
      departure_stop?: string;
      arrival_stop?: string;
      headsign?: string;
      trip_short_text?: string;
      segments?: Array<{
        line_name?: string;
        line_color?: string;
        line_text_color?: string;
        vehicle_name?: string;
        vehicle_type?: string;
        departure_stop?: string;
        arrival_stop?: string;
        headsign?: string;
        trip_short_text?: string;
        departure_time?: string;
        arrival_time?: string;
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
  places?: PlaceOption[];
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
  return `${(meters / 1000).toFixed(1)}km`;
};

export const TravelTimesBreakdown = ({ routeData, places = [] }: Props) => {
  const itinerary = routeData?.itinerary || [];
  const timingSummary = routeData?.timing_summary;
  const [expandedTripIndex, setExpandedTripIndex] = useState<number | null>(null);

  const placeByName = new Map(
    places.map((place) => [place.name.trim().toLowerCase(), place]),
  );

  const getPlaceDetails = (name?: string) => {
    if (!name) return null;

    const normalizedName = name
      .replace(/^airport \(return\)$/i, "Airport")
      .trim()
      .toLowerCase();

    return placeByName.get(normalizedName) || null;
  };

  const routeWaypoints = (routeData as any)?.route?.waypoints || [];

  const displayItinerary =
    itinerary.length > 0
      ? itinerary
      : routeWaypoints.length > 1
        ? routeWaypoints.flatMap(
            (
              waypoint: { name?: string },
              index: number,
              allWaypoints: Array<{ name?: string }>,
            ) => {
              if (index === allWaypoints.length - 1) {
                return [];
              }

              const nextWaypoint = allWaypoints[index + 1];
              const fromName = waypoint.name || "Start";
              const toName = nextWaypoint?.name || "Next stop";
              const placeDetails = getPlaceDetails(toName) || getPlaceDetails(fromName);

              return [
                {
                  sequence: index * 2 + 1,
                  type: "travel" as const,
                  from: fromName,
                  to: toName,
                  duration_minutes: 0,
                  distance_meters: undefined,
                },
                {
                  sequence: index * 2 + 2,
                  type: "activity" as const,
                  place: placeDetails?.name || toName,
                  duration_minutes: 45,
                },
              ];
            },
          )
      : [];

  return (
    <div className="space-y-6">
      {timingSummary && (
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2">
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
              Travel Time
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums text-foreground sm:text-4xl">
              {formatDuration(timingSummary.total_travel_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-foreground">
              Activity Time
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums text-primary sm:text-4xl">
              {formatDuration(timingSummary.total_activity_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-foreground">
              Total Used
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums text-foreground sm:text-4xl">
              {formatDuration(timingSummary.total_used_minutes)}
            </div>
          </div>
          <div className="bg-card p-5">
            <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-foreground">
              Time Remaining
            </div>
            <div className="mt-3 text-3xl font-medium tracking-tight tabular-nums text-muted-foreground sm:text-4xl">
              {formatDuration(timingSummary.remaining_minutes)}
            </div>
          </div>
        </div>
      )}

      {displayItinerary.length > 0 && (
        <div className="space-y-3">
          <div>
            <h3 className="text-base font-semibold text-foreground">Trip Breakdown</h3>
            <p className="text-sm text-muted-foreground">
              Travel legs and place stops shown in the exact order they happen.
            </p>
          </div>

          <div className="space-y-2">
            {displayItinerary.map((item, idx) => {
              const isTravel = item.type === "travel";
              const isExpanded = expandedTripIndex === idx;
              const transitDetails = item.transit_details;
              const placeDetails = !isTravel ? getPlaceDetails(item.place) : null;
              const title = isTravel
                ? `${item.from || "Start"} → ${item.to || "Next stop"}`
                : placeDetails?.name || item.place || "Place stop";

              return (
                <div key={idx}>
                  <button
                    type="button"
                    onClick={() => {
                      if (!isTravel || !item.transit_details) return;
                      setExpandedTripIndex(isExpanded ? null : idx);
                    }}
                    className={`flex w-full items-start gap-4 rounded-lg border p-4 text-left transition-colors ${
                      isTravel
                      ? "border-blue-950 bg-[#141831]"
                      : "cursor-default border-zinc-700 bg-zinc-800/60 dark:border-zinc-700 dark:bg-zinc-800/60"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-white">
                        {isTravel ? "🚇" : "⭐"} {title}
                      </div>

                      {isTravel ? (
                        <>
                          {item.distance_meters && (
                            <div className="mt-1 text-xs text-zinc-300">
                              Distance: {formatDistance(item.distance_meters)}
                            </div>
                          )}
                          {item.transit_details ? (
                            <div className="mt-1 text-xs text-zinc-300">
                              Tap to view transit details
                            </div>
                          ) : (
                            <div className="mt-1 text-xs text-zinc-300">
                              Detailed transit steps are not available yet.
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          {placeDetails?.description && (
                            <p className="mt-1 text-sm text-zinc-300">
                              {placeDetails.description}
                            </p>
                          )}
                          {placeDetails?.address && (
                            <p className="mt-2 text-xs text-zinc-400">
                              📍 {placeDetails.address}
                            </p>
                          )}
                        </>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-right">
                      <div className="mfont-semibold text-white">
                        {formatDuration(item.duration_minutes)}
                      </div>
                      <div className="text-xs text-zinc-300">
                        {isTravel ? "travel" : "visit"}
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
                            {(transitDetails.trip_short_text || transitDetails.headsign) && (
                              <div className="rounded-md bg-muted/40 px-3 py-2">
                                {transitDetails.trip_short_text && (
                                  <span className="font-medium">Trip {transitDetails.trip_short_text}</span>
                                )}
                                {transitDetails.trip_short_text && transitDetails.headsign && <span> · </span>}
                                {transitDetails.headsign && (
                                  <span>Headsign: {transitDetails.headsign}</span>
                                )}
                              </div>
                            )}

                            {transitDetails.departure_stop && transitDetails.arrival_stop && (
                              <div className="rounded-md bg-muted/40 px-3 py-2">
                                {transitDetails.departure_stop} → {transitDetails.arrival_stop}
                              </div>
                            )}

                            {transitDetails.arrival_stop && (
                              <div className="rounded-md border border-dashed border-border px-3 py-2">
                                Get off at <span className="font-semibold">{transitDetails.arrival_stop}</span>
                              </div>
                            )}

                            <div className="space-y-2">
                              {(transitDetails.segments || []).map((segment, segmentIndex) => (
                                <div
                                  key={segmentIndex}
                                  className="rounded-md border border-border bg-background px-3 py-2"
                                >
                                  <div className="font-medium text-foreground">
                                    <span
                                      className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                                      style={{
                                        backgroundColor:
                                          segment.line_color || transitDetails.line_color || "#ef4444",
                                      }}
                                    />
                                    {segment.line_name || segment.vehicle_name || "Transit"}
                                  </div>
                                  {(segment.trip_short_text || segment.headsign) && (
                                    <div className="mt-1 text-xs text-muted-foreground">
                                      {segment.trip_short_text && <span>Trip {segment.trip_short_text}</span>}
                                      {segment.trip_short_text && segment.headsign && <span> · </span>}
                                      {segment.headsign && <span>{segment.headsign}</span>}
                                    </div>
                                  )}
                                  {(segment.departure_stop || segment.arrival_stop) && (
                                    <div className="mt-1 text-xs text-foreground">
                                      {segment.departure_stop || "Start"} → {segment.arrival_stop || "End"}
                                    </div>
                                  )}
                                  {(segment.departure_time || segment.arrival_time) && (
                                    <div className="mt-1 text-xs text-muted-foreground">
                                      {segment.departure_time || ""}
                                      {segment.departure_time && segment.arrival_time ? " → " : ""}
                                      {segment.arrival_time || ""}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="text-foreground">
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
