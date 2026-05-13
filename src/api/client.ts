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
  inbound_flight:  string;  // arriving flight,  e.g. "KL1234"
  outbound_flight: string;  // departing flight, e.g. "TP1835"
  inbound_date?:   string;  // "YYYY-MM-DD"; defaults to today on backend
  outbound_date?:  string;  // "YYYY-MM-DD"; defaults to today on backend
  layover_airport: string;  // "AMS" | "LIS" | "SIN"
  passport_type:   string;  // "EU" | "US" | "OTHER"
  transport_mode?: "transit" | "driving";
}

/**
 * Response from POST /api/extract-flights
 */
export interface FlightExtractResponse {
  inbound_flight: string | null;
  outbound_flight: string | null;
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

export interface FlightInfo {
  flight_number: string;
  date: string;
  scheduled_arrival?: string;
  actual_arrival?: string;
  delay_minutes?: number;
  status: string;
  terminal: string;
  pier: string;
  scheduled_departure?: string;
}

export interface PlanFlightOverview {
  inbound:                   FlightInfo;
  outbound:                  FlightInfo;
  total_layover_minutes:     number;
  airport_buffer_minutes:    number;
  security_reentry_minutes:  number;
  transport_minutes:         number;
  city_time_minutes:         number;
}

export interface PlanPersona {
  key: string;
  label: string;
  description: string;
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
  flight_overview:          PlanFlightOverview;
  verdict:                  "safe" | "tight" | "not_possible";
  verdict_description?:     string;
  headline?:                string;
  timeline?:                TimelineSegment[];
  activity_itinerary?:      ActivityItinerary;
  available_time_minutes?:  number;
  usable_minutes?:          number;
  airport?:                 AirportInfo;
  suggestions?:             Array<{
    emoji: string;
    title: string;
    blurb: string;
    minTimeNeeded: number;
  }>;
  place_options?:           PlaceOption[];
  safety_buffer_breakdown?: Record<string, number>;
  buffer_breakdown?:        Array<{
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
 * Upload a boarding pass image or PDF and extract flight numbers.
 * Backend tries regex first; falls back to Gemini Vision if needed.
 *
 * @param file - image (JPEG/PNG) or PDF boarding pass
 * @returns inbound_flight and outbound_flight (either may be null)
 * @throws Error if extraction fails
 */
export async function extractFlightsFromFile(file: File): Promise<FlightExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/extract-flights`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = "Failed to extract flight numbers";
    try {
      const error = (await response.json()) as ApiError;
      errorMessage = error.detail || errorMessage;
    } catch {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as FlightExtractResponse;
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
