import React, { useState } from "react";
import { api } from "../api/client";
import { Link, useNavigate } from "react-router-dom";
import AuthShell, { saInputClass, saLabelClass } from "./AuthShell";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleForgotPassword = async () => {
    setMessage("");
    setError("");

    const formData = new FormData();
    formData.append("email", email);

    try {
      const response = await api.post("/api/forgetpassword/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      sessionStorage.setItem("reset_email", JSON.stringify(email));
      setMessage(
        response.data?.message ||
          "If an account exists for this email, check your inbox for a code."
      );
      navigate("/forget/resetpassword");
    } catch (err) {
      if (err.response) {
        setError(
          err.response.data?.error || "Failed to send reset instructions."
        );
      } else if (err.request) {
        setError("No response received from server.");
      } else {
        setError("Failed to send reset instructions. Please try again.");
      }
    }
  };

  return (
    <AuthShell
      title="Reset password"
      subtitle="We’ll email you a code to set a new password."
      footer={
        <>
          Remember it?{" "}
          <Link
            to="/login"
            className="font-semibold text-indigo-700 hover:text-indigo-800"
          >
            Back to login
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        <div>
          <label htmlFor="forgot-email" className={saLabelClass}>
            Email
          </label>
          <input
            id="forgot-email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={saInputClass}
            autoComplete="email"
          />
        </div>
        {message && (
          <div className="text-sm text-center text-violet-800 bg-violet-50 rounded-xl py-2.5 px-3">
            {message}
          </div>
        )}
        {error && (
          <div className="text-sm text-center text-red-700 bg-red-50 rounded-xl py-2.5 px-3">
            {error}
          </div>
        )}
        <button
          type="button"
          onClick={handleForgotPassword}
          className="sa-btn-primary"
        >
          Send reset instructions
        </button>
      </div>
    </AuthShell>
  );
};

export default ForgotPassword;
