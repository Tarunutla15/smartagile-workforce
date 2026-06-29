import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell, { saInputClass, saLabelClass } from "./AuthShell";
import { api, setAuthTokens } from "../api/client";
import { useSession } from "../context/SessionContext";

const Register = () => {
  const navigate = useNavigate();
  const { refreshSession } = useSession();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("employee");
  const [profilePhoto, setProfilePhoto] = useState(null);
  const [error, setError] = useState("");

  const handleRegister = () => {
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length > 100) {
      setError("Password must be at most 100 characters.");
      return;
    }

    const formData = new FormData();
    formData.append("username", username);
    formData.append("email", email);
    formData.append("password", password);
    formData.append("role", role);
    if (profilePhoto) {
      formData.append("profile_photo", profilePhoto);
    }

    api
      .post("/api/signup/", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })
      .then(async (res) => {
        if (res.data?.access) {
          setAuthTokens({
            access: res.data.access,
            refresh: res.data.refresh,
          });
        }
        await refreshSession({ quiet: true });
        if (role === "admin") {
          navigate("/admin/dashboard");
        } else {
          navigate("/employee/dashboard");
        }
      })
      .catch((err) => {
        const msg =
          err.response?.data &&
          (typeof err.response.data === "string"
            ? err.response.data
            : JSON.stringify(err.response.data));
        setError(msg || "Registration failed. Try a different email.");
      });
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (
      file &&
      (file.type === "image/png" ||
        file.type === "image/jpeg" ||
        file.type === "image/jpg")
    ) {
      setProfilePhoto(file);
    } else if (file) {
      setError("Please upload PNG, JPG, or JPEG only.");
    }
  };

  const selectClass = `${saInputClass} appearance-none cursor-pointer`;

  return (
    <AuthShell
      title="Create your account"
      subtitle="Join SmartAgile as an employee or admin."
      footer={
        <>
          <p className="mb-3 text-slate-600">
            <Link
              to="/data-collection"
              className="font-semibold text-indigo-700 hover:text-indigo-800 underline-offset-2 hover:underline"
            >
              What we collect
            </Link>{" "}
            — read before using the desktop activity agent.
          </p>
          Already registered?{" "}
          <Link
            to="/login"
            className="font-semibold text-indigo-700 hover:text-indigo-800"
          >
            Sign in
          </Link>
        </>
      }
    >
      <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1 -mr-1">
        <div>
          <label htmlFor="reg-username" className={saLabelClass}>
            Username
          </label>
          <input
            id="reg-username"
            type="text"
            placeholder="Jane Doe"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={saInputClass}
            autoComplete="username"
          />
        </div>
        <div>
          <label htmlFor="reg-email" className={saLabelClass}>
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={saInputClass}
            autoComplete="email"
          />
        </div>
        <div>
          <label htmlFor="reg-password" className={saLabelClass}>
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            placeholder="Choose a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={saInputClass}
            autoComplete="new-password"
          />
        </div>
        <div>
          <label htmlFor="reg-confirm" className={saLabelClass}>
            Confirm password
          </label>
          <input
            id="reg-confirm"
            type="password"
            placeholder="Repeat password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className={saInputClass}
            autoComplete="new-password"
          />
        </div>
        <div>
          <label htmlFor="reg-role" className={saLabelClass}>
            Role
          </label>
          <select
            id="reg-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className={selectClass}
          >
            <option value="employee">Employee</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div>
          <label htmlFor="profilePhoto" className={saLabelClass}>
            Profile photo{" "}
            <span className="font-normal normal-case text-slate-400">
              (optional)
            </span>
          </label>
          <input
            type="file"
            id="profilePhoto"
            accept="image/png,image/jpeg,image/jpg"
            onChange={handlePhotoUpload}
            className="block w-full text-sm text-slate-600 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-800 hover:file:bg-indigo-100 cursor-pointer"
          />
        </div>
        {error && (
          <div className="text-sm text-red-700 bg-red-50 rounded-xl py-2.5 px-3">
            {error}
          </div>
        )}
        <button
          type="button"
          onClick={handleRegister}
          className="sa-btn-primary"
        >
          Create account
        </button>
      </div>
    </AuthShell>
  );
};

export default Register;
