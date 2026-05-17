import React from "react";
import { Link } from "react-router-dom";
import { ABOUT_PRIVACY_REPLACEMENT } from "../content/dataCollectionCopy";

const sections = [
  {
    title: ABOUT_PRIVACY_REPLACEMENT.title,
    items: ABOUT_PRIVACY_REPLACEMENT.items,
  },
  {
    title: "Context-aware insights",
    items: [
      "Actionable insights based on work tasks and activities.",
      "Trends and optimizations tailored to roles and projects.",
    ],
  },
  {
    title: "Automated workflow optimization",
    items: [
      "Recommends adjustments to reduce inefficiencies.",
      "Surfaces bottlenecks and streamlining opportunities.",
    ],
  },
  {
    title: "Personalized recommendations",
    items: [
      "Tips and best practices for individual performance.",
      "Breaks and prioritization to support focus and reduce burnout.",
    ],
  },
  {
    title: "Real-time monitoring and feedback",
    items: [
      "Timely feedback without constant surveillance.",
      "Pattern-aware suggestions when it matters.",
    ],
  },
  {
    title: "Integration with workplace tools",
    items: [
      "Works alongside project and communication tools.",
      "Adds analytics without replacing your stack.",
    ],
  },
  {
    title: "Dashboards and reports",
    items: [
      "Visualize productivity metrics and trends.",
      "Reports for leads and managers.",
    ],
  },
  {
    title: "Task automation",
    items: [
      "Reduce repetitive work with ML-assisted patterns.",
      "Adapts as workflows change.",
    ],
  },
  {
    title: "Focus and distraction management",
    items: [
      "Support deep work and fewer interruptions.",
      "Surface better windows for concentration.",
    ],
  },
  {
    title: "Security and compliance",
    items: [
      "Encryption and alignment with common regulations (e.g. GDPR).",
      "Transparency and user control over data.",
    ],
  },
];

const About = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="absolute inset-0 sa-landing-mesh opacity-40 pointer-events-none" aria-hidden />
      <header className="relative border-b border-slate-200/80 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <Link
            to="/"
            className="text-sm font-semibold text-teal-700 hover:text-teal-800"
          >
            ← Home
          </Link>
          <Link
            to="/data-collection"
            className="text-sm font-semibold text-slate-600 hover:text-slate-900"
          >
            Data we collect
          </Link>
          <Link
            to="/login"
            className="text-sm font-semibold text-slate-700 hover:text-slate-900"
          >
            Login
          </Link>
        </div>
      </header>
      <main className="relative max-w-3xl mx-auto px-4 py-12 sm:py-16">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
          About SmartAgile
        </h1>
        <p className="mt-3 text-lg text-slate-600 leading-relaxed">
          Features and ideas behind this AI-assisted workplace productivity
          tool.
        </p>
        <div className="mt-10 rounded-2xl border border-amber-200/90 bg-amber-50/90 p-6 shadow-sm shadow-slate-900/5">
          <h2 className="font-semibold text-lg text-slate-900">
            Data collection (technical summary)
          </h2>
          <p className="mt-2 text-sm text-slate-700 leading-relaxed">
            SmartAgile can store per-user workplace metrics: foreground app
            name, window titles (including browser titles for site/tab
            context), time in focus, idle time, counts of key presses / clicks /
            scrolls (not what you type), attendance-related durations, and
            related dashboard fields. There is no keystroke content and no
            screen capture.
          </p>
          <p className="mt-3">
            <Link
              to="/data-collection"
              className="text-sm font-semibold text-teal-800 hover:text-teal-900 underline-offset-2 hover:underline"
            >
              Full disclosure: what is collected, who can see it, retention →
            </Link>
          </p>
        </div>
        <ul className="mt-12 space-y-8">
          {sections.map((s) => (
            <li
              key={s.title}
              className="rounded-2xl bg-white/90 border border-slate-200/80 p-6 shadow-sm shadow-slate-900/5"
            >
              <h2 className="font-semibold text-lg text-slate-900">
                {s.title}
              </h2>
              <ul className="mt-3 space-y-2 text-slate-600 text-sm leading-relaxed list-disc list-inside">
                {s.items.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
};

export default About;
