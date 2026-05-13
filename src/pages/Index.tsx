import { useEffect, useState } from "react";
import { Header } from "@/components/gateaway/Header";
import { PlannerForm } from "@/components/gateaway/PlannerForm";
import { Verdict } from "@/components/gateaway/Verdict";
import { Timeline } from "@/components/gateaway/Timeline";
import { TimelineFlowchart } from "@/components/gateaway/TimelineFlowchart";
import { PlaceOptions } from "@/components/gateaway/PlaceOptions";
import { MyPlan } from "@/components/gateaway/MyPlan";
import { Suggestions } from "@/components/gateaway/Suggestions";
import { RouteMap } from "@/components/gateaway/RouteMap";
import { SimpleMap } from "@/components/gateaway/SimpleMap";
import { DebugMap } from "@/components/gateaway/DebugMap";
import { TravelTimesBreakdown } from "@/components/gateaway/TravelTimesBreakdown";
import { PersonaSelector } from "@/components/gateaway/PersonaSelector";
import { submitPlannerForm, PlanResponse, PlaceOption } from "@/api/client";
import { PlanResult as GDPlanResult, AirportCode, PassportRegion, AIRPORTS } from "@/lib/gateaway-data";
import { AlertCircle, Loader2 } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PERSONA_META: Record<string, { label: string; description: string }> = {
  food_lover: { label: "Food Lover", description: "Travels to discover local cuisine, cafés, markets, and memorable dining experiences." },
  culture_seeker: { label: "Culture Seeker", description: "Enjoys museums, history, traditions, architecture, and authentic local experiences." },
  nature_wanderer: { label: "Nature Wanderer", description: "Prefers outdoor adventures, scenic landscapes, and peaceful escapes in nature." },
  checklist_traveler: { label: "Checklist Traveler", description: "Focuses on visiting iconic landmarks and must-see attractions efficiently." },
};

// Extends gateaway-data.PlanResult with backend-only fields so components stay typed
type PlanResult = GDPlanResult & Pick<PlanResponse,
  "verdict_description" | "timeline" | "activity_itinerary" |
  "available_time_minutes" | "place_options" | "safety_buffer_breakdown"
>;

