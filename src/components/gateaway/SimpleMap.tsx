import { useEffect, useRef } from "react";
import { MapPin, Clock } from "lucide-react";

interface RouteData {
  route: {
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

export const SimpleMap = ({ routeData, airportCode }: Props) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<google.maps.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || !window.google) return;

    // Initialize map centered on first waypoint
    const waypoints = routeData?.route?.waypoints || [];
    if (waypoints.length === 0) return;

    const firstPoint = waypoints[0];
    
    mapInstance.current = new google.maps.Map(mapRef.current, {
      zoom: 12,
      center: { lat: firstPoint.lat, lng: firstPoint.lng },
      mapTypeControl: false,
    });

    // Add markers for each waypoint
    waypoints.forEach((wp, index) => {
      const isAirport = wp.name.includes("Airport");
      const color = isAirport ? "8B5CF6" : index === 0 ? "3B82F6" : "10B981"; // Purple for airport, blue for first, green for others

      const marker = new google.maps.Marker({
        position: { lat: wp.lat, lng: wp.lng },
        map: mapInstance.current,
        title: wp.name,
        icon: `http://maps.google.com/mapfiles/ms/micons/${isAirport ? "purple" : index === 0 ? "blue" : "green"}-dot.png`,
      });

      // Add info window on click
      const infoWindow = new google.maps.InfoWindow({
        content: `<div style="padding: 8px; color: black;"><strong style="color: black;">${wp.name}</strong></div>`,
      });

      marker.addListener("click", () => {
        infoWindow.open(mapInstance.current, marker);
      });
    });

  }, [routeData]);

  const { timing_summary: timing } = routeData;

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins === 0 ? `${hours}h` : `${hours}h ${mins}m`;
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-6">
      {/* Map */}
      <div className="rounded-lg overflow-hidden border border-border h-96 bg-muted" ref={mapRef} />

      {/* Timing Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
          <p className="text-xs text-muted-foreground mb-1">Travel Time</p>
          <p className="text-lg font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {formatDuration(timing.total_travel_minutes)}
          </p>
        </div>

        <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-3 border border-green-200 dark:border-green-800">
          <p className="text-xs text-muted-foreground mb-1">At Places</p>
          <p className="text-lg font-semibold text-green-600 dark:text-green-400 flex items-center gap-1">
            <MapPin className="w-4 h-4" />
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
    </div>
  );
};
