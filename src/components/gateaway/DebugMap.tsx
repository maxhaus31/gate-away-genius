/// <reference types="google.maps" />
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
        label: {
          text: `${index + 1}`,
          color: 'black',
        },
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
      {/* Map Container */}
      <div
        ref={mapRef}
        className="h-96 w-full rounded-lg border border-gray-300 shadow-md"
      />
    </div>
  );
};
