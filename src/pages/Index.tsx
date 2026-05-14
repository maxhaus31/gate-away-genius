import { useEffect, useState } from "react";
import { Header } from "@/components/gateaway/Header";
import { FlightOverview } from "@/components/gateaway/FlightOverview";
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
import { FeedbackForm } from "@/components/gateaway/FeedbackForm";
import { API_BASE_URL, submitPlannerForm, PlanResponse, PlaceOption } from "@/api/client";
import { PlanResult as GDPlanResult, AirportCode, PassportRegion, AIRPORTS } from "@/lib/gateaway-data";
import { AlertCircle, Loader2 } from "lucide-react";

const PERSONA_META: Record<string, { label: string; description: string }> = {
  food_lover: { label: "Food Lover", description: "Travels to discover local cuisine, cafés, markets, and memorable dining experiences." },
  culture_seeker: { label: "Culture Seeker", description: "Enjoys museums, history, traditions, architecture, and authentic local experiences." },
  nature_wanderer: { label: "Nature Wanderer", description: "Prefers outdoor adventures, scenic landscapes, and peaceful escapes in nature." },
  checklist_traveler: { label: "Checklist Traveler", description: "Focuses on visiting iconic landmarks and must-see attractions efficiently." },
};

// Extends gateaway-data.PlanResult with backend-only fields so components stay typed
type PlanResult = GDPlanResult & Pick<PlanResponse,
  "flight_overview" | "verdict_description" | "timeline" | "activity_itinerary" |
  "available_time_minutes" | "place_options" | "safety_buffer_breakdown"
>;

