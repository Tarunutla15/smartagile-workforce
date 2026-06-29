// src/components/Login.js — Employee login

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell, { saInputClass, saLabelClass } from "./AuthShell";
import { api, setAuthTokens } from "../api/client";
import { useSession } from "../context/SessionContext";

function Login() {
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
      navigate("/employee/dashboard");
    } catch {
      setMessage("Invalid email or password.");
    }
  };

  return (
    <AuthShell
      title="Employee sign in"
      subtitle="Use the email and password from your registration."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link
            to="/signup"
            className="font-semibold text-indigo-700 hover:text-indigo-800"
          >
            Register
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="email" className={saLabelClass}>
            Email
          </label>
          <input
            id="email"
            type="email"
            name="email"
            placeholder="you@company.com"
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
          <label htmlFor="password" className={saLabelClass}>
            Password
          </label>
          <input
            id="password"
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
                ? "bg-violet-50 text-violet-800"
                : "bg-red-50 text-red-700"
            }`}
          >
            {message}
          </div>
        )}
        <button type="submit" className="sa-btn-primary">
          Sign in
        </button>
        <p className="text-center text-sm">
          <Link
            to="/forget"
            className="font-medium text-indigo-700 hover:text-indigo-800 underline-offset-2 hover:underline"
          >
            Forgot password?
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}

export default Login;
