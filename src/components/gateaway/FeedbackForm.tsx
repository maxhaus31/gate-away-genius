import { useState } from "react";
import { Star } from "lucide-react";
import { submitFeedback } from "@/api/client";

export const FeedbackForm = () => {
  const [hovered, setHovered] = useState<number>(0);
  const [selected, setSelected] = useState<number>(0);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await submitFeedback({ rating: selected || undefined, email: email || undefined, message: message || undefined });
    } catch {
      // submit best-effort; don't block the thank-you on a network error
    }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
        <p className="text-sm font-medium text-foreground">Thanks for your feedback!</p>
        <p className="mt-1 text-sm text-muted-foreground">We read every submission.</p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-foreground">Was this helpful?</h2>
        <div className="mt-4 flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onMouseEnter={() => setHovered(star)}
              onMouseLeave={() => setHovered(0)}
              onClick={() => setSelected(star)}
              className="p-0.5 transition-transform hover:scale-110"
            >
              <Star
                className={`h-7 w-7 transition-colors ${
                  star <= (hovered || selected)
                    ? "fill-primary text-primary"
                    : "fill-transparent text-muted-foreground/40"
                }`}
              />
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-foreground">Tell us more about your trip?</h2>

        <div>
          <label className="block text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-1.5">
            Your email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none focus:border-primary transition-colors"
          />
        </div>

        <div>
          <label className="block text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground mb-1.5">
            Your experience
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Tell us more about your experience"
            rows={4}
            className="w-full rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none focus:border-primary transition-colors resize-none"
          />
        </div>
      </div>

      <button
        type="submit"
        className="rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
      >
        Submit feedback
      </button>
    </form>
  );
};
