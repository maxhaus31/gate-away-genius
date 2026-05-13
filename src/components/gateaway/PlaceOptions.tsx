import { PlaceOption } from "@/api/client";
import { Star, ExternalLink, CheckCircle2, X } from "lucide-react";

interface Props {
  places: PlaceOption[];
  selectedIds: Set<string>;
  onPlaceSelect: (place: PlaceOption) => void;
  onPlaceDeselect: (placeId: string) => void;
}

export const PlaceOptions = ({ places, selectedIds, onPlaceSelect, onPlaceDeselect }: Props) => {
  if (!places || places.length === 0) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-foreground">
          Popular Places to Visit
        </h2>
        <div className="text-sm font-medium text-muted-foreground">
          Selected: {selectedIds.size}
        </div>
      </div>
      <p className="text-sm text-muted-foreground mb-6">
        Click to add places for your route (~45 min per place)
      </p>
      
      <div className="grid gap-3">
        {places.map((place) => {
          const isAdded = selectedIds.has(place.place_id);
          
          return (
            <button
              key={place.place_id}
              onClick={() => !isAdded && onPlaceSelect(place)}
              disabled={isAdded}
              className={`group relative overflow-hidden rounded-xl border bg-card text-left transition-all ${
                isAdded
                  ? "border-green-500 opacity-100 bg-green-50 dark:bg-green-950/20 cursor-default"
                  : "border-border hover:border-primary hover:shadow-md hover:bg-secondary/20 cursor-pointer"
              }`}
            >
              {/* Photo if available */}
              {place.photo_url && (
                <div className="relative h-40 w-full overflow-hidden bg-muted">
                  <img 
                    src={place.photo_url} 
                    alt={place.name}
                    className="h-full w-full object-cover group-hover:scale-105 transition-transform"
                  />
                  
                  {/* Photographer attribution on image (Unsplash requirement) */}
                  {place.photographer_name && place.photographer_url && (
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                      <a
                        href={place.photographer_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-white hover:underline flex items-center gap-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Photo by {place.photographer_name} on{' '}
                        <span className="font-semibold">Unsplash</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </div>
                  )}
                </div>
              )}
              
              <div className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className={`font-semibold ${isAdded ? "text-green-700 dark:text-green-400" : "group-hover:text-primary transition-colors"}`}>
                        {place.name}
                      </h3>
                      {isAdded && (
                        <div className="flex items-center gap-1">
                          <span className="flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          </span>
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              onPlaceDeselect(place.place_id);
                            }}
                            className="ml-1 p-0.5 hover:bg-red-100 dark:hover:bg-red-900/20 rounded cursor-pointer transition-colors"
                            title="Remove place"
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.stopPropagation();
                                onPlaceDeselect(place.place_id);
                              }
                            }}
                          >
                            <X className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                          </div>
                        </div>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {place.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      📍 {place.address}
                    </p>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    {place.rating > 0 && (
                      <div className="flex items-center gap-1 bg-yellow-100 dark:bg-yellow-900/30 px-2 py-1 rounded">
                        <Star className="w-3 h-3 fill-yellow-500 text-yellow-500" />
                        <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                          {place.rating.toFixed(1)}
                        </span>
                      </div>
                    )}
                    {place.user_ratings_total > 0 && (
                      <span className="text-xs text-muted-foreground">
                        {place.user_ratings_total.toLocaleString()} reviews
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
      
      {/* Unsplash attribution footer (required by API guidelines) */}
      <div className="mt-6 pt-4 border-t border-border">
        <p className="text-xs text-muted-foreground text-center">
          Photos powered by{' '}
          <a 
            href="https://unsplash.com/?utm_source=GateAwayGenius&utm_medium=referral" 
            target="_blank" 
            rel="noopener noreferrer"
            className="font-semibold text-foreground hover:underline"
          >
            Unsplash
          </a>
        </p>
      </div>
    </div>
  );
};
