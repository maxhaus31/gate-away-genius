import { useEffect, useState } from "react";
import { Header } from "@/components/gateaway/Header";
import { PlannerForm } from "@/components/gateaway/PlannerForm";
import { Verdict } from "@/components/gateaway/Verdict";
import { Timeline } from "@/components/gateaway/Timeline";
import { TimelineFlowchart } from "@/components/gateaway/TimelineFlowchart";
import { PlaceOptions } from "@/components/gateaway/PlaceOptions";
import { Suggestions } from "@/components/gateaway/Suggestions";
import { submitPlannerForm, PlanResponse, PlaceOption } from "@/api/client";
import { PlanResult as GDPlanResult, AirportCode, PassportRegion } from "@/lib/gateaway-data";
import { AlertCircle, Loader2 } from "lucide-react";

// Extends gateaway-data.PlanResult with backend-only fields so components stay typed
type PlanResult = GDPlanResult & Pick<PlanResponse,
  "verdict_description" | "timeline" | "activity_itinerary" |
  "available_time_minutes" | "place_options" | "safety_buffer_breakdown"
>;

// Helper: Convert "HH:MM" time to ISO date string for today
function timeToISO(time: string): string {
  const today = new Date().toISOString().split("T")[0];
  return `${today}T${time}:00`;
}

const Index = () => {
  const [arrival, setArrival] = useState("10:30");
  const [departure, setDeparture] = useState("16:15");
  const [airport, setAirport] = useState<AirportCode>("LIS");
  const [passport, setPassport] = useState<PassportRegion>("EU");
  const [arrivalFlight, setArrivalFlight] = useState<string>("");
  const [departureFlight, setDepartureFlight] = useState<string>("");
  const [transportMode, setTransportMode] = useState<"transit" | "driving">("transit");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [selectedPlaces, setSelectedPlaces] = useState<PlaceOption[]>([]);

  useEffect(() => {
    if (!submitted) return;

    const fetchPlan = async () => {
      setLoading(true);
      setError(null);
      setPlan(null);

      try {
        const response = await submitPlannerForm({
          arrival_time: timeToISO(arrival),
          departure_time: timeToISO(departure),
          airport_code: airport,
          passport_region: passport,
          arrival_flight: arrivalFlight || undefined,
          departure_flight: departureFlight || undefined,
          transport_mode: transportMode,
        });

        const adaptedPlan: PlanResult = {
          ...response,
          airport: { ...response.airport, code: response.airport.code as AirportCode },
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
  }, [submitted, arrival, departure, airport, passport, transportMode]);

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
          arrivalFlight={arrivalFlight}
          departureFlight={departureFlight}
          transportMode={transportMode}
          onChange={(p) => {
            if (p.arrival !== undefined) setArrival(p.arrival);
            if (p.departure !== undefined) setDeparture(p.departure);
            if (p.airport !== undefined) setAirport(p.airport as AirportCode);
            if (p.passport !== undefined) setPassport(p.passport as PassportRegion);
            if (p.arrivalFlight !== undefined) setArrivalFlight(p.arrivalFlight);
            if (p.departureFlight !== undefined) setDepartureFlight(p.departureFlight);
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
          
          {/* Place Options - Interactive selection */}
          {plan.place_options && plan.place_options.length > 0 && (
            <PlaceOptions 
              places={plan.place_options}
              onPlaceSelect={(place) => {
                // Trigger Unsplash download tracking (required by API guidelines)
                if (place.download_location) {
                  fetch(place.download_location, { method: 'GET' }).catch(() => {
                    // Silently fail - tracking is optional
                  });
                }
                
                setSelectedPlaces([...selectedPlaces, place]);
                alert(`✅ Added ${place.name} to your itinerary!`);
              }}
            />
          )}
          
          {/* Activity Itinerary Flowchart */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
            <h2 className="text-xl font-semibold text-foreground mb-4">Your Journey</h2>
            <TimelineFlowchart itinerary={plan.activity_itinerary} />
          </div>
          
          <Timeline plan={plan} arrival={arrival} departure={departure} />
          <Suggestions plan={plan} />
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
