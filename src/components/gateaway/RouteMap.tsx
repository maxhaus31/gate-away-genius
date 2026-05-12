import { useState, useEffect } from "react";
import { AlertCircle, MapPin, Clock, Navigation } from "lucide-react";

interface RouteData {
  route: {
    total_distance_meters: number;
    total_duration_minutes: number;
    legs: Array<{
      from_place: string;
      to_place: string;
      distance_meters: number;
      duration_minutes: number;
    }>;
    polyline?: string;
    waypoints: Array<{
      lat: number;
      lng: number;
      name: string;
    }>;
  };
  itinerary: Array<{
    sequence: number;
    type: "travel" | "activity";
    from?: string;
    to?: string;
    place?: string;
    duration_minutes: number;
    cumulative_minutes: number;
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
  airportCode: string;
}

export const RouteMap = ({ routeData, airportCode }: Props) => {
  const [mapUrl, setMapUrl] = useState<string>("");

  useEffect(() => {
    // Build Google Maps Embed URL from waypoints
    if (routeData.route.waypoints && routeData.route.waypoints.length > 0) {
      const waypoints = routeData.route.waypoints;
      
      // Format: waypoint1|waypoint2|waypoint3
      const waypointStrs = waypoints
        .map(wp => `${wp.lat},${wp.lng}`)
        .join("|");
      
      // Use Google Maps Embed API (requires API key in VITE_GOOGLE_MAPS_API_KEY)
      const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
      if (apiKey) {
        const url = `https://www.google.com/maps/embed/v1/directions?key=${apiKey}&origin=${waypoints[0].lat},${waypoints[0].lng}&destination=${waypoints[waypoints.length - 1].lat},${waypoints[waypoints.length - 1].lng}&waypoints=${waypoints.slice(1, -1).map(wp => `${wp.lat},${wp.lng}`).join("|")}&mode=transit`;
        setMapUrl(url);
      }
    }
  }, [routeData]);

  const { timing_summary: timing, route } = routeData;

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const formatDistance = (meters: number) => {
    if (meters < 1000) return `${meters}m`;
    return `${(meters / 1000).toFixed(1)}km`;
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-6">
      {/* Map */}
      <div className="rounded-lg overflow-hidden border border-border">
        {mapUrl ? (
          <iframe
            width="100%"
            height="400"
            frameBorder="0"
            src={mapUrl}
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="w-full"
          />
        ) : (
          <div className="w-full h-96 bg-muted flex items-center justify-center flex-col gap-2 text-muted-foreground">
            <MapPin className="w-6 h-6" />
            <p>Map loading...</p>
            <p className="text-xs">Make sure VITE_GOOGLE_MAPS_API_KEY is configured</p>
          </div>
        )}
      </div>

      {/* Timing Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
          <p className="text-xs text-muted-foreground mb-1">Travel Time</p>
          <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
            {formatDuration(timing.total_travel_minutes)}
          </p>
        </div>

        <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
          <p className="text-xs text-muted-foreground mb-1">Activity Time</p>
          <p className="text-lg font-semibold text-green-600 dark:text-green-400">
            {formatDuration(timing.total_activity_minutes)}
          </p>
        </div>

        <div className="bg-orange-50 dark:bg-orange-950/20 rounded-lg p-3 border border-orange-200 dark:border-orange-800">
          <p className="text-xs text-muted-foreground mb-1">Total Used</p>
          <p className="text-lg font-semibold text-orange-600 dark:text-orange-400">
            {formatDuration(timing.total_used_minutes)}
          </p>
        </div>

        <div className={`rounded-lg p-3 border ${
          timing.remaining_minutes >= 30
            ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
            : timing.remaining_minutes >= 0
            ? "bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800"
            : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800"
        }`}>
          <p className="text-xs text-muted-foreground mb-1">Remaining</p>
          <p className={`text-lg font-semibold ${
            timing.remaining_minutes >= 30
              ? "text-green-600 dark:text-green-400"
              : timing.remaining_minutes >= 0
              ? "text-yellow-600 dark:text-yellow-400"
              : "text-red-600 dark:text-red-400"
          }`}>
            {formatDuration(Math.max(0, timing.remaining_minutes))}
          </p>
        </div>
      </div>

      {/* Detailed Itinerary */}
      <div className="space-y-3">
        <h3 className="font-semibold text-foreground flex items-center gap-2">
          <Clock className="w-4 h-4" />
          Detailed Itinerary
        </h3>

        <div className="space-y-2">
          {routeData.itinerary.map((item, idx) => (
            <div key={idx} className="flex items-start gap-4 pb-3 border-b border-border last:border-b-0">
              <div className="flex-shrink-0">
                {item.type === "travel" ? (
                  <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Navigation className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <MapPin className="w-4 h-4 text-green-600 dark:text-green-400" />
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                {item.type === "travel" ? (
                  <>
                    <p className="text-sm font-medium text-foreground">
                      Travel: {item.from} → {item.to}
                    </p>
                    <div className="flex items-center gap-4 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {formatDuration(item.duration_minutes)}
                      </span>
                      {item.distance_meters && (
                        <span className="text-xs text-muted-foreground">
                          {formatDistance(item.distance_meters)}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-foreground">
                      Visit: {item.place}
                    </p>
                    <span className="text-xs text-muted-foreground">
                      {formatDuration(item.duration_minutes)}
                    </span>
                  </>
                )}
              </div>

              <div className="flex-shrink-0 text-right">
                <p className="text-xs font-medium text-muted-foreground">
                  +{formatDuration(item.cumulative_minutes)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Route Summary */}
      <div className="bg-muted/50 rounded-lg p-4 space-y-2">
        <p className="text-sm font-medium text-foreground">Route Summary</p>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-muted-foreground">Total Distance:</span>
            <p className="font-medium">{formatDistance(route.total_distance_meters)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Total Travel:</span>
            <p className="font-medium">{formatDuration(route.total_duration_minutes)}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Stops:</span>
            <p className="font-medium">{route.legs.length} legs</p>
          </div>
          <div>
            <span className="text-muted-foreground">Available:</span>
            <p className="font-medium">{formatDuration(timing.available_minutes)}</p>
          </div>
        </div>
      </div>

      {/* Warning if not enough time */}
      {timing.remaining_minutes < 0 && (
        <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-900 dark:text-red-400">
              Not enough time!
            </p>
            <p className="text-xs text-red-800 dark:text-red-500 mt-1">
              This route requires {formatDuration(Math.abs(timing.remaining_minutes))} more than available. 
              Consider fewer or closer places.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
