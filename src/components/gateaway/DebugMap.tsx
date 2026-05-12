import { useEffect, useRef } from "react";

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

export const DebugMap = ({ routeData, airportCode }: Props) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<google.maps.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || !window.google) return;

    const waypoints = routeData?.route?.waypoints || [];
    if (waypoints.length === 0) return;

    console.log("DEBUG: Waypoints received:", waypoints);

    const firstPoint = waypoints[0];
    
    mapInstance.current = new google.maps.Map(mapRef.current, {
      zoom: 13,
      center: { lat: firstPoint.lat, lng: firstPoint.lng },
      mapTypeControl: false,
    });

    // Add markers and debug labels
    waypoints.forEach((wp, index) => {
      const isAirport = wp.name.toLowerCase().includes("airport");
      
      const marker = new google.maps.Marker({
        position: { lat: wp.lat, lng: wp.lng },
        map: mapInstance.current,
        title: wp.name,
        label: `${index + 1}`,
      });

      // Rich info window with coordinates
      const infoWindow = new google.maps.InfoWindow({
        content: `
          <div style="padding: 12px; font-family: monospace; font-size: 12px;">
            <div style="font-weight: bold; margin-bottom: 8px;">${wp.name}</div>
            <div>Lat: ${wp.lat}</div>
            <div>Lng: ${wp.lng}</div>
            <div style="margin-top: 8px; color: #666;">Index: ${index}</div>
          </div>
        `,
      });

      marker.addListener("click", () => {
        infoWindow.open(mapInstance.current, marker);
      });

      // Auto-open first marker
      if (index === 0) {
        infoWindow.open(mapInstance.current, marker);
      }
    });

  }, [routeData]);

  return (
    <div className="w-full space-y-4">
      {/* Debug Info Panel */}
      <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4">
        <h3 className="mb-3 font-semibold text-yellow-900">🐛 DEBUG MAP</h3>
        <div className="space-y-2 text-sm text-yellow-800">
          <div><strong>Airport:</strong> {airportCode}</div>
          <div><strong>Total Waypoints:</strong> {routeData?.route?.waypoints?.length || 0}</div>
          <div><strong>Map Initialized:</strong> {mapInstance.current ? "✅ Yes" : "❌ No"}</div>
        </div>
      </div>

      {/* Coordinates Table */}
      {routeData?.route?.waypoints && routeData.route.waypoints.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">#</th>
                <th className="px-4 py-2 text-left">Place Name</th>
                <th className="px-4 py-2 text-left">Latitude</th>
                <th className="px-4 py-2 text-left">Longitude</th>
              </tr>
            </thead>
            <tbody>
              {routeData.route.waypoints.map((wp, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-2 font-semibold">{idx + 1}</td>
                  <td className="px-4 py-2">{wp.name}</td>
                  <td className="px-4 py-2 font-mono text-xs">{wp.lat.toFixed(6)}</td>
                  <td className="px-4 py-2 font-mono text-xs">{wp.lng.toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Map Container */}
      <div
        ref={mapRef}
        className="h-96 w-full rounded-lg border border-gray-300 shadow-md"
      />

      {/* Raw JSON */}
      <details className="rounded-lg border border-gray-300 p-4">
        <summary className="cursor-pointer font-semibold">Raw Route Data (JSON)</summary>
        <pre className="mt-3 overflow-x-auto rounded bg-gray-100 p-3 text-xs">
          {JSON.stringify(routeData, null, 2)}
        </pre>
      </details>
    </div>
  );
};
