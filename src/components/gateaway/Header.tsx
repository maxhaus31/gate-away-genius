export const Header = () => (
  <header className="flex items-center justify-between">
    <div className="flex items-center gap-2.5">
      <span className="grid h-7 w-7 place-items-center rounded-md border border-border text-primary">
        {/* simple geometric mark */}
        <svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor" aria-hidden>
          <path d="M2 8 L14 8 M10 4 L14 8 L10 12" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="square" />
        </svg>
      </span>
      <span className="text-sm font-semibold tracking-tight text-foreground">
        GateAway
      </span>
    </div>
    <span className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
      Prototype · v0.1
    </span>
  </header>
);