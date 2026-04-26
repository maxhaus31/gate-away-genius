import { useMemo, useState } from "react";
import { Header } from "@/components/gateaway/Header";
import { PlannerForm } from "@/components/gateaway/PlannerForm";
import { Verdict } from "@/components/gateaway/Verdict";
import { Timeline } from "@/components/gateaway/Timeline";
import { Suggestions } from "@/components/gateaway/Suggestions";
import {
  AIRPORTS,
  AirportCode,
  PassportRegion,
  buildPlan,
} from "@/lib/gateaway-data";

const Index = () => {
  const [arrival, setArrival] = useState("10:30");
  const [departure, setDeparture] = useState("16:15");
  const [airport, setAirport] = useState<AirportCode>("AMS");
  const [passport, setPassport] = useState<PassportRegion>("EU");
  const [submitted, setSubmitted] = useState(true);

  const plan = useMemo(
    () => (submitted ? buildPlan(arrival, departure, airport, passport) : null),
    [arrival, departure, airport, passport, submitted],
  );

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <Header />

      <section className="mt-12 sm:mt-20" id="hero">
        <p className="text-xs uppercase tracking-[0.22em] text-primary">
          The honest layover planner
        </p>
        <h1 className="mt-4 max-w-3xl font-display text-5xl leading-[0.98] text-foreground sm:text-7xl">
          Can I leave the airport — and what should I actually do?
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Tell GateAway when you land and when your next flight leaves. We'll do the
          buffer math, account for your passport, and give you a straight answer —
          plus one or two ideas worth your time.
        </p>
      </section>

      <section className="mt-10" id="planner">
        <PlannerForm
          arrival={arrival}
          departure={departure}
          airport={airport}
          passport={passport}
          onChange={(p) => {
            if (p.arrival !== undefined) setArrival(p.arrival);
            if (p.departure !== undefined) setDeparture(p.departure);
            if (p.airport !== undefined) setAirport(p.airport);
            if (p.passport !== undefined) setPassport(p.passport);
            setSubmitted(true);
          }}
          onSubmit={() => setSubmitted(true)}
        />
      </section>

      {plan && (
        <section className="mt-8 space-y-6" id="result">
          <Verdict plan={plan} />
          <Timeline plan={plan} arrival={arrival} departure={departure} />
          <Suggestions plan={plan} />
        </section>
      )}

      <section className="mt-16" id="how">
        <h2 className="font-display text-3xl text-foreground">How the math works</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          {[
            {
              n: "01",
              t: "Subtract the unavoidable",
              d: "Disembark, immigration, walking, security re-entry, and the boarding cutoff. None of that is your time.",
            },
            {
              n: "02",
              t: "Subtract the round trip",
              d: "Real transit time to the city centre and back — train schedules, not Google's optimistic ETA.",
            },
            {
              n: "03",
              t: "What's left is yours",
              d: "If it's enough for something memorable, we say go. If it's not, we say stay. No fluff.",
            },
          ].map((s) => (
            <div key={s.n} className="rounded-2xl border border-border bg-gradient-card p-6">
              <div className="font-display text-3xl text-primary">{s.n}</div>
              <h3 className="mt-2 text-lg font-semibold text-foreground">{s.t}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16" id="airports">
        <h2 className="font-display text-3xl text-foreground">Airports in this prototype</h2>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          {Object.values(AIRPORTS).map((a) => (
            <div key={a.code} className="rounded-2xl border border-border bg-gradient-card p-6">
              <div className="text-2xl">{a.flag}</div>
              <h3 className="mt-2 font-display text-xl text-foreground">{a.city} ({a.code})</h3>
              <p className="mt-1 text-sm text-muted-foreground">{a.name}, {a.country}</p>
              <dl className="mt-4 space-y-1 text-xs text-muted-foreground">
                <Row k="To city" v={`${a.transportToCityMin} min`} />
                <Row k="Re-entry security" v={`${a.reentrySecurityMin} min`} />
                <Row k="Boarding cutoff" v={`${a.checkinCutoffMin} min`} />
              </dl>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-20 border-t border-border pt-6 text-xs text-muted-foreground">
        Prototype · Hardcoded transit and security values for demonstration. Always check
        live transport and your airline's boarding cutoff before leaving the terminal.
      </footer>
    </main>
  );
};

const Row = ({ k, v }: { k: string; v: string }) => (
  <div className="flex justify-between border-b border-border/60 py-1 last:border-b-0">
    <dt>{k}</dt>
    <dd className="text-foreground">{v}</dd>
  </div>
);

export default Index;
