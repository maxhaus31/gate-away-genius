import { Plane } from "lucide-react";

export const Header = () => (
  <header className="flex items-center justify-between">
    <div className="flex items-center gap-2">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-accent text-primary-foreground shadow-glow">
        <Plane className="h-4 w-4 -rotate-45" />
      </span>
      <span className="font-display text-xl tracking-tight text-foreground">
        GateAway
      </span>
    </div>
    <nav className="hidden items-center gap-6 text-sm text-muted-foreground sm:flex">
      <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
      <a href="#airports" className="transition-colors hover:text-foreground">Airports</a>
      <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.14em]">
        Prototype
      </span>
    </nav>
  </header>
);