import React, { useContext, useMemo, useState, useCallback, Fragment } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Button,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  CircularProgress,
  Typography,
  Alert,
  Stack,
  Chip,
  Tooltip,
  Collapse,
  IconButton,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import { format } from "date-fns";
import {
  Mail as MailIcon,
  Code as CodeIcon,
  Work as WorkIcon,
  LinkedIn as LinkedInIcon,
  VideoCall as VideoCallIcon,
  YouTube as YouTubeIcon,
  InsertChart as InsertChartIcon,
  Assessment as AssessmentIcon,
  GitHub as GitHubIcon,
  ViewList as ViewListIcon,
  Chat as ChatIcon,
  ChromeReaderModeOutlined as ChromeIcon,
} from "@mui/icons-material";
import "./styles.css";
import { AppDataContext } from "./AppDataProvider";
import { isWorkRelatedCategory } from "../../utils/workRelatedCategory";

const ACCENT = "#4f46e5";

const getIcon = (app) => {
  switch (app) {
    case "Slack":
      return <ChatIcon sx={{ color: "#4A154B", fontSize: 22 }} />;
    case "Gmail":
      return <MailIcon sx={{ color: "#D93025", fontSize: 22 }} />;
    case "Google Chrome":
      return <ChromeIcon sx={{ color: "#D93025", fontSize: 22 }} />;
    case "Visual Studio Code":
      return <CodeIcon sx={{ color: "#007ACC", fontSize: 22 }} />;
    case "JIRA":
      return <WorkIcon sx={{ color: "#0052CC", fontSize: 22 }} />;
    case "Chrome (LinkedIn)":
      return <LinkedInIcon sx={{ color: "#0A66C2", fontSize: 22 }} />;
    case "Excel":
      return <AssessmentIcon sx={{ color: "#217346", fontSize: 22 }} />;
    case "Zoom":
      return <VideoCallIcon sx={{ color: "#2D8CFF", fontSize: 22 }} />;
    case "Chrome (YouTube)":
      return <YouTubeIcon sx={{ color: "#FF0000", fontSize: 22 }} />;
    case "Outlook":
      return <MailIcon sx={{ color: "#0078D4", fontSize: 22 }} />;
    case "PowerPoint":
      return <InsertChartIcon sx={{ color: "#D24726", fontSize: 22 }} />;
    case "GitHub":
      return <GitHubIcon sx={{ color: "#000000", fontSize: 22 }} />;
    case "Trello":
      return <ViewListIcon sx={{ color: "#0079BF", fontSize: 22 }} />;
    default:
      return <MonitorHeartOutlinedIcon sx={{ color: "text.disabled", fontSize: 22 }} />;
  }
};

function rowYmd(row) {
  if (row?.date == null) return "";
  const s = String(row.date);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  return format(new Date(s), "yyyy-MM-dd");
}