const Index = () => {
  // arrival/departure (HH:MM) are kept for the time-picker UI and Timeline display only —
  // they are NOT sent to the backend.  The backend derives times from Schiphol using the
  // flight numbers below.  Lovable redesign: replace with inbound_flight / outbound_flight inputs.
  const [arrival, setArrival] = useState("10:30");
  const [departure, setDeparture] = useState("16:15");
  const [airport, setAirport] = useState<AirportCode>("LIS");
  const [passport, setPassport] = useState<PassportRegion>("EU");
  // Renamed from arrivalFlight / departureFlight to match the backend contract
  const [inboundFlight, setInboundFlight] = useState<string>("");
  const [outboundFlight, setOutboundFlight] = useState<string>("");
  const [transportMode, setTransportMode] = useState<"transit" | "driving">("transit");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [personaPlaces, setPersonaPlaces] = useState<PlaceOption[]>([]);
  const [loadingPersonaPlaces, setLoadingPersonaPlaces] = useState(false);
  const [selectedPlaces, setSelectedPlaces] = useState<PlaceOption[]>([]);
  const [routeData, setRouteData] = useState<any>(null);
  const [calculatingRoute, setCalculatingRoute] = useState(false);

  useEffect(() => {
    if (!submitted) return;

    const fetchPlan = async () => {
      setLoading(true);
      setError(null);
      setPlan(null);
      setSelectedPersona(null);
      setSelectedPlaces([]);
      setRouteData(null);

      if (!inboundFlight || !outboundFlight) {
        setError("Please enter both inbound and outbound flight numbers.");
        setLoading(false);
        return;
      }

      try {
        const response = await submitPlannerForm({
          inbound_flight: inboundFlight,
          outbound_flight: outboundFlight,
          airport_code: airport,
          passport_region: passport,
          transport_mode: transportMode,
        });

        const adaptedPlan: PlanResult = {
          ...response,
          airport: response.airport || {
            code: airport as AirportCode,
            city: AIRPORTS[airport].city,
            name: AIRPORTS[airport].name,
            country: AIRPORTS[airport].country,
            flag: AIRPORTS[airport].flag,
            transportToCityMin: 0,
            transportLabel: "",
            reentrySecurityMin: 0,
            walkToGateMin: 0,
            checkinCutoffMin: 0,
            vibe: ""
          },
          totalMinutes: response.total_minutes,
          bufferMinutes: response.buffer_minutes,
          cityTimeMinutes: response.city_time_minutes,
          bufferBreakdown: response.buffer_breakdown,
          usableMinutes: response.usable_minutes,
          immigrationBuffer: response.immigration_buffer,
          headline: response.headline,
          message: response.verdict_description,
        };

        setPlan(adaptedPlan);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to generate plan";
        setError(message);
        setPlan(null);
      } finally {
        setLoading(false);
      }
    };

    fetchPlan();
  }, [submitted, inboundFlight, outboundFlight, airport, passport, transportMode]);

  // Fetch persona-tailored places whenever the user picks a persona
  useEffect(() => {
    if (!selectedPersona || !plan) return;

    const meta = PERSONA_META[selectedPersona];
    if (!meta) return;

    const fetchPersonaPlaces = async () => {
      setLoadingPersonaPlaces(true);
      setPersonaPlaces([]);
      setSelectedPlaces([]);
      setRouteData(null);
      try {
        const response = await fetch(`${API_BASE_URL}/api/places-for-persona`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            airport_code: airport,
            persona_key: selectedPersona,
            persona_label: meta.label,
            persona_description: meta.description,
            available_minutes: plan.cityTimeMinutes,
          }),
        });
        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Failed to fetch persona places");
        }
        const data = await response.json();
        setPersonaPlaces(data.place_options ?? []);
      } catch (err) {
        console.error("Persona places error:", err);
        // Fall back to the generic places from the plan
        setPersonaPlaces(plan.place_options ?? []);
      } finally {
        setLoadingPersonaPlaces(false);
      }
    };

    fetchPersonaPlaces();
  }, [selectedPersona]);

  // Calculate route when user clicks "Plan Trip" button
  const handlePlanTrip = async () => {
    setCalculatingRoute(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/calculate-route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          airport_code: airport,
          place_ids: selectedPlaces.map(p => p.place_id),
          place_names: selectedPlaces.map(p => p.name),
          place_coordinates: selectedPlaces.map(p => p.coordinates),
          transport_mode: transportMode,
          available_minutes: plan.cityTimeMinutes,
          time_per_place: 45,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to calculate route");
      }

      const data = await response.json();
      setRouteData(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Route calculation failed";
      console.error("Route error:", message);
      alert(`Error: ${message}`);
    } finally {
      setCalculatingRoute(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
      <Header />

      <section className="mt-16 sm:mt-24">
        <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-primary">
          Layover planner
        </p>
        <h1 className="mt-5 max-w-2xl text-4xl font-medium leading-[1.05] tracking-tight text-foreground sm:text-5xl">
          Can I leave the airport — and what should I actually do?
        </h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
          Four inputs. One straight answer. No fluff.
        </p>
      </section>

      <section className="mt-10">
        <PlannerForm
          arrival={arrival}
          departure={departure}
          airport={airport}
          passport={passport}
          arrivalFlight={inboundFlight}
          departureFlight={outboundFlight}
          transportMode={transportMode}
          onChange={(p) => {
            if (p.arrival !== undefined) setArrival(p.arrival);
            if (p.departure !== undefined) setDeparture(p.departure);
            if (p.airport !== undefined) setAirport(p.airport as AirportCode);
            if (p.passport !== undefined) setPassport(p.passport as PassportRegion);
            // PlannerForm still uses arrivalFlight/departureFlight internally;
            // map to the new inbound/outbound names for the API call
            if (p.arrivalFlight !== undefined) setInboundFlight(p.arrivalFlight);
            if (p.departureFlight !== undefined) setOutboundFlight(p.departureFlight);
            if (p.transportMode !== undefined) setTransportMode(p.transportMode);
          }}
          onSubmit={() => setSubmitted(true)}
        />
      </section>

      {/* Loading state */}
      {loading && (
        <section className="mt-6">
          <div className="rounded-2xl border border-border bg-card p-8 sm:p-10 flex items-center justify-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-muted-foreground">Generating your plan...</span>
          </div>
        </section>
      )}

      {/* Error state */}
      {error && !loading && (
        <section className="mt-6">
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 sm:p-8">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
              <div>
                <h3 className="font-semibold text-red-900">Could not generate plan</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
                <p className="mt-3 text-xs text-red-600">
                  💡 Tip: Make sure the backend is running on http://localhost:8000
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Results */}
      {plan && !loading && (
        <section className="mt-6 space-y-6">
          <Verdict plan={plan} />

          <PersonaSelector selected={selectedPersona} onSelect={setSelectedPersona} />

          {/* Place Options - revealed after persona is chosen */}
          {selectedPersona && loadingPersonaPlaces && (
            <div className="rounded-2xl border border-border bg-card p-8 sm:p-10 flex items-center justify-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span className="text-muted-foreground">Finding places for you...</span>
            </div>
          )}
          {selectedPersona && !loadingPersonaPlaces && personaPlaces.length > 0 && (
            <PlaceOptions
              places={personaPlaces}
              selectedIds={new Set(selectedPlaces.map((p) => p.place_id))}
              onPlaceSelect={(place) => {
                if (place.download_location) {
                  fetch(place.download_location, { method: "GET" }).catch(() => {});
                }
                setSelectedPlaces((prev) => [...prev, place]);
              }}
              onPlaceDeselect={(placeId) => {
                setSelectedPlaces((prev) => prev.filter((p) => p.place_id !== placeId));
                setRouteData(null);
              }}
            />
          )}

          {/* Plan Trip Button - appears when places selected */}
          {selectedPlaces.length > 0 && !routeData && (
            <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 flex flex-col items-center gap-4">
              <p className="text-sm text-muted-foreground">
                {selectedPlaces.length} place{selectedPlaces.length !== 1 ? 's' : ''} selected
              </p>
              <button
                onClick={handlePlanTrip}
                disabled={calculatingRoute}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {calculatingRoute ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Calculating route...
                  </span>
                ) : (
                  "Plan Trip"
                )}
              </button>
            </div>
          )}

          {/* Route Map - appears after route is calculated */}
          {routeData && (
            <div className="space-y-6">
              {calculatingRoute && (
                <div className="rounded-2xl border border-border bg-card p-8 sm:p-10 flex items-center justify-center gap-3">
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <span className="text-muted-foreground">Calculating route...</span>
                </div>
              )}
              {!calculatingRoute && (
                <>
                  <div className="rounded-2xl border border-border bg-card p-8 sm:p-10">
                    <TravelTimesBreakdown routeData={routeData} places={selectedPlaces} />
                  </div>
                  <DebugMap routeData={routeData} airportCode={airport} />
                </>
              )}
            </div>
          )}

          {/* My Plan - appears once user has added at least one place */}
          {selectedPlaces.length > 0 && (
            <MyPlan
              places={selectedPlaces}
              cityTimeMinutes={plan.cityTimeMinutes}
              onRemove={(id) =>
                setSelectedPlaces((prev) => prev.filter((p) => p.place_id !== id))
            }
            onMoveUp={(index) =>
              setSelectedPlaces((prev) => {
                const next = [...prev];
                [next[index - 1], next[index]] = [next[index], next[index - 1]];
                return next;
              })
            }
            onMoveDown={(index) =>
              setSelectedPlaces((prev) => {
                const next = [...prev];
                [next[index], next[index + 1]] = [next[index + 1], next[index]];
                return next;
              })
            }
          />
          )}

          {/* Activity Itinerary Flowchart — only when timeline data available */}
          {plan.activity_itinerary && (
            <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
              <h2 className="text-xl font-semibold text-foreground mb-4">Your Journey</h2>
              <TimelineFlowchart itinerary={plan.activity_itinerary} />
            </div>
          )}

          {/* Timeline — only when timeline data available */}
          {plan.timeline && (
            <Timeline plan={plan} arrival={arrival} departure={departure} />
          )}

          {/* Suggestions — only when suggestions data available */}
          {plan.suggestions && (
            <Suggestions plan={plan} />
          )}
        </section>
      )}

      <footer className="mt-20 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground">
        Prototype · Times are hardcoded estimates. Always double-check your airline's
        boarding cutoff before stepping outside the terminal.
      </footer>
    </main>
  );
};

export default Index;
