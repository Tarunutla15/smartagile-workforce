import React from "react";
import { Link } from "react-router-dom";
import { Box, CssBaseline, Paper } from "@mui/material";
import DataCollectionMui from "./DataCollectionMui";

/**
 * Public page: read before enabling the desktop agent or using dashboards.
 */
const DataCollectionPage = () => {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f8fafc" }}>
      <CssBaseline />
      <Box
        component="header"
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "rgba(255,255,255,0.9)",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <Box
          sx={{
            maxWidth: 720,
            mx: "auto",
            px: 2,
            py: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Link to="/" style={{ fontSize: 14, fontWeight: 600, color: "#4338ca", textDecoration: "none" }}>
            ← Home
          </Link>
          <Link to="/login" style={{ fontSize: 14, fontWeight: 600, color: "#334155", textDecoration: "none" }}>
            Login
          </Link>
        </Box>
      </Box>
      <Box component="main" sx={{ maxWidth: 720, mx: "auto", px: 2, py: 4 }}>
        <TypographyPublicTitle />
        <Paper elevation={0} sx={{ p: { xs: 2, sm: 3 }, borderRadius: 2, border: 1, borderColor: "divider" }}>
          <DataCollectionMui showAdminAudience />
        </Paper>
      </Box>
    </Box>
  );
};

function TypographyPublicTitle() {
  return (
    <Box sx={{ mb: 3 }}>
      <Box
        component="h1"
        sx={{
          fontFamily: '"Source Serif 4", Georgia, serif',
          fontSize: { xs: "1.75rem", sm: "2rem" },
          fontWeight: 700,
          color: "#0f172a",
          letterSpacing: "-0.02em",
          m: 0,
        }}
      >
        Data we collect
      </Box>
      <Box component="p" sx={{ mt: 1, color: "text.secondary", fontSize: "1rem", lineHeight: 1.6, m: 0 }}>
        Plain-language inventory of workplace metrics stored by SmartAgile. Read this before installing or running the
        desktop tracking agent.
      </Box>
    </Box>
  );
}

export default DataCollectionPage;
