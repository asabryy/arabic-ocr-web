import React from "react";
import { Link } from "react-router-dom";
import { Check } from "lucide-react";

const PLANS = [
  {
    name: "Free",
    price: "$0",
    desc: "Perfect for light use",
    features: ["5 pages per PDF", "Basic layout detection", "Community support"],
    cta: "Get Started",
    href: "/signup",
    accent: false,
  },
  {
    name: "Pro",
    price: "$9.99",
    period: "/mo",
    desc: "Ideal for frequent users",
    features: ["50+ pages per PDF", "Advanced layout detection", "Priority processing", "Translation (Soon)"],
    cta: "Upgrade",
    href: "/coming-soon",
    accent: true,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-4xl mx-auto px-6 py-20">
        <div className="mb-14">
          <div className="flex items-baseline gap-4 mb-6">
            <span className="section-label">Pricing</span>
            <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight mb-3 text-foreground">Choose your plan</h1>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm max-w-md">
            Whether you're an occasional user or a document-heavy professional.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-0 border border-zinc-200 dark:border-zinc-800 divide-y sm:divide-y-0 sm:divide-x divide-zinc-200 dark:divide-zinc-800">
          {PLANS.map((plan) => (
            <div key={plan.name} className={`p-8 flex flex-col bg-surface ${plan.accent ? "border-t-2 border-t-indigo-500" : "border-t-2 border-t-zinc-200 dark:border-t-zinc-700"}`}>
              <div className="mb-6">
                <h2 className="text-lg font-bold mb-1 text-foreground">{plan.name}</h2>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">{plan.desc}</p>
              </div>
              <div className="mb-8">
                <span className="text-4xl font-extrabold tabular-nums text-foreground">{plan.price}</span>
                {plan.period && <span className="text-sm text-zinc-400 ml-1">{plan.period}</span>}
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-zinc-600 dark:text-zinc-400">
                    <Check className="w-3.5 h-3.5 shrink-0 mt-0.5 text-indigo-500" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link to={plan.href} className={plan.accent ? "btn-primary justify-center py-2.5" : "btn-secondary justify-center py-2.5"}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
