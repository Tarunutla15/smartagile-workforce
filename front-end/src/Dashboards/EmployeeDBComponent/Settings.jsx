import React from "react";
import { Link } from "react-router-dom";
import { Box, Button, Paper, Typography } from "@mui/material";
import DataCollectionMui from "../../components/DataCollectionMui";
import DesktopAgentConnect from "../../components/DesktopAgentConnect";

const Settings = () => {
  return (
    <Box>
      <Typography variant="h5" fontWeight={700} gutterBottom sx={{ color: "#0f172a" }}>
        Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Privacy and data collection match what the desktop agent sends to your organization’s server.
      </Typography>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 3 },
          borderRadius: 2,
          border: 1,
          borderColor: "divider",
          maxWidth: 720,
        }}
      >
        <DataCollectionMui showAdminAudience />
        <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: "divider" }}>
          <DesktopAgentConnect />
        </Box>
        <Button
          component={Link}
          to="/data-collection"
          variant="outlined"
          size="small"
          sx={{ mt: 2 }}
        >
          Open printable / shareable page
        </Button>
      </Paper>
    </Box>
  );
};

export default Settings;
