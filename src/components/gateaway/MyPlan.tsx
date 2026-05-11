import { PlaceOption } from "@/api/client";
import { X, ChevronUp, ChevronDown, Clock } from "lucide-react";

const MINUTES_PER_STOP = 45;

interface Props {
  places: PlaceOption[];
  cityTimeMinutes: number;
  onRemove: (placeId: string) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
}

export const MyPlan = ({ places, cityTimeMinutes, onRemove, onMoveUp, onMoveDown }: Props) => {
  if (places.length === 0) return null;

  const totalPlanned = places.length * MINUTES_PER_STOP;
  const isOver = totalPlanned > cityTimeMinutes;
  const fillPercent = Math.min(100, (totalPlanned / cityTimeMinutes) * 100);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-semibold text-foreground">My Plan</h2>
        <span className="text-sm text-muted-foreground">
          {places.length} stop{places.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Time bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2 text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            ~{totalPlanned} min planned
          </span>
          <span className={isOver ? "text-red-500 font-medium" : "text-green-600 font-medium"}>
            {isOver
              ? `Over by ${totalPlanned - cityTimeMinutes} min`
              : `${cityTimeMinutes - totalPlanned} min to spare`}
          </span>
        </div>
        <div className="h-2 rounded-full bg-secondary overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${isOver ? "bg-red-500" : "bg-green-500"}`}
            style={{ width: `${fillPercent}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-1.5">
          {cityTimeMinutes} min available in the city · ~{MINUTES_PER_STOP} min estimated per stop
        </p>
      </div>

      {/* Ordered place list */}
      <ol className="space-y-2">
        {places.map((place, index) => (
          <li
            key={place.place_id}
            className="flex items-center gap-3 rounded-xl border border-border bg-secondary/20 p-3"
          >
            {/* Step number */}
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-foreground text-background text-xs font-semibold flex items-center justify-center">
              {index + 1}
            </span>

            {/* Thumbnail */}
            {place.photo_url ? (
              <img
                src={place.photo_url}
                alt={place.name}
                className="h-12 w-12 rounded-lg object-cover flex-shrink-0"
              />
            ) : (
              <div className="h-12 w-12 rounded-lg bg-secondary flex-shrink-0 flex items-center justify-center text-xl">
                📍
              </div>
            )}

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm text-foreground truncate">{place.name}</p>
              <p className="text-xs text-muted-foreground">~{MINUTES_PER_STOP} min</p>
            </div>

            {/* Reorder + remove controls */}
            <div className="flex items-center gap-0.5 flex-shrink-0">
              <button
                onClick={() => onMoveUp(index)}
                disabled={index === 0}
                className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
                aria-label="Move up"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
              <button
                onClick={() => onMoveDown(index)}
                disabled={index === places.length - 1}
                className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-secondary disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
                aria-label="Move down"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => onRemove(place.place_id)}
                className="p-1.5 rounded text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors ml-1"
                aria-label="Remove from plan"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
};
