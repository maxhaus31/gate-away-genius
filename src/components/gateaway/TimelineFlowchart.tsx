import { ActivityItinerary, ActivityStep } from "@/api/client";

interface TimelineFlowchartProps {
  itinerary: ActivityItinerary;
}

export function TimelineFlowchart({ itinerary }: TimelineFlowchartProps) {
  const formatDuration = (minutes: number) => {
    if (minutes <= 0) return "0 min";
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h === 0) return `${m} min`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}min`;
  };

  const getStepColor = (step: ActivityStep) => {
    switch (step.type) {
      case "airport":
        return "bg-red-100 border-red-400";
      case "travel":
        return "bg-blue-100 border-blue-400";
      case "activity":
        return "bg-green-100 border-green-400";
      default:
        return "bg-gray-100 border-gray-400";
    }
  };

  const getStepIcon = (step: ActivityStep) => {
    return (
      <div className="text-3xl mb-2 text-center">
        {step.emoji}
      </div>
    );
  };

  return (
    <div className="w-full overflow-x-auto">
      {/* Horizontal Flowchart */}
      <div className="flex items-center gap-2 p-6 bg-gradient-to-r from-slate-50 to-slate-100 rounded-lg border border-slate-200 min-w-min">
        {itinerary.steps.map((step, index) => (
          <div key={index} className="flex items-center gap-2">
            {/* Step Card */}
            <div
              className={`
                flex flex-col items-center justify-center
                px-4 py-3 rounded-lg border-2 min-w-max
                ${getStepColor(step)}
                transition-all hover:shadow-md
              `}
            >
              {getStepIcon(step)}
              <div className="text-sm font-semibold text-center text-slate-800 max-w-xs line-clamp-2">
                {step.title}
              </div>
              <div className="text-xs text-slate-600 mt-1 font-medium">
                {formatDuration(step.duration_minutes)}
              </div>
            </div>

            {/* Arrow to next step (except for last step) */}
            {index < itinerary.steps.length - 1 && (
              <div className="flex flex-col items-center gap-1">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 40 40"
                  className="text-slate-400"
                >
                  <path
                    d="M 5 20 L 35 20"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                  />
                  <path
                    d="M 30 15 L 35 20 L 30 25"
                    stroke="currentColor"
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary below flowchart */}
      <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        {itinerary.steps.map((step, index) => (
          <div key={index} className="text-xs p-2 bg-slate-50 rounded border border-slate-200">
            <div className="font-semibold text-slate-700 flex items-center gap-2">
              <span className="text-lg">{step.emoji}</span>
              {step.title}
            </div>
            <div className="text-slate-600 mt-1 text-right">
              {formatDuration(step.duration_minutes)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
