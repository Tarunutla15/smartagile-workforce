import React, { useState, useEffect, useCallback, useMemo } from "react";
import "./styles.css";
import { PieChart } from "@mui/x-charts/PieChart";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Grid,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import TodayIcon from "@mui/icons-material/Today";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import { parseISO, isToday, format } from "date-fns";
import { api } from "../../api/client";

const ACCENT = "#0d9488";
const CHART_COLORS = ["#0d9488", "#6366f1"];

function formatDurationSeconds(sec) {
  if (sec == null || Number.isNaN(sec)) return "—";
  const m = Math.floor(sec / 60);
  const h = Math.floor(m / 60);
  const min = m % 60;
  if (h > 0) return `${h}h ${min}m`;
  return `${min}m`;
}

function StatCard({ label, value, icon }) {
  return (
    <Card
      elevation={0}
      sx={{
        height: "100%",
        borderRadius: 2.5,
        border: 1,
        borderColor: "divider",
        background: (t) =>
          t.palette.mode === "dark"
            ? "linear-gradient(145deg, rgba(13,148,136,0.12) 0%, rgba(15,23,42,0.9) 100%)"
            : "linear-gradient(145deg, #f0fdfa 0%, #fff 50%)",
        boxShadow: (t) => (t.palette.mode === "dark" ? "none" : "0 2px 12px rgba(15,23,42,0.06)"),
        transition: "0.2s ease",
        "&:hover": {
          borderColor: "rgba(13, 148, 136, 0.35)",
          boxShadow: (t) => (t.palette.mode === "dark" ? 2 : "0 6px 20px rgba(15,23,42,0.1)"),
        },
      }}
    >
      <CardContent sx={{ py: 2, px: 1.75, "&:last-child": { pb: 2 } }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1}>
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ textTransform: "uppercase", letterSpacing: 0.45, fontWeight: 700, lineHeight: 1.2 }}
            >
              {label}
            </Typography>
            <Typography variant="h6" sx={{ mt: 0.4, fontWeight: 800, letterSpacing: -0.3, lineHeight: 1.2 }}>
              {value}
            </Typography>
          </Box>
          <Box
            aria-hidden
            sx={{
              color: ACCENT,
              display: "grid",
              placeItems: "center",
              width: 40,
              height: 40,
              borderRadius: 1.5,
              flexShrink: 0,
              bgcolor: "rgba(13, 148, 136, 0.12)",
              border: 1,
              borderColor: "rgba(13, 148, 136, 0.25)",
              fontSize: 20,
            }}
          >
            {icon}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function TodayTimeline({ todayRow }) {
  const steps = todayRow
    ? [
        {
          title: "Login recorded",
          time: todayRow.login || "—",
          done: true,
        },
        {
          title: todayRow.logout ? "Logout recorded" : "Still active · 7:00 PM auto-logout rule",
          time: todayRow.logout || "—",
          done: !!todayRow.logout,
        },
      ]
    : [
        {
          title: "No record for today",
          time: "Log in to start the day",
          done: false,
        },
      ];

  return (
    <Box
      sx={{
        p: 2.5,
        borderRadius: 2.5,
        border: 1,
        borderColor: "divider",
        background: (t) =>
          t.palette.mode === "dark"
            ? "linear-gradient(180deg, rgba(15,23,42,0.95) 0%, #0f172a 100%)"
            : "linear-gradient(180deg, #f8fffe 0%, #fff 100%)",
        boxShadow: (t) => (t.palette.mode === "dark" ? "0 2px 16px rgba(0,0,0,0.3)" : "0 2px 16px rgba(15,23,42,0.06)"),
        height: "100%",
      }}
    >
      <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 2.5 }}>
        <Box
          sx={{
            width: 42,
            height: 42,
            borderRadius: 2,
            display: "grid",
            placeItems: "center",
            bgcolor: "rgba(13, 148, 136, 0.15)",
            color: ACCENT,
            border: 1,
            borderColor: "rgba(13, 148, 136, 0.35)",
          }}
        >
          <TodayIcon />
        </Box>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: -0.2, color: ACCENT, lineHeight: 1.2 }}>
            Today
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Login, logout, and in-progress for the current day
          </Typography>
        </Box>
      </Stack>

      <Stack component="ul" spacing={0} sx={{ m: 0, p: 0, listStyle: "none" }}>
        {steps.map((step, i) => (
          <Box
            key={i}
            component="li"
            sx={{
              display: "flex",
              gap: 1.5,
              pb: i < steps.length - 1 ? 2.5 : 0,
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", width: 20, flexShrink: 0, pt: 0.4 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  bgcolor: step.done ? "success.main" : ACCENT,
                  border: 2,
                  borderColor: "background.paper",
                  boxShadow: 1,
                }}
              />
              {i < steps.length - 1 && (
                <Box
                  sx={{
                    width: 2,
                    flex: 1,
                    minHeight: 20,
                    mt: 0.5,
                    borderRadius: 1,
                    bgcolor: "divider",
                  }}
                />
              )}
            </Box>
            <Box sx={{ minWidth: 0, flex: 1, pb: i < steps.length - 1 ? 0 : 0 }}>
              <Typography variant="body1" fontWeight={700} sx={{ lineHeight: 1.35 }}>
                {step.title}
              </Typography>
              <Stack direction="row" alignItems="center" gap={0.75} sx={{ mt: 0.75 }} flexWrap="wrap">
                <AccessTimeIcon sx={{ fontSize: 18, color: "text.secondary" }} />
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  {step.time}
                </Typography>
              </Stack>
            </Box>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}

function MyAttendance({ rows }) {
  const theme = useTheme();
  const isNarrow = useMediaQuery(theme.breakpoints.down("md"));
  const { pieData } = useMemo(() => {
    const w = rows.filter((r) => r.logout != null).length;
    const o = Math.max(0, rows.length - w);
    const data = [];
    if (w > 0) {
      data.push({ id: "done", value: w, label: "Completed day (logged out)" });
    }
    if (o > 0) {
      data.push({ id: "open", value: o, label: "Open / in progress" });
    }
    return { pieData: data };
  }, [rows]);

  if (rows.length === 0) {
    return (
      <Box
        sx={{
          p: 3,
          border: 1,
          borderStyle: "dashed",
          borderColor: "divider",
          borderRadius: 2.5,
          textAlign: "center",
          bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.50"),
        }}
      >
        <EventAvailableIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 280, mx: "auto" }}>
          No history to chart yet. As you accrue days, you&apos;ll see completed vs open days here.
        </Typography>
      </Box>
    );
  }

  if (pieData.length === 0) {
    return (
      <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No segments to show.
        </Typography>
      </Box>
    );
  }

  const w = isNarrow ? 300 : 400;
  const h = isNarrow ? 260 : 300;

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 2.5,
        border: 1,
        borderColor: "divider",
        background: (t) =>
          t.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(13, 148, 136, 0.04)",
      }}
    >
      <Typography variant="subtitle1" fontWeight={800} sx={{ mb: 0.5, color: "text.primary" }}>
        Day balance
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
        Days with a recorded logout vs days still open (in progress). Hover a slice for counts; legend matches colors.
      </Typography>
      <Box sx={{ display: "flex", justifyContent: "center", width: "100%", overflow: "auto" }}>
        <PieChart
          width={w}
          height={h}
          margin={isNarrow ? { top: 8, right: 4, bottom: 8, left: 4 } : { top: 8, right: 8, bottom: 8, left: 8 }}
          colors={CHART_COLORS}
          series={[
            {
              data: pieData,
              innerRadius: "42%",
              outerRadius: "80%",
              paddingAngle: 2,
              cornerRadius: 2,
              highlightScope: { fade: "global", highlight: "item" },
              valueFormatter: (v) => (v == null ? "" : `${Number(v)} day${Number(v) === 1 ? "" : "s"}`),
            },
          ]}
          slotProps={{
            legend: {
              hidden: isNarrow,
            },
            tooltip: { trigger: "item" },
          }}
          sx={{ maxWidth: "100%" }}
        />
      </Box>
      {isNarrow && pieData.length > 0 && (
        <Stack component="ul" spacing={0.75} sx={{ mt: 2, m: 0, pl: 0, listStyle: "none" }} alignItems="flex-start">
          {pieData.map((d, i) => (
            <Box key={d.id} component="li" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: 0.5, flexShrink: 0, bgcolor: CHART_COLORS[i % CHART_COLORS.length] }} />
              <Typography variant="body2" color="text.secondary">
                {d.label} · {d.value} {d.value === 1 ? "day" : "days"}
              </Typography>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}

function Attendance() {
  const [rows, setRows] = useState([]);
  const [authSummary, setAuthSummary] = useState(null);
  const [authEvents, setAuthEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const loadAttendance = useCallback(async () => {
    try {
      const attRes = await api.get("/api/attendence/");
      setRows(Array.isArray(attRes.data) ? attRes.data : []);
    } catch (e) {
      console.error(e);
      setRows([]);
      if (e.response?.status === 401) {
        setError("Not signed in.");
      } else {
        setError("Could not load daily attendance.");
      }
      setLoading(false);
      setRefreshing(false);
      return;
    }

    try {
      const authRes = await api.get("/api/auth_events/?limit=150");
      if (authRes.data?.summary) {
        setAuthSummary(authRes.data.summary);
        setAuthEvents(Array.isArray(authRes.data.events) ? authRes.data.events : []);
      } else {
        setAuthSummary(null);
        setAuthEvents([]);
      }
    } catch (e) {
      console.error(e);
      setAuthSummary(null);
      setAuthEvents([]);
    }

    setError("");
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    loadAttendance();
  }, [loadAttendance]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadAttendance();
  };

  const todayRow = rows.find((r) => {
    if (!r.date) return false;
    try {
      return isToday(parseISO(r.date));
    } catch {
      return false;
    }
  });

  const officeDisplay = todayRow ? formatDurationSeconds(todayRow.duration_seconds) : "—";
  const activeDisplay = todayRow?.logout
    ? "Logged out"
    : todayRow?.login
      ? "In progress"
      : "—";

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress size={32} thickness={4} sx={{ color: ACCENT }} />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", width: "100%" }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
        gap={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -0.3 }}>
            Attendance
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 520 }}>
            Your daily login window, sign-in counts, and history. Sync pulls the latest from the server.
          </Typography>
        </Box>
        <Button
          startIcon={<RefreshIcon />}
          variant="outlined"
          onClick={handleRefresh}
          disabled={refreshing}
          sx={{ alignSelf: { xs: "stretch", sm: "center" }, textTransform: "none", fontWeight: 700, borderRadius: 2, px: 2 }}
        >
          {refreshing ? "Syncing…" : "Sync"}
        </Button>
      </Stack>

      {error && (
        <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={1.5} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <StatCard label="Today (login → logout)" value={officeDisplay} icon={<AccessTimeIcon fontSize="small" />} />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            label="Status"
            value={activeDisplay}
            icon={todayRow?.logout ? <CheckCircleOutlineIcon fontSize="small" /> : <HourglassEmptyIcon fontSize="small" />}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard label="Logout rule" value="7:00 PM" icon={<LogoutIcon fontSize="small" />} />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard label="Days on file" value={String(rows.length)} icon={<CalendarMonthIcon fontSize="small" />} />
        </Grid>
        {authSummary && (
          <>
            <Grid item xs={6} sm={3}>
              <StatCard label="Logins today" value={String(authSummary.logins_today)} icon={<LoginIcon fontSize="small" />} />
            </Grid>
            <Grid item xs={6} sm={3}>
              <StatCard
                label="Logouts today"
                value={String(authSummary.logouts_today)}
                icon={<LogoutIcon fontSize="small" />}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <StatCard
                label="Logins (month)"
                value={String(authSummary.logins_this_month)}
                icon={<LoginIcon fontSize="small" />}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <StatCard
                label="Logouts (month)"
                value={String(authSummary.logouts_this_month)}
                icon={<LogoutIcon fontSize="small" />}
              />
            </Grid>
          </>
        )}
      </Grid>

      <Grid container spacing={2} alignItems="flex-start" sx={{ mb: 4 }}>
        <Grid item xs={12} md={5} lg={4}>
          <TodayTimeline todayRow={todayRow} />
        </Grid>
        <Grid item xs={12} md={7} lg={8}>
          <MyAttendance rows={rows} />
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ fontWeight: 800, color: ACCENT, mb: 0.5, letterSpacing: -0.2 }}>
        Daily history
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Login, logout, and duration per calendar day.
      </Typography>
      <TableContainer
        component={Paper}
        elevation={0}
        sx={{ borderRadius: 2, border: 1, borderColor: "divider", mb: 4, overflow: "hidden" }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>Date</TableCell>
              <TableCell>Login</TableCell>
              <TableCell>Logout</TableCell>
              <TableCell>Duration</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} sx={{ py: 2 }}>
                  No attendance rows yet. Log in to record today&apos;s login time; sign out in the app or use the 7:00
                  PM rule.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.date} hover>
                  <TableCell>{r.date || "—"}</TableCell>
                  <TableCell>{r.login || "—"}</TableCell>
                  <TableCell>{r.logout || "—"}</TableCell>
                  <TableCell>{formatDurationSeconds(r.duration_seconds)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h6" sx={{ fontWeight: 800, color: ACCENT, mb: 0.5, letterSpacing: -0.2 }}>
        App sign-in activity
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, maxWidth: 640 }}>
        Web logins and logouts (multiple sessions in one day appear as separate rows).
      </Typography>
      <TableContainer
        component={Paper}
        elevation={0}
        sx={{ borderRadius: 2, border: 1, borderColor: "divider", overflow: "hidden" }}
      >
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: "action.hover" }}>
              <TableCell>When</TableCell>
              <TableCell>Event</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {authEvents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2} sx={{ py: 2 }}>
                  No sign-in events yet. They appear after you log in or out of the app.
                </TableCell>
              </TableRow>
            ) : (
              authEvents.map((ev) => (
                <TableRow key={ev.id} hover>
                  <TableCell>
                    {ev.created_at ? format(parseISO(ev.created_at), "MMM d, yyyy · h:mm:ss a") : "—"}
                  </TableCell>
                  <TableCell sx={{ textTransform: "capitalize" }}>
                    {ev.event === "login" ? "Login" : ev.event === "logout" ? "Logout" : ev.event}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

export default Attendance;
