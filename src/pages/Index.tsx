import { useMemo, useState } from "react";
import { Header } from "@/components/gateaway/Header";
import { PlannerForm } from "@/components/gateaway/PlannerForm";
import { Verdict } from "@/components/gateaway/Verdict";
import { Timeline } from "@/components/gateaway/Timeline";
import { Suggestions } from "@/components/gateaway/Suggestions";
import {
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
        <section className="mt-6 space-y-6">
          <Verdict plan={plan} />
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
