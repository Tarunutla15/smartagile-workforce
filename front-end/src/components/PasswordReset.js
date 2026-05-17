import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import AuthShell, { saInputClass, saLabelClass } from "./AuthShell";

const PasswordResetForm = () => {
  const navigate = useNavigate();
  const [otp, setOTP] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleResetPassword = async () => {
    setMessage("");
    setError("");

    if (!otp) {
      setError("OTP is required.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (!password) {
      setError("Enter a new password.");
      return;
    }

    if (password.length > 100) {
      setError("Password must be at most 100 characters.");
      return;
    }

    const formData = new FormData();
    formData.append("otp", otp);
    formData.append("password", password);

    try {
      const response = await api.post("/api/resetpassword/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.status === 200) {
        sessionStorage.removeItem("reset_email");
        setMessage(response.data.message);
        setTimeout(() => {
          navigate("/login");
        }, 2000);
      } else {
        setError(
          response.data.error || "Failed to reset password. Please try again."
        );
      }
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Failed to reset password. Please try again."
      );
    }
  };

  return (
    <AuthShell
      title="Choose a new password"
      subtitle="Enter the code from your email and your new password."
      footer={
        <>
          <Link
            to="/forget"
            className="font-semibold text-teal-700 hover:text-teal-800"
          >
            Request a new code
          </Link>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label htmlFor="reset-otp" className={saLabelClass}>
            One-time code
          </label>
          <input
            id="reset-otp"
            type="text"
            placeholder="6-digit code"
            value={otp}
            onChange={(e) => setOTP(e.target.value)}
            className={saInputClass}
            inputMode="numeric"
            autoComplete="one-time-code"
          />
        </div>
        <div>
          <label htmlFor="reset-pass" className={saLabelClass}>
            New password
          </label>
          <input
            id="reset-pass"
            type="password"
            placeholder="New password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={saInputClass}
            autoComplete="new-password"
          />
        </div>
        <div>
          <label htmlFor="reset-confirm" className={saLabelClass}>
            Confirm password
          </label>
          <input
            id="reset-confirm"
            type="password"
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={saInputClass}
            autoComplete="new-password"
          />
        </div>
        {message && (
          <div className="text-sm text-center text-emerald-800 bg-emerald-50 rounded-xl py-2.5 px-3">
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
          onClick={handleResetPassword}
          className="sa-btn-primary"
        >
          Update password
        </button>
      </div>
    </AuthShell>
  );
};

export default PasswordResetForm;
