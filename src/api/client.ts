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
  arrival_time: string; // ISO format: "2024-05-01T10:00:00"
  departure_time: string; // ISO format: "2024-05-01T14:00:00"
  airport_code: string; // "LIS", "AMS", "SIN"
  passport_region: string; // "EU", "US", "OTHER"
  flight_number?: string; // Optional flight number for lookup
  transport_mode?: "transit" | "driving"; // "transit" for public transport, "driving" for car/taxi
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

export interface Activity {
  emoji: string;
  name: string;
  description: string;
  duration_minutes: number;
}

export interface PlanResponse {
  verdict: "safe" | "tight" | "stay";
  verdict_description: string;
  headline: string;
  timeline: TimelineSegment[];
  activity_itinerary: ActivityItinerary;
  available_time_minutes: number;
  city_time_minutes: number;
  suggestions: Array<{
    emoji: string;
    title: string;
    blurb: string;
    minTimeNeeded: number;
  }>;
  safety_buffer_breakdown: Record<string, number>;
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
