import React from "react";
import { useNavigate, Link } from "react-router-dom";
import logo from "../assets/smartagilelogo.png";

const LoginPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen sa-auth-page flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.35] pointer-events-none sa-auth-mesh"
        aria-hidden
      />
      <div className="absolute top-6 left-6 z-10">
        <Link
          to="/"
          className="text-sm font-medium text-slate-600 hover:text-indigo-700 transition-colors inline-flex items-center gap-1"
        >
          <span aria-hidden>←</span> Back to home
        </Link>
      </div>

      <div className="relative z-[1] w-full max-w-lg">
        <div className="text-center mb-10">
          <div className="inline-flex w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-700 items-center justify-center shadow-lg shadow-indigo-900/20 mb-4 ring-4 ring-white/80 overflow-hidden mx-auto">
            <img src={logo} alt="" className="w-10 h-10 object-contain" />
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight">
            Welcome back
          </h1>
          <p className="mt-2 text-slate-600">
            Choose how you want to sign in to SmartAgile.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => navigate("/loging")}
            className="group text-left rounded-2xl border-2 border-slate-200 bg-white/90 p-6 shadow-sm hover:border-indigo-400 hover:shadow-md hover:shadow-indigo-900/5 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 text-lg font-semibold mb-4 group-hover:bg-indigo-100">
              E
            </span>
            <h2 className="font-semibold text-lg text-slate-900">
              Employee login
            </h2>
            <p className="mt-1 text-sm text-slate-600 leading-relaxed">
              Tasks, attendance, apps &amp; websites dashboard.
            </p>
            <span className="mt-4 inline-flex items-center text-sm font-semibold text-indigo-700">
              Continue
              <span className="ml-1 group-hover:translate-x-0.5 transition-transform">
                →
              </span>
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigate("/adminlogin")}
            className="group text-left rounded-2xl border-2 border-slate-200 bg-white/90 p-6 shadow-sm hover:border-slate-800 hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-slate-400/40"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-800 text-lg font-semibold mb-4 group-hover:bg-slate-200">
              A
            </span>
            <h2 className="font-semibold text-lg text-slate-900">
              Admin login
            </h2>
            <p className="mt-1 text-sm text-slate-600 leading-relaxed">
              Sprint dashboard and team oversight.
            </p>
            <span className="mt-4 inline-flex items-center text-sm font-semibold text-slate-800">
              Continue
              <span className="ml-1 group-hover:translate-x-0.5 transition-transform">
                →
              </span>
            </span>
          </button>
        </div>

        <p className="text-center mt-8 text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
          <Link
            to="/data-collection"
            className="font-semibold text-indigo-700 hover:text-indigo-800 underline-offset-2 hover:underline"
          >
            What we collect
          </Link>
          {" — "}
          read this before installing or running the desktop activity agent.
        </p>

        <p className="text-center mt-6 text-sm text-slate-600">
          New here?{" "}
          <Link
            to="/signup"
            className="font-semibold text-indigo-700 hover:text-indigo-800 underline-offset-2 hover:underline"
          >
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
