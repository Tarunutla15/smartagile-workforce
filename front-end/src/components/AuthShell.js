import React from "react";
import { Link } from "react-router-dom";
import logo from "../assets/smartagilelogo.png";
import { DarkModeButton } from "../theme/DarkModeToggle";

/**
 * Shared layout for sign-in / sign-up screens.
 */
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
  backTo = "/",
  backLabel = "Back to home",
}) {
  return (
    <div className="min-h-screen sa-auth-page flex flex-col items-center justify-center px-4 py-10 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.35] pointer-events-none sa-auth-mesh"
        aria-hidden
      />
      <div className="absolute top-6 left-6 z-10">
        <Link
          to={backTo}
          className="text-sm font-medium text-slate-600 hover:text-indigo-700 transition-colors inline-flex items-center gap-1 dark:text-slate-300 dark:hover:text-indigo-300"
        >
          <span aria-hidden>←</span> {backLabel}
        </Link>
      </div>
      <div className="absolute top-6 right-6 z-10">
        <DarkModeButton />
      </div>
      <div className="relative z-[1] w-full max-w-md">
        <div className="sa-auth-card rounded-2xl shadow-xl shadow-slate-900/10 border border-white/60 p-8 sm:p-10 backdrop-blur-md dark:border-white/10">
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center shadow-lg shadow-indigo-900/20 mb-4 overflow-hidden ring-4 ring-white/80 dark:ring-white/10">
              <img
                src={logo}
                alt=""
                className="w-12 h-12 object-contain"
              />
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight dark:text-slate-50">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-2 text-slate-600 text-sm leading-relaxed max-w-xs mx-auto dark:text-slate-300">
                {subtitle}
              </p>
            ) : null}
          </div>
          {children}
          {footer ? (
            <div className="mt-8 pt-6 border-t border-slate-200/80 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
              {footer}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export const saInputClass =
  "w-full rounded-xl border border-slate-200 bg-white/90 px-4 py-3 text-slate-900 text-sm placeholder:text-slate-400 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-100 dark:placeholder:text-slate-500";

export const saLabelClass =
  "block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5 dark:text-slate-400";