const EmployeeActivityTable = () => {
  const {
    dateFilter,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    filteredData,
    loading,
    lastUpdated,
    handleDateFilterChange,
    applyDateFilter,
    refetch,
  } = useContext(AppDataContext);

  const [expandedByApp, setExpandedByApp] = useState({});

  const groups = useMemo(() => {
    const byApp = new Map();
    for (const row of filteredData) {
      const app = (row.applicationname || "").trim() || "Unknown app";
      if (!byApp.has(app)) byApp.set(app, []);
      const sec = Math.max(0, Math.round(Number(row.duration) || 0));
      byApp.get(app).push({ ...row, _sec: sec });
    }
    const out = [];
    for (const [app, rows] of byApp) {
      const totalSec = rows.reduce((a, r) => a + r._sec, 0);
      const taskRows = [...rows].sort((a, b) => b._sec - a._sec);
      const productiveSec = taskRows
        .filter((r) => isWorkRelatedCategory(r.category))
        .reduce((a, r) => a + r._sec, 0);
      const pct =
        totalSec > 0 ? Math.round((productiveSec / totalSec) * 100) : 0;
      const ymds = new Set(taskRows.map((r) => rowYmd(r)).filter(Boolean));
      const cats = new Set(taskRows.map((r) => (r.category || "").trim()).filter(Boolean));
      let dateLabel = "—";
      if (ymds.size === 1) dateLabel = [...ymds][0];
      else if (ymds.size > 1) dateLabel = "Multiple days";
      const categorySummary =
        cats.size === 0 ? "—" : cats.size === 1 ? [...cats][0] : "Mixed";
      out.push({
        app,
        taskRows,
        totalSec,
        focusPct: pct,
        dateLabel,
        categorySummary,
      });
    }
    out.sort((a, b) => b.totalSec - a.totalSec);
    return out;
  }, [filteredData]);

  const toggleApp = useCallback((app) => {
    setExpandedByApp((prev) => ({ ...prev, [app]: !prev[app] }));
  }, []);

  const formatDuration = (secondsTotal) => {
    const s = Math.max(0, Math.round(Number(secondsTotal) || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) {
      return `${h}h ${m}m ${sec}s`;
    }
    if (m > 0) {
      return `${m}m ${sec}s`;
    }
    return `${sec}s`;
  };

  if (loading && filteredData.length === 0) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress size={32} thickness={4} sx={{ color: ACCENT }} />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1280, mx: "auto", width: "100%", px: { xs: 0, sm: 0.5 } }}>
      <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ xs: "stretch", sm: "center" }} justifyContent="space-between" gap={2} sx={{ mb: 2.5 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: -0.3 }}>
            Usage log
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 560 }}>
            Grouped by app: total time on each app; expand a row to see every window or tab (longest time first) for
            that app.
          </Typography>
        </Box>
      </Stack>

      <Alert
        severity="info"
        sx={{
          mb: 2.5,
          borderRadius: 2,
          border: 1,
          borderColor: (t) => (t.palette.mode === "dark" ? "info.dark" : "info.light"),
        }}
      >
        Recorded by a <strong>Windows</strong> desktop tracker on the same PC as the app; it reads the active window
        (apps and browser titles). Remote or Linux servers won&apos;t see local activity. If nothing appears, check the
        Django console, then sign out and back in.
      </Alert>

      {!loading && filteredData.length === 0 && (
        <Alert severity="warning" sx={{ mb: 2.5, borderRadius: 2 }}>
          No rows for this period. Try <strong>This week</strong> or <strong>Custom</strong> dates, click{" "}
          <strong>Apply</strong>, or <strong>Refresh now</strong>. Use a few apps after login so the agent can write
          events.
        </Alert>
      )}

      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2.5,
          borderRadius: 2.5,
          border: 1,
          borderColor: "divider",
          background: (t) =>
            t.palette.mode === "dark" ? "rgba(15,23,42,0.5)" : "linear-gradient(180deg, #f8fffe 0%, #fff 100%)",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          flexWrap="wrap"
          useFlexGap
          spacing={1.5}
          alignItems={{ xs: "stretch", md: "center" }}
          justifyContent="space-between"
        >
          <Stack direction="row" alignItems="center" flexWrap="wrap" useFlexGap gap={1.5}>
            {lastUpdated && (
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Updated {format(lastUpdated, "HH:mm:ss")}
              </Typography>
            )}
            <Button
              startIcon={<RefreshIcon />}
              variant="outlined"
              size="small"
              onClick={() => refetch?.()}
              sx={{ textTransform: "none", fontWeight: 700, borderRadius: 2 }}
            >
              Refresh now
            </Button>
          </Stack>
          <Stack direction="row" flexWrap="wrap" useFlexGap spacing={1} alignItems="center" justifyContent={{ xs: "flex-start", md: "flex-end" }}>
            <FormControl size="small" variant="outlined" sx={{ minWidth: 150 }}>
              <InputLabel id="usage-date-filter">Period</InputLabel>
              <Select
                labelId="usage-date-filter"
                value={dateFilter}
                onChange={handleDateFilterChange}
                label="Period"
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
                  label="From"
                  type="date"
                  size="small"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  label="To"
                  type="date"
                  size="small"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </>
            )}
            <Button
              variant="contained"
              onClick={applyDateFilter}
              sx={{ bgcolor: ACCENT, textTransform: "none", fontWeight: 700, borderRadius: 2, px: 2, "&:hover": { bgcolor: "#4338ca" } }}
            >
              Apply
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <TableContainer
        component={Paper}
        elevation={0}
        sx={{ borderRadius: 2, border: 1, borderColor: "divider", overflow: "hidden" }}
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}>
                App / site
              </TableCell>
              <TableCell sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}>
                Sessions
              </TableCell>
              <TableCell sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}>
                Category
              </TableCell>
              <TableCell
                align="right"
                sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}
              >
                Duration
              </TableCell>
              <TableCell sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}>
                Work %
              </TableCell>
              <TableCell sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.100") }}>
                Date
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups.length === 0 && !loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 6, color: "text.secondary" }}>
                  No data for this period
                </TableCell>
              </TableRow>
            ) : (
              groups.map((g) => {
                const open = Boolean(expandedByApp[g.app]);
                const n = g.taskRows.length;
                return (
                  <Fragment key={g.app}>
                    <TableRow
                      hover
                      onClick={() => toggleApp(g.app)}
                      sx={{ cursor: "pointer" }}
                      aria-expanded={open}
                    >
                      <TableCell sx={{ py: 1.5, maxWidth: 240, borderBottom: open ? 0 : undefined }}>
                        <Stack direction="row" alignItems="center" gap={0.5}>
                          <IconButton
                            size="small"
                            aria-label={open ? "Hide tasks" : "Show tasks"}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleApp(g.app);
                            }}
                            sx={{
                              transform: open ? "rotate(180deg)" : "rotate(0deg)",
                              transition: (theme) => theme.transitions.create("transform", { duration: 200 }),
                            }}
                          >
                            <ExpandMoreIcon fontSize="small" />
                          </IconButton>
                          <Box
                            sx={{
                              width: 40,
                              height: 40,
                              borderRadius: 1.5,
                              display: "grid",
                              placeItems: "center",
                              flexShrink: 0,
                              bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.50"),
                              border: 1,
                              borderColor: "divider",
                            }}
                          >
                            {getIcon(g.app)}
                          </Box>
                          <Typography variant="body2" fontWeight={700} noWrap title={g.app}>
                            {g.app}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell sx={{ py: 1.5, color: "text.secondary", maxWidth: 200 }}>
                        <Typography variant="body2" noWrap>
                          {n} window{n === 1 ? "" : "s"}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: 1.5, maxWidth: 160 }}>
                        <Chip
                          size="small"
                          label={g.categorySummary}
                          variant="outlined"
                          sx={{ fontWeight: 500, maxWidth: "100%", borderColor: "divider" }}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ py: 1.5, whiteSpace: "nowrap" }}>
                        <Tooltip
                          title={`${g.totalSec.toLocaleString()} seconds across ${n} window${n === 1 ? "" : "s"}`}
                          arrow
                        >
                          <Typography component="span" fontWeight={800} color="primary" sx={{ cursor: "help" }}>
                            {formatDuration(g.totalSec)}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ py: 1.5 }}>
                        <Tooltip
                          title="Share of time in work-related categories for this app (by duration)"
                          enterDelay={400}
                          arrow
                        >
                          <Chip
                            size="small"
                            label={`${g.focusPct}% work`}
                            color={g.focusPct >= 50 ? "success" : "default"}
                            variant={g.focusPct >= 50 ? "filled" : "outlined"}
                            sx={{ fontWeight: 700, minWidth: 72 }}
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ py: 1.5, color: "text.secondary", fontWeight: 500 }}>{g.dateLabel}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        sx={{
                          p: 0,
                          borderBottom: (t) => `1px solid ${t.palette.divider}`,
                        }}
                      >
                        <Collapse in={open} timeout="auto" unmountOnExit>
                          <Box
                            sx={{
                              px: 2,
                              py: 1.5,
                              pl: { xs: 1, sm: 2 },
                              ml: { xs: 0, sm: 1 },
                              borderLeft: (t) => `3px solid ${t.palette.mode === "dark" ? t.palette.divider : ACCENT}`,
                              bgcolor: (t) =>
                                t.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(79, 70, 229, 0.06)",
                            }}
                          >
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ display: "block", mb: 1, fontWeight: 700, letterSpacing: 0.3 }}
                            >
                              Per window / tab — longest time first
                            </Typography>
                            <Table size="small" sx={{ "& .MuiTableCell-root": { borderColor: "divider" } }}>
                              <TableHead>
                                <TableRow>
                                  <TableCell sx={{ fontWeight: 700, py: 1, fontSize: "0.7rem" }}>Task / title</TableCell>
                                  <TableCell sx={{ fontWeight: 700, py: 1, fontSize: "0.7rem", width: 120 }}>Category</TableCell>
                                  <TableCell
                                    align="right"
                                    sx={{ fontWeight: 700, py: 1, fontSize: "0.7rem", width: 100 }}
                                  >
                                    Time
                                  </TableCell>
                                  <TableCell sx={{ fontWeight: 700, py: 1, fontSize: "0.7rem", width: 90 }}>Productive</TableCell>
                                  <TableCell sx={{ fontWeight: 700, py: 1, fontSize: "0.7rem", width: 100 }}>Date</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {g.taskRows.map((row, index) => {
                                  const productive = isWorkRelatedCategory(row.category);
                                  return (
                                    <TableRow
                                      key={`${g.app}-task-${row.task}-${rowYmd(row)}-${index}`}
                                      hover
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <TableCell sx={{ py: 1, maxWidth: 300 }}>
                                        <Tooltip title={row.task || "—"} enterDelay={400} placement="top" arrow>
                                          <Typography variant="body2" noWrap sx={{ cursor: "default" }}>
                                            {row.task || "—"}
                                          </Typography>
                                        </Tooltip>
                                      </TableCell>
                                      <TableCell sx={{ py: 1 }}>
                                        <Chip
                                          size="small"
                                          label={row.category || "—"}
                                          variant="outlined"
                                          sx={{ fontWeight: 500, maxWidth: 180, borderColor: "divider" }}
                                        />
                                      </TableCell>
                                      <TableCell align="right" sx={{ py: 1, whiteSpace: "nowrap" }}>
                                        <Tooltip title={`${row._sec.toLocaleString()} seconds`} arrow>
                                          <Typography
                                            component="span"
                                            fontWeight={700}
                                            color="primary"
                                            sx={{ cursor: "help" }}
                                          >
                                            {formatDuration(row._sec)}
                                          </Typography>
                                        </Tooltip>
                                      </TableCell>
                                      <TableCell sx={{ py: 1 }}>
                                        <Chip
                                          size="small"
                                          label={productive ? "Yes" : "No"}
                                          color={productive ? "success" : "default"}
                                          variant={productive ? "filled" : "outlined"}
                                          sx={{ fontWeight: 700, minWidth: 40 }}
                                        />
                                      </TableCell>
                                      <TableCell sx={{ py: 1, color: "text.secondary", fontSize: "0.8125rem" }}>
                                        {row.date ? format(new Date(row.date), "yyyy-MM-dd") : "—"}
                                      </TableCell>
                                    </TableRow>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </Fragment>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default EmployeeActivityTable;