const Index = () => {
  // arrival/departure (HH:MM) kept for the Timeline display only — not sent to backend
  const [arrival, setArrival] = useState("10:30");
  const [departure, setDeparture] = useState("16:15");
  const [layoverAirport, setLayoverAirport] = useState<AirportCode>("AMS");
  const [passportType, setPassportType] = useState<PassportRegion>("EU");
  const [inboundFlight, setInboundFlight] = useState<string>("");
  const [outboundFlight, setOutboundFlight] = useState<string>("");
  const [inboundDate, setInboundDate] = useState<string>("");
  const [outboundDate, setOutboundDate] = useState<string>("");
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
  const [routePlacesSnapshot, setRoutePlacesSnapshot] = useState<PlaceOption[]>([]);
  const [showRecalculateButton, setShowRecalculateButton] = useState(false);

  useEffect(() => {
    if (!submitted) return;

    const fetchPlan = async () => {
      setLoading(true);
      setError(null);
      setPlan(null);
      setSelectedPersona(null);
      setSelectedPlaces([]);
      setRouteData(null);
      setRoutePlacesSnapshot([]);
      setShowRecalculateButton(false);

      if (!inboundFlight || !outboundFlight) {
        setError("Please enter both inbound and outbound flight numbers.");
        setLoading(false);
        return;
      }

      try {
        const response = await submitPlannerForm({
          inbound_flight:  inboundFlight,
          outbound_flight: outboundFlight,
          inbound_date:    inboundDate  || undefined,
          outbound_date:   outboundDate || undefined,
          layover_airport: layoverAirport,
          passport_type:   passportType,
          transport_mode:  transportMode,
        });

        const fo = response.flight_overview;
        const cityMins = fo.city_time_minutes;
        const localVerdict: PlanResult["verdict"] =
          cityMins < 30 ? "stay" : cityMins < 90 ? "tight" : "safe";
        const adaptedPlan: PlanResult = {
          ...response,
          verdict: localVerdict,
          airport: response.airport || {
            code: layoverAirport as AirportCode,
            city: AIRPORTS[layoverAirport].city,
            name: AIRPORTS[layoverAirport].name,
            country: AIRPORTS[layoverAirport].country,
            flag: AIRPORTS[layoverAirport].flag,
            transportToCityMin: 0,
            transportLabel: "",
            reentrySecurityMin: 0,
            walkToGateMin: 0,
            checkinCutoffMin: 0,
            vibe: ""
          },
          totalMinutes:     fo.total_layover_minutes,
          bufferMinutes:    fo.airport_buffer_minutes,
          cityTimeMinutes:  fo.city_time_minutes,
          bufferBreakdown:  response.buffer_breakdown ?? [],
          usableMinutes:    response.usable_minutes ?? 0,
          immigrationBuffer: 0,
          headline:  response.headline  ?? "",
          message:   response.verdict_description ?? "",
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
  }, [submitted, inboundFlight, outboundFlight, inboundDate, outboundDate, layoverAirport, passportType, transportMode]);

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
      setRoutePlacesSnapshot([]);
      setShowRecalculateButton(false);
      try {
        const response = await fetch(`${API_BASE_URL}/api/places-for-persona`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            airport_code: layoverAirport,
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

  // Detect when selected places change after route is calculated
  useEffect(() => {
    if (!routeData) {
      setShowRecalculateButton(false);
      return;
    }

    // Check if selected places differ from the snapshot that was used for the route
    const hasChanged =
      selectedPlaces.length !== routePlacesSnapshot.length ||
      selectedPlaces.some((place, idx) => place.place_id !== routePlacesSnapshot[idx]?.place_id);

    setShowRecalculateButton(hasChanged);
  }, [selectedPlaces, routeData, routePlacesSnapshot]);

  // Calculate route when user clicks "Plan Trip" button
  const handlePlanTrip = async () => {
    setCalculatingRoute(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/calculate-route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          airport_code: layoverAirport,
          place_ids: selectedPlaces.map(p => p.place_id),
          place_names: selectedPlaces.map(p => p.name),
          place_coordinates: selectedPlaces.map(p => p.coordinates),
          transport_mode: transportMode,
          available_minutes: plan.cityTimeMinutes,
          time_per_place: 45,
          total_layover_minutes: plan.totalMinutes,
          airport_buffer_minutes: plan.bufferMinutes,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to calculate route");
      }

      const data = await response.json();
      setRouteData(data);
      setRoutePlacesSnapshot([...selectedPlaces]);
      setShowRecalculateButton(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Route calculation failed";
      console.error("Route error:", message);
      alert(`Error: ${message}`);
    } finally {
      setCalculatingRoute(false);
    }
  };

  const handleReset = () => {
    setInboundFlight("");
    setOutboundFlight("");
    setInboundDate("");
    setOutboundDate("");
    setSubmitted(false);
    setPlan(null);
    setSelectedPersona(null);
    setPersonaPlaces([]);
    setSelectedPlaces([]);
    setRouteData(null);
    setRoutePlacesSnapshot([]);
    setShowRecalculateButton(false);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
          airport={layoverAirport}
          passport={passportType}
          arrivalFlight={inboundFlight}
          departureFlight={outboundFlight}
          inboundDate={inboundDate}
          outboundDate={outboundDate}
          transportMode={transportMode}
          onChange={(p) => {
            if (p.arrival !== undefined)       setArrival(p.arrival);
            if (p.departure !== undefined)     setDeparture(p.departure);
            if (p.airport !== undefined)       setLayoverAirport(p.airport as AirportCode);
            if (p.passport !== undefined)      setPassportType(p.passport as PassportRegion);
            if (p.arrivalFlight !== undefined) setInboundFlight(p.arrivalFlight);
            if (p.departureFlight !== undefined) setOutboundFlight(p.departureFlight);
            if (p.inboundDate !== undefined)   setInboundDate(p.inboundDate);
            if (p.outboundDate !== undefined)  setOutboundDate(p.outboundDate);
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
                  💡 Tip: Make sure the backend is reachable at {API_BASE_URL}
                </p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Results */}
      {plan && !loading && (
        <section className="mt-6 space-y-6">
          <FlightOverview overview={plan.flight_overview} />
          <Verdict plan={plan} flightOverview={plan.flight_overview} />

          {plan.verdict === "stay" ? (
            <div className="rounded-2xl border border-border bg-card p-8 sm:p-10 flex flex-col gap-6">
              <div className="space-y-3">
                <p className="text-sm font-medium uppercase tracking-[0.22em] text-muted-foreground">This one's a terminal day</p>
                <p className="text-base leading-relaxed text-foreground">
                  By the time you cleared immigration and rode into {plan.airport.city}, you&apos;d be turning right back around. The maths just don&apos;t add up on this layover.
                </p>
                <p className="text-base leading-relaxed text-muted-foreground">
                  {plan.airport.name} is genuinely worth exploring — find a good spot to eat, grab a coffee, and save {plan.airport.city} for a layover where you&apos;ll actually have time to enjoy it.
                </p>
              </div>
              <button
                onClick={handleReset}
                className="self-start px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
              >
                Start planning next trip
              </button>
            </div>
          ) : (
          <>
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
              }}
            />
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

          {/* Recalculate Route Button - appears when places change after route is calculated */}
          {showRecalculateButton && routeData && !calculatingRoute && (
            <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 flex flex-col items-center gap-4">
              <p className="text-sm text-muted-foreground">
                You've updated your place selections
              </p>
              <button
                onClick={handlePlanTrip}
                disabled={calculatingRoute}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Recalculate Route
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
                  <DebugMap routeData={routeData} airportCode={layoverAirport} />
                  <FeedbackForm />
                </>
              )}
            </div>
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
          </>
          )}
        </section>
      )}

      <footer className="mt-20 border-t border-border pt-6 text-xs leading-relaxed text-muted-foreground">
        <p className="font-medium text-foreground">AI-Generated Itinerary — Disclaimer</p>
        <p className="mt-1">
          This itinerary is generated by an AI system and is provided for informational purposes only.
          GateAway accepts no liability for missed flights, incorrect transit times, or changes in local conditions.
          Always verify transport times independently and allow extra buffer time.
          You are solely responsible for returning to the airport on time.
        </p>
      </footer>
    </main>
  );
};

export default Index;
