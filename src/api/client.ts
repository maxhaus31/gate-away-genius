/**
 * API Client for GateAway Genius Backend
 * 
 * Handles all communication with the backend API at http://localhost:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Request types (matches backend models.py)
 */
export interface PlannerInput {
  // Option A: manual timestamps
  arrival_time?: string;   // ISO format: "2024-05-01T10:00:00"
  departure_time?: string; // ISO format: "2024-05-01T14:00:00"

  // Option B: flight numbers (backend resolves via Schiphol)
  arrival_flight?: string;   // e.g. "KL1234"
  departure_flight?: string; // e.g. "KL5678"
  flight_date?: string;      // "YYYY-MM-DD"; defaults to today

  // Always required
  airport_code: string; // "LIS", "AMS", "SIN"
  passport_region: string; // "EU", "US", "OTHER"
  transport_mode?: "transit" | "driving";
}

/**
 * Response types (matches backend models.py)
 */
export interface TimelineSegment {
  label: string;
  duration_minutes: number;
  color: string;
}

export interface ActivityStep {
  type: "airport" | "travel" | "activity";
  emoji: string;
  title: string;
  duration_minutes: number;
  coordinates?: string;
}

export interface ActivityItinerary {
  steps: ActivityStep[];
}

export interface PlaceOption {
  place_id: string;
  name: string;
  description: string;
  rating: number;
  user_ratings_total: number;
  coordinates: string;
  address: string;
  types: string[];
  photo_url?: string;
  photographer_name?: string;  // For Unsplash attribution
  photographer_url?: string;  // Link to photographer profile with UTM params
  unsplash_url?: string;  // Link back to Unsplash with UTM params
  download_location?: string;  // Unsplash download tracking endpoint
}

export interface Activity {
  emoji: string;
  name: string;
  description: string;
  duration_minutes: number;
}

export interface AirportInfo {
  code: string;
  city: string;
  name: string;
  country: string;
  flag: string;
  transportToCityMin: number;
  transportLabel: string;
  reentrySecurityMin: number;
  walkToGateMin: number;
  checkinCutoffMin: number;
  vibe: string;
}

export interface PlanResponse {
  verdict: "safe" | "tight" | "stay";
  verdict_description: string;
  headline: string;
  timeline: TimelineSegment[];
  activity_itinerary: ActivityItinerary;
  available_time_minutes: number;
  city_time_minutes: number;
  total_minutes: number;
  buffer_minutes: number;
  usable_minutes: number;
  airport: AirportInfo;
  immigration_buffer: number;
  suggestions: Array<{
    emoji: string;
    title: string;
    blurb: string;
    minTimeNeeded: number;
  }>;
  place_options: PlaceOption[];
  safety_buffer_breakdown: Record<string, number>;
  buffer_breakdown: Array<{
    label: string;
    minutes: number;
  }>;
}

/**
 * Error response from API
 */
export interface ApiError {
  detail: string;
}

/**
 * Submit planner form to backend and get verdict
 * 
 * @param input - Flight info, airport, passport
 * @returns Plan response with verdict, timeline, suggestions
 * @throws Error if API call fails
 */
export async function submitPlannerForm(input: PlannerInput): Promise<PlanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let errorMessage = "Failed to generate plan";
    try {
      const error = (await response.json()) as ApiError;
      errorMessage = error.detail || errorMessage;
    } catch {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as PlanResponse;
}

/**
 * Check if backend is available
 * 
 * @returns true if health check passes, false otherwise
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
    });
    return response.ok;
  } catch {
    return false;
  }
}
