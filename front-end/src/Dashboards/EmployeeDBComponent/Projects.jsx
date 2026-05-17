import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Button,
} from "@mui/material";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import { api } from "../../api/client";

/**
 * Only projects where you are a member, lead, or manager (allocated by admin).
 */
const Projects = () => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const { data } = await api.get("/taskapi/my-projects/");
      setRows(Array.isArray(data) ? data : []);
    } catch (e) {
      setError("Could not load your projects.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 2, mb: 2 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            My projects
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            You only see projects your admin added you to (team member, lead, or manager). Everything else stays on the
            admin organization dashboard.
          </Typography>
        </Box>
        <Button startIcon={<RefreshRoundedIcon />} variant="outlined" size="small" onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && rows.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>No project allocated yet.</strong> When an admin adds you to a project (or names you as lead/manager),
          it will show up here.
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: "action.hover" }}>
                <TableCell>Project</TableCell>
                <TableCell>Your role</TableCell>
                <TableCell>Lead</TableCell>
                <TableCell>Manager</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>
                    <Typography fontWeight={600}>{p.name}</Typography>
                    {p.description ? (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {p.description}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={p.your_role || "member"} variant="outlined" />
                  </TableCell>
                  <TableCell>{p.lead ? p.lead.username : "—"}</TableCell>
                  <TableCell>{p.manager ? p.manager.username : "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Projects;
