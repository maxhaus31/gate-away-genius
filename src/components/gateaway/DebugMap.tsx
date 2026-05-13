/// <reference types="google.maps" />
import { useEffect, useRef, useState } from "react";

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
  const routePolylines = useRef<google.maps.Polyline[]>([]);
  const routeDrawToken = useRef(0);
  const [showRoute, setShowRoute] = useState(false);

  const clearRoutePolylines = () => {
    routePolylines.current.forEach((polyline) => polyline.setMap(null));
    routePolylines.current = [];
  };

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
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: '#FFD700',  // yellow background
          fillOpacity: 1,
          strokeColor: '#000000',
          strokeWeight: 1,
          scale: 14,
        },
        label: {
          text: `${index + 1}`,
          color: 'black',        // black text on yellow works well
          fontWeight: 'bold',
          fontSize: '12px',
        },
      });

      // Rich info window with coordinates
      const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 10px; font-family: monospace; font-size: 12px; color: #333;">
          <div style="font-weight: bold; margin-bottom: 8px; color: #e11d48;">${wp.name}</div>
        </div>`,
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

  useEffect(() => {
    if (!mapInstance.current || !window.google) return;

    const waypoints = routeData?.route?.waypoints || [];
    clearRoutePolylines();

    if (!showRoute || waypoints.length < 2) return;

    const directionsService = new google.maps.DirectionsService();
    const currentToken = ++routeDrawToken.current;

    const drawRoute = async () => {
      const bounds = new google.maps.LatLngBounds();
      const colors = ["#ef4444", "#f97316", "#e11d48", "#dc2626"];

      for (let index = 0; index < waypoints.length - 1; index += 1) {
        const origin = { lat: waypoints[index].lat, lng: waypoints[index].lng };
        const destination = { lat: waypoints[index + 1].lat, lng: waypoints[index + 1].lng };

        const result = await new Promise<google.maps.DirectionsResult | null>((resolve) => {
          directionsService.route(
            {
              origin,
              destination,
              travelMode: google.maps.TravelMode.TRANSIT,
            },
            (response, status) => {
              if (status === "OK" && response) {
                resolve(response);
                return;
              }

              directionsService.route(
                {
                  origin,
                  destination,
                  travelMode: google.maps.TravelMode.WALKING,
                },
                (fallbackResponse, fallbackStatus) => {
                  if (fallbackStatus === "OK" && fallbackResponse) {
                    resolve(fallbackResponse);
                  } else {
                    resolve(null);
                  }
                }
              );
            }
          );
        });

        if (currentToken !== routeDrawToken.current) return;
        if (!result?.routes?.[0]?.overview_path?.length) continue;

        const path = result.routes[0].overview_path;
        const polyline = new google.maps.Polyline({
          path,
          geodesic: true,
          strokeColor: colors[index % colors.length],
          strokeOpacity: 0.9,
          strokeWeight: 5,
          map: mapInstance.current,
        });

        routePolylines.current.push(polyline);
        path.forEach((point) => bounds.extend(point));
      }

      if (!bounds.isEmpty() && currentToken === routeDrawToken.current) {
        mapInstance.current?.fitBounds(bounds, 48);
      }
    };

    void drawRoute();

    return () => {
      routeDrawToken.current += 1;
      clearRoutePolylines();
    };
  }, [routeData, showRoute]);

  return (
    <div className="w-full space-y-4">
      {/* Map Container */}
      <div
        ref={mapRef}
        className="h-96 w-full rounded-lg border border-gray-300 shadow-md"
      />

      <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
        <div>
          <p className="text-sm font-medium text-foreground">Route overlay</p>
          <p className="text-xs text-muted-foreground">
            Draw the actual trip line on the map.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowRoute((value) => !value)}
          className="rounded-full bg-foreground px-4 py-2 text-sm font-semibold text-background transition-opacity hover:opacity-90"
        >
          {showRoute ? "Hide route" : "Show route"}
        </button>
      </div>
    </div>
  );
};
