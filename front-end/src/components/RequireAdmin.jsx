import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useSession } from "../context/SessionContext";

/**
 * Wraps admin-only routes. Non-admins are sent to the employee dashboard.
 */
export default function RequireAdmin({ children }) {
  const { user, loading } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }
    if (user.role !== "admin") {
      navigate("/employee/dashboard", { replace: true });
    }
  }, [loading, user, navigate]);

  if (loading || !user || user.role !== "admin") {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  return children;
}
