import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Paper,
} from "@mui/material";
import { format } from "date-fns";
import { api } from "../../api/client";
import { applyDateFilter } from "../EmployeeDBComponent/AppDataProvider";
import { isWorkRelatedCategory } from "../../utils/workRelatedCategory";

function formatDuration(secondsTotal) {
  const s = Math.max(0, Math.round(Number(secondsTotal) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

/** @typedef {'all' | 'workRelated' | 'other'} KindFilter */

export default function AdminEmployeeActivityDialog({ open, onClose, employee }) {
  const today = new Date();
  const [dateFilter, setDateFilter] = useState("This Week");
  const [startDate, setStartDate] = useState(format(today, "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(format(today, "yyyy-MM-dd"));
  const [kindFilter, setKindFilter] = useState(/** @type {KindFilter} */ ("all"));
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!employee?.id) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get(`/api/admin/employee/${employee.id}/usage/`);
      setRows(Array.isArray(data) ? data : []);
    } catch (e) {
      setRows([]);
      setError(e.response?.data?.error || e.message || "Could not load activity.");
    } finally {
      setLoading(false);
    }
  }, [employee?.id]);

  useEffect(() => {
    if (open && employee?.id) load();
  }, [open, employee?.id, load]);

  useEffect(() => {
    if (open) setKindFilter("all");
  }, [open, employee?.id]);

  const filtered = useMemo(
    () => applyDateFilter(rows, dateFilter, startDate, endDate),
    [rows, dateFilter, startDate, endDate]
  );

  const totals = useMemo(() => {
    let work = 0;
    let other = 0;
    for (const r of filtered) {
      const d = Number(r.duration) || 0;
      if (isWorkRelatedCategory(r.category)) work += d;
      else other += d;
    }
    const total = work + other;
    return {
      work,
      other,
      total,
      workPct: total > 0 ? Math.round((work / total) * 1000) / 10 : 0,
    };
  }, [filtered]);

  const sortedRows = useMemo(() => {
    let list = filtered;
    if (kindFilter === "workRelated") {
      list = filtered.filter((r) => isWorkRelatedCategory(r.category));
    } else if (kindFilter === "other") {
      list = filtered.filter((r) => !isWorkRelatedCategory(r.category));
    }
    return [...list].sort((a, b) => {
      const db = new Date(b.date).getTime() - new Date(a.date).getTime();
      if (db !== 0) return db;
      return (Number(b.duration) || 0) - (Number(a.duration) || 0);
    });
  }, [filtered, kindFilter]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg" aria-labelledby="admin-activity-title">
      <DialogTitle id="admin-activity-title">
        Activity — {employee?.username || "User"}
        <Typography variant="body2" color="text.secondary" fontWeight={400} sx={{ mt: 0.5 }}>
          {employee?.email}
        </Typography>
      </DialogTitle>
      <DialogContent dividers>
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>Work-related</strong> = category is exactly <code>work</code> or <code>work-related</code> (with
          hyphen), any casing (e.g. <code>Work</code>, <code>Work-related</code>). <strong>Other</strong> = all
          remaining categories. Click a chip below to filter the table. Categories come from the on-device model.
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          Filter table (selected period):
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, mb: 2, alignItems: "center" }}>
          <Chip
            label={`All — ${formatDuration(totals.total)}`}
            onClick={() => setKindFilter("all")}
            variant={kindFilter === "all" ? "filled" : "outlined"}
            sx={{ fontWeight: kindFilter === "all" ? 700 : 400, cursor: "pointer" }}
          />
          <Chip
            label={`Work-related — ${formatDuration(totals.work)}`}
            onClick={() => setKindFilter("workRelated")}
            variant={kindFilter === "workRelated" ? "filled" : "outlined"}
            color={kindFilter === "workRelated" ? "success" : "default"}
            sx={{ cursor: "pointer" }}
          />
          <Chip
            label={`Other — ${formatDuration(totals.other)}`}
            onClick={() => setKindFilter("other")}
            variant={kindFilter === "other" ? "filled" : "outlined"}
            color={kindFilter === "other" ? "warning" : "default"}
            sx={{ cursor: "pointer" }}
          />
          <Chip label={`Work-related share: ${totals.total ? `${totals.workPct}%` : "—"}`} variant="outlined" />
          <Box sx={{ flex: 1 }} />
          <Button size="small" variant="outlined" onClick={load} disabled={loading}>
            Refresh
          </Button>
        </Box>

        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2, alignItems: "center" }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Period</InputLabel>
            <Select
              label="Period"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
            >
              <MenuItem value="Today">Today</MenuItem>
              <MenuItem value="Yesterday">Yesterday</MenuItem>
              <MenuItem value="This Week">This week</MenuItem>
              <MenuItem value="Custom">Custom</MenuItem>
            </Select>
          </FormControl>
          {dateFilter === "Custom" && (
            <>
              <TextField
                size="small"
                label="From"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                size="small"
                label="To"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </>
          )}
        </Box>

        {loading && !rows.length ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>App / browser</TableCell>
                  <TableCell>Window / site</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Work-related</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography color="text.secondary" variant="body2">
                        {filtered.length === 0
                          ? "No usage rows for this period. The employee needs the desktop tracker running on Windows with data synced to this server."
                          : kindFilter === "workRelated"
                            ? "No work-related rows (categories work or work-related) in this period."
                            : "No “other” rows in this period."}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedRows.map((row, index) => (
                    <TableRow key={`${row.applicationname}-${row.task}-${row.date}-${index}`} hover>
                      <TableCell>{row.applicationname}</TableCell>
                      <TableCell sx={{ maxWidth: 280, wordBreak: "break-word" }}>{row.task}</TableCell>
                      <TableCell>{row.category}</TableCell>
                      <TableCell>{isWorkRelatedCategory(row.category) ? "Yes" : "No"}</TableCell>
                      <TableCell>{formatDuration(row.duration)}</TableCell>
                      <TableCell>{row.date}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} variant="contained" sx={{ bgcolor: "#0f766e" }}>
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
