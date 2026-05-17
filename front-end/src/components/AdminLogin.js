// src/components/AdminLogin.js

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell, { saInputClass, saLabelClass } from "./AuthShell";
import { api, setAuthTokens } from "../api/client";
import { useSession } from "../context/SessionContext";

function AdminLogin() {
  const { refreshSession } = useSession();
  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const validate = () => {
    const newErrors = {};

    if (!form.email) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(form.email)) {
      newErrors.email = "Email is not valid";
    }

    if (!form.password) {
      newErrors.password = "Password is required";
    } else if (form.password.length > 100) {
      newErrors.password = "Password must be at most 100 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      const { data } = await api.post("/api/login/", form, {
        headers: { "Content-Type": "application/json" },
      });
      if (data.access) {
        setAuthTokens({ access: data.access, refresh: data.refresh });
      }
      setMessage("Login successful!");
      await refreshSession({ quiet: true });
      navigate("/admin/dashboard");
    } catch {
      setMessage("Invalid email or password.");
    }
  };

  return (
    <AuthShell
      title="Admin sign in"
      subtitle="Organization admin: people, projects, assignments, and sprint tools."
      backTo="/login"
      backLabel="Other login options"
      footer={
        <>
          <Link
            to="/forget"
            className="font-semibold text-teal-700 hover:text-teal-800"
          >
            Forgot password?
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="admin-email" className={saLabelClass}>
            Email
          </label>
          <input
            id="admin-email"
            type="email"
            name="email"
            placeholder="admin@company.com"
            className={saInputClass}
            value={form.email}
            onChange={handleChange}
            autoComplete="email"
          />
          {errors.email && (
            <p className="mt-1.5 text-sm text-red-600">{errors.email}</p>
          )}
        </div>
        <div>
          <label htmlFor="admin-password" className={saLabelClass}>
            Password
          </label>
          <input
            id="admin-password"
            type="password"
            name="password"
            placeholder="••••••••"
            className={saInputClass}
            value={form.password}
            onChange={handleChange}
            autoComplete="current-password"
          />
          {errors.password && (
            <p className="mt-1.5 text-sm text-red-600">{errors.password}</p>
          )}
        </div>
        {message && (
          <div
            className={`text-center text-sm rounded-xl py-2.5 px-3 ${
              message.includes("successful")
                ? "bg-emerald-50 text-emerald-800"
                : "bg-red-50 text-red-700"
            }`}
          >
            {message}
          </div>
        )}
        <button
          type="submit"
          className="w-full rounded-xl bg-slate-900 text-white font-semibold py-3.5 px-4 shadow-lg shadow-slate-900/20 transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2"
        >
          Sign in as admin
        </button>
      </form>
    </AuthShell>
  );
}

export default AdminLogin;
