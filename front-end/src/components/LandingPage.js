import React from "react";
import { Link } from "react-router-dom";
import logo from "../assets/smartagilelogo.png";
import { DarkModeButton } from "../theme/DarkModeToggle";

const LandingPage = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 relative overflow-hidden dark:bg-slate-950 dark:text-slate-100">
      <div
        className="absolute inset-0 sa-landing-mesh pointer-events-none"
        aria-hidden
      />
      <nav className="relative z-10 w-full max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <Link
          to="/"
          className="flex items-center gap-3 group"
        >
          <span className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-700 shadow-md shadow-indigo-900/15 flex items-center justify-center overflow-hidden ring-2 ring-white">
            <img
              src={logo}
              alt=""
              className="w-8 h-8 object-contain"
            />
          </span>
          <span className="font-display text-xl font-semibold tracking-tight text-slate-900 group-hover:text-indigo-800 transition-colors dark:text-slate-50 dark:group-hover:text-indigo-300">
            SmartAgile
          </span>
        </Link>
        <div className="flex items-center gap-1 sm:gap-2 text-sm font-medium">
          <Link
            to="/"
            className="px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-white/70 transition-colors dark:text-slate-300 dark:hover:text-white dark:hover:bg-white/10"
          >
            Home
          </Link>
          <Link
            to="/about"
            className="px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-white/70 transition-colors dark:text-slate-300 dark:hover:text-white dark:hover:bg-white/10"
          >
            About
          </Link>
          <Link
            to="/data-collection"
            className="px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-white/70 transition-colors dark:text-slate-300 dark:hover:text-white dark:hover:bg-white/10"
          >
            Data we collect
          </Link>
          <Link
            to="/signup"
            className="px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-white/70 transition-colors dark:text-slate-300 dark:hover:text-white dark:hover:bg-white/10"
          >
            Register
          </Link>
          <Link
            to="/login"
            className="ml-1 px-4 py-2 rounded-lg bg-slate-900 text-white hover:bg-indigo-700 shadow-sm transition-colors dark:bg-indigo-600 dark:hover:bg-indigo-500"
          >
            Login
          </Link>
          <DarkModeButton className="ml-1" />
        </div>
      </nav>

      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 pb-20 pt-6 sm:pt-12">
        <div className="max-w-3xl mx-auto text-center">
          <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-full px-4 py-1.5 mb-6 dark:text-indigo-300 dark:bg-indigo-950/50 dark:border-indigo-400/20">
            Workplace intelligence
          </p>
          <h1 className="font-display text-4xl sm:text-5xl md:text-6xl font-bold text-slate-900 leading-[1.1] tracking-tight dark:text-slate-50">
            Agile workflows,{" "}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              smarter productivity
            </span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed dark:text-slate-300">
            AI-assisted insights that separate focused work from noise—so teams
            ship sprints with clarity, not guesswork.
          </p>
          <p className="mt-4 text-slate-500 max-w-xl mx-auto text-sm sm:text-base leading-relaxed dark:text-slate-400">
            Understand application and browser usage in context, align tasks with
            real effort, and keep everyone on the same page.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/login"
              className="sa-btn-primary w-full sm:w-auto min-w-[200px] text-center no-underline"
            >
              Get started
            </Link>
            <Link
              to="/signup"
              className="sa-btn-secondary w-full sm:w-auto min-w-[200px] no-underline"
            >
              Create an account
            </Link>
          </div>
        </div>

        <div className="mt-16 sm:mt-24 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-4xl w-full text-left">
          {[
            {
              title: "Sprint visibility",
              body: "Dashboards for employees, groups, and admins in one place.",
            },
            {
              title: "Usage context",
              body: "See where time goes across apps and sites—labeled for work relevance.",
            },
            {
              title: "Task alignment",
              body: "Connect kanban-style tasks with how teams actually spend their day.",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-2xl bg-white/80 border border-slate-200/80 p-5 shadow-sm shadow-slate-900/5 backdrop-blur-sm hover:border-indigo-200/80 transition-colors dark:bg-slate-900/70 dark:border-slate-800 dark:hover:border-indigo-500/40"
            >
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">{item.title}</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed dark:text-slate-400">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default LandingPage;
