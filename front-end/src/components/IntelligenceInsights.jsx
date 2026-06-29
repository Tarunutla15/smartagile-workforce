import React, { useCallback, useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Grid,
  LinearProgress,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import CodeOutlinedIcon from "@mui/icons-material/CodeOutlined";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import SubdirectoryArrowRightIcon from "@mui/icons-material/SubdirectoryArrowRight";
import TrendingUpOutlinedIcon from "@mui/icons-material/TrendingUpOutlined";
import { api } from "../api/client";

const severityColor = (sev) => {
  if (sev === "warning") return "warning";
  if (sev === "success") return "success";
  return "info";
};

function formatDurationSec(totalSec) {
  if (totalSec == null || !Number.isFinite(totalSec) || totalSec < 0) return "—";
  const s = Math.round(totalSec);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

function typeShort(st) {
  if (!st) return "";
  if (st === "application") return "app";
  if (st === "browser") return "web";
  return st;
}

function appLabel(name, st) {
  const t = typeShort(st);
  return t ? `${name} (${t})` : name;
}

function maxInList(items, getNum) {
  if (!items?.length) return 1;
  return Math.max(1, ...items.map((x) => getNum(x) || 0));
}

const accent = { main: "#4f46e5", light: "rgba(79, 70, 229, 0.12)", line: "rgba(79, 70, 229, 0.45)" };
const warm = { line: "rgba(217, 119, 6, 0.4)", bg: "rgba(245, 158, 11, 0.12)" };
const rankColor = (i) => {
  if (i === 0) return { bg: "rgba(79, 70, 229, 0.2)", fg: "#4338ca" };
  if (i === 1) return { bg: "rgba(100, 116, 139, 0.18)", fg: "#475569" };
  if (i === 2) return { bg: "rgba(180, 83, 9, 0.12)", fg: "#b45309" };
  return { bg: "action.hover", fg: "text.secondary" };
};

function AppTypeIcon({ st, fontSize = "small" }) {
  if (st === "browser") {
    return <OpenInNewOutlinedIcon sx={{ fontSize, opacity: 0.7 }} color="action" />;
  }
  return <CodeOutlinedIcon sx={{ fontSize, opacity: 0.7 }} color="action" />;
}

/**
 * @param {{ name: string, source_type: string, open_count: number, duration_seconds: number }[]} items
 * @param {'opens' | 'time'} mode
 */
function AppRankList({ items, mode }) {
  const getVal = mode === "opens" ? (a) => a.open_count : (a) => a.duration_seconds;
  const maxV = maxInList(items, getVal);

  return (
    <Stack spacing={1.25}>
      {items.map((a, i) => {
        const v = getVal(a);
        const pct = maxV > 0 ? (v / maxV) * 100 : 0;
        const rc = rankColor(i);
        return (
          <Box
            key={`${a.name}-${i}`}
            sx={{
              p: 1.25,
              pr: 1.5,
              borderRadius: 2,
              bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.85)"),
              border: 1,
              borderColor: "divider",
              position: "relative",
              overflow: "hidden",
              boxShadow: (t) => (t.palette.mode === "dark" ? "none" : "0 1px 0 rgba(15,23,42,0.04)"),
            }}
          >
            <Box
              sx={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                width: 3,
                borderRadius: "0 2px 2px 0",
                bgcolor: accent.main,
                opacity: 0.4 + (pct / 100) * 0.45,
              }}
            />
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Box
                sx={{
                  minWidth: 28,
                  height: 28,
                  borderRadius: 1,
                  display: "grid",
                  placeItems: "center",
                  fontSize: 13,
                  fontWeight: 800,
                  color: rc.fg,
                  bgcolor: rc.bg,
                }}
              >
                {i + 1}
              </Box>
              <AppTypeIcon st={a.source_type} />
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  noWrap
                  title={appLabel(a.name, a.source_type)}
                >
                  {a.name}
                </Typography>
                <Typography variant="caption" color="text.secondary" component="div">
                  {typeShort(a.source_type) || "app"} · {a.open_count} opens
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={pct}
                  sx={{
                    mt: 0.75,
                    height: 4,
                    borderRadius: 2,
                    bgcolor: (t) => t.palette.action.hover,
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 2,
                      bgcolor: mode === "opens" ? accent.main : "warning.main",
                    },
                  }}
                />
              </Box>
              <Box sx={{ textAlign: "right", flexShrink: 0 }}>
                {mode === "time" && (
                  <Typography variant="body2" fontWeight={800} sx={{ color: "warning.dark" }}>
                    {formatDurationSec(a.duration_seconds)}
                  </Typography>
                )}
                {mode === "opens" && (
                  <Typography variant="body2" fontWeight={800} color="primary">
                    {a.open_count}
                  </Typography>
                )}
                {mode === "time" && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    opens: {a.open_count}
                  </Typography>
                )}
                {mode === "opens" && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ maxWidth: 80 }}>
                    {formatDurationSec(a.duration_seconds)}
                  </Typography>
                )}
              </Box>
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}

function SwitchPairCarousel({ pairs }) {
  if (!pairs.length) return null;
  const maxC = maxInList(pairs, (p) => p.count);
  return (
    <Box sx={{ position: "relative" }}>
      <Box
        sx={{
          display: "flex",
          gap: 1.5,
          overflowX: "auto",
          pb: 0.5,
          scrollSnapType: "x mandatory",
          WebkitOverflowScrolling: "touch",
          "&::-webkit-scrollbar": { height: 6 },
          "&::-webkit-scrollbar-thumb": {
            borderRadius: 3,
            bgcolor: "action.disabled",
          },
        }}
      >
        {pairs.map((p, i) => {
          const w = maxC > 0 ? (p.count / maxC) * 100 : 0;
          return (
            <Card
              key={`${p.from_name}-${p.to_name}-${i}`}
              variant="outlined"
              elevation={0}
              sx={{
                minWidth: { xs: 260, sm: 280 },
                maxWidth: 300,
                flex: "0 0 auto",
                scrollSnapAlign: "start",
                borderRadius: 2,
                borderColor: (t) => t.palette.divider,
                background: (t) =>
                  t.palette.mode === "dark"
                    ? "linear-gradient(160deg, rgba(79, 70, 229,0.1) 0%, rgba(15,23,42,0.6) 100%)"
                    : "linear-gradient(160deg, rgba(79, 70, 229,0.08) 0%, #fff 50%)",
                boxShadow: "0 2px 12px rgba(15,23,42,0.06)",
              }}
            >
              <CardContent sx={{ py: 1.5, px: 1.75, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.25 }}>
                  <Chip
                    size="small"
                    icon={<DragIndicatorIcon sx={{ "&&": { fontSize: 16 } }} />}
                    label="Switch"
                    variant="outlined"
                    sx={{ fontWeight: 600, borderColor: accent.line }}
                  />
                  <Chip
                    size="small"
                    color="primary"
                    label={`${p.count}×`}
                    sx={{ fontWeight: 800, fontSize: "0.8rem" }}
                  />
                </Stack>
                <Stack spacing={0.5}>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: warm.bg,
                      border: 1,
                      borderColor: warm.line,
                    }}
                  >
                    <Stack direction="row" alignItems="center" gap={0.5}>
                      <SubdirectoryArrowRightIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        From
                      </Typography>
                    </Stack>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      noWrap
                      title={appLabel(p.from_name, p.from_source_type)}
                      sx={{ mt: 0.25, pl: 0.5 }}
                    >
                      {p.from_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ pl: 0.5 }}>
                      {typeShort(p.from_source_type) || "app"}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "center",
                      color: "primary.main",
                    }}
                  >
                    <SubdirectoryArrowRightIcon sx={{ transform: "rotate(90deg)", fontSize: 22, opacity: 0.6 }} />
                  </Box>
                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1,
                      bgcolor: (t) => t.palette.action.hover,
                      border: 1,
                      borderColor: "divider",
                    }}
                  >
                    <Stack direction="row" alignItems="center" gap={0.5}>
                      <TrendingUpOutlinedIcon sx={{ fontSize: 16, color: "primary.main" }} />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        To
                      </Typography>
                    </Stack>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      noWrap
                      title={appLabel(p.to_name, p.to_source_type)}
                      sx={{ mt: 0.25, pl: 0.5 }}
                    >
                      {p.to_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ pl: 0.5 }}>
                      {typeShort(p.to_source_type) || "app"}
                    </Typography>
                  </Box>
                </Stack>
                <LinearProgress
                  variant="determinate"
                  value={w}
                  sx={{
                    mt: 1.25,
                    height: 3,
                    borderRadius: 2,
                    bgcolor: "action.hover",
                    "& .MuiLinearProgress-bar": { borderRadius: 2, bgcolor: accent.main },
                  }}
                />
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
}

export default function IntelligenceInsights() {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [payload, setPayload] = useState(null);
  const today = format(new Date(), "yyyy-MM-dd");

  const toggleDetails = useCallback((e) => {
    e?.stopPropagation();
    setDetailsOpen((o) => !o);
  }, []);

  const load = useCallback(
    async (date = today) => {
      setLoading(true);
      setErr(null);
      try {
        const { data } = await api.get("/api/insights/summary/", {
          params: { date },
        });
        setPayload(data);
      } catch (e) {
        setErr(e?.response?.data?.error || e?.message || "Failed to load insights");
        setPayload(null);
      } finally {
        setLoading(false);
      }
    },
    [today]
  );

  useEffect(() => {
    load();
  }, [load]);

  const panelGradient = useMemo(
    () =>
      isDark
        ? "linear-gradient(135deg, rgba(79, 70, 229,0.15) 0%, rgba(15,23,42,0.95) 40%, #0f172a 100%)"
        : "linear-gradient(135deg, #eef2ff 0%, #ffffff 35%, #f8fafc 100%)",
    [isDark]
  );

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 1.5,
          py: 4,
          px: 2,
          borderRadius: 3,
          background: panelGradient,
          border: 1,
          borderColor: "divider",
        }}
      >
        <CircularProgress size={24} thickness={4} />
        <Typography variant="body2" color="text.secondary">
          Loading your intelligence snapshot…
        </Typography>
      </Box>
    );
  }

  if (err) {
    return (
      <Alert severity="error" sx={{ borderRadius: 2 }}>
        {err}
      </Alert>
    );
  }

  const f = payload?.features;
  const insights = Array.isArray(payload?.insights) ? payload.insights : [];
  const aa = payload?.app_activity || {};
  const pairs = Array.isArray(aa.top_switch_pairs) ? aa.top_switch_pairs : [];
  const opened = Array.isArray(aa.most_opened_apps) ? aa.most_opened_apps : [];
  const timeIn = Array.isArray(aa.most_time_in_apps) ? aa.most_time_in_apps : [];
  const hasActivity = f && (f.event_count > 0 || f.total_duration_seconds > 0);
  const hasAppDetail = pairs.length > 0 || opened.length > 0;

  return (
    <Box
      id="employee-intelligence"
      sx={{
        mb: 2,
        borderRadius: 3,
        border: 1,
        borderColor: "divider",
        background: panelGradient,
        boxShadow: isDark ? "0 4px 24px rgba(0,0,0,0.35)" : "0 4px 24px rgba(15, 23, 42, 0.06)",
        overflow: "hidden",
        position: "relative",
        scrollMarginTop: 24,
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          right: 0,
          width: { xs: 120, md: 200 },
          height: 120,
          background: (t) =>
            `radial-gradient(ellipse at top right, ${t.palette.mode === "dark" ? "rgba(79, 70, 229,0.25)" : "rgba(79, 70, 229,0.15)"} 0%, transparent 70%)`,
          pointerEvents: "none",
        },
      }}
    >
      <Box sx={{ p: { xs: 2, sm: 2.5 }, position: "relative", zIndex: 1 }}>
        <Box
          onClick={toggleDetails}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggleDetails(e);
            }
          }}
          role="button"
          tabIndex={0}
          aria-expanded={detailsOpen}
          aria-label={detailsOpen ? "Hide app activity and insight details" : "Show app activity and insight details"}
          sx={{
            borderRadius: 2,
            p: 1,
            mx: -1,
            cursor: "pointer",
            outline: "none",
            transition: "background-color 0.2s",
            "&:hover": { bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(79, 70, 229,0.06)") },
            "&:focus-visible": { boxShadow: (t) => `0 0 0 2px ${t.palette.primary.main}` },
            mb: 0.5,
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            flexWrap="nowrap"
            gap={1}
            sx={{ width: "100%" }}
          >
            <Stack direction="row" alignItems="center" spacing={1.5} flexWrap="wrap" useFlexGap sx={{ minWidth: 0, flex: 1 }}>
              <Box
                sx={{
                  width: 44,
                  height: 44,
                  borderRadius: 2,
                  display: "grid",
                  placeItems: "center",
                  flexShrink: 0,
                  bgcolor: accent.light,
                  border: 1,
                  borderColor: accent.line,
                  color: accent.main,
                }}
              >
                <AutoAwesomeOutlinedIcon />
              </Box>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1} useFlexGap>
                  <Typography
                    variant="h6"
                    sx={{
                      fontWeight: 800,
                      letterSpacing: -0.3,
                      lineHeight: 1.2,
                    }}
                  >
                    Intelligence
                  </Typography>
                  <Chip
                    size="small"
                    label={payload?.date || today}
                    variant="outlined"
                    onClick={(e) => e.stopPropagation()}
                    sx={{ fontWeight: 600 }}
                  />
                  {payload?.baseline_sample_days > 0 ? (
                    <Chip
                      size="small"
                      label={`${payload.baseline_sample_days}d baseline`}
                      variant="outlined"
                      onClick={(e) => e.stopPropagation()}
                      sx={{ fontWeight: 500, opacity: 0.9 }}
                    />
                  ) : null}
                </Stack>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5, maxWidth: 560, display: "block" }}
                >
                  {detailsOpen
                    ? "Context switches, ranked apps, and narrative tips below. Click this row to hide."
                    : "Click to show where you switched apps most, ranked usage, and full insight cards."}
                </Typography>
              </Box>
            </Stack>
            <ExpandMoreIcon
              color="action"
              sx={{
                flexShrink: 0,
                transform: detailsOpen ? "rotate(180deg)" : "rotate(0deg)",
                transition: (t) => t.transitions.create("transform", { duration: t.transitions.duration.shorter }),
              }}
            />
          </Stack>
        </Box>

        {hasActivity && (
          <Stack
            direction="row"
            flexWrap="wrap"
            gap={1}
            sx={{
              mb: 2.5,
              p: 1.25,
              borderRadius: 2,
              bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.7)"),
              border: 1,
              borderColor: (t) => t.palette.divider,
            }}
          >
            <Chip
              size="small"
              icon={<SpeedOutlinedIcon sx={{ "&&": { fontSize: 18 } }} />}
              label={f.focus_score != null ? `Focus ≈ ${Math.round(f.focus_score * 100)}%` : "Focus n/a"}
              color="default"
              sx={{ fontWeight: 700 }}
            />
            <Chip
              size="small"
              label={`${f.app_switch_count} context switches`}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`${f.deep_work_segment_count} deep-work blocks (15m+)`}
              variant="outlined"
            />
          </Stack>
        )}

        <Collapse
          in={detailsOpen}
          timeout="auto"
        >
          <Box>
            {hasAppDetail && (
              <Box sx={{ mb: 2.5 }}>
                <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1} sx={{ mb: 1.5 }}>
                  <Typography variant="subtitle2" fontWeight={800} color="text.secondary" letterSpacing={0.2}>
                    Where your attention goes
                  </Typography>
                </Stack>

                {pairs.length > 0 && (
                  <Box sx={{ mb: 2.5 }}>
                    <Stack direction="row" alignItems="center" gap={0.5} sx={{ mb: 1.25, ml: 0.25 }}>
                      <SubdirectoryArrowRightIcon sx={{ fontSize: 18, color: accent.main }} />
                      <Typography variant="body2" fontWeight={800}>
                        Most common app → app switches
                      </Typography>
                    </Stack>
                    <SwitchPairCarousel pairs={pairs} />
                  </Box>
                )}

                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    mb: 2,
                    border: 1,
                    borderColor: "divider",
                    bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.55)"),
                  }}
                >
                  <Stack direction="row" alignItems="center" gap={0.5} sx={{ mb: 2, ml: 0.25 }}>
                    <OpenInNewOutlinedIcon sx={{ color: "primary.main", fontSize: 20 }} />
                    <Typography fontWeight={800} variant="subtitle2">
                      Ranked apps: opens &amp; time
                    </Typography>
                  </Stack>
                  <Grid container spacing={2.5}>
                    {opened.length > 0 && (
                      <Grid item xs={12} md={6}>
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: 2,
                            bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(248,250,252,0.9)"),
                            border: 1,
                            borderColor: "divider",
                          }}
                        >
                          <Typography
                            variant="overline"
                            color="text.secondary"
                            display="block"
                            sx={{ mb: 1.5, letterSpacing: 1, fontWeight: 700 }}
                          >
                            Most often opened
                          </Typography>
                          <AppRankList items={opened} mode="opens" />
                        </Box>
                      </Grid>
                    )}
                    {timeIn.length > 0 && (
                      <Grid item xs={12} md={6}>
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: 2,
                            bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(0,0,0,0.2)" : "rgba(248,250,252,0.9)"),
                            border: 1,
                            borderColor: "divider",
                          }}
                        >
                          <Typography
                            variant="overline"
                            color="text.secondary"
                            display="block"
                            sx={{ mb: 1.5, letterSpacing: 1, fontWeight: 700 }}
                          >
                            Most time spent
                          </Typography>
                          <AppRankList items={timeIn} mode="time" />
                        </Box>
                      </Grid>
                    )}
                  </Grid>
                </Box>
              </Box>
            )}

            <Stack spacing={1.5} sx={{ pb: 0.5 }}>
              {insights.map((item) => (
                <Card
                  key={`${item.type}-${item.title}`}
                  variant="outlined"
                  sx={{
                    borderColor: (t) => t.palette.divider,
                    background: (t) =>
                      t.palette.mode === "dark" ? "rgba(15,23,42,0.4)" : "rgba(255,255,255,0.8)",
                    borderRadius: 2,
                    boxShadow: "none",
                  }}
                >
                  <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
                    <Stack
                      direction="row"
                      alignItems="flex-start"
                      justifyContent="space-between"
                      gap={1.5}
                    >
                      <Box>
                        <Typography variant="subtitle1" fontWeight={800}>
                          {item.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.5 }}>
                          {item.body}
                        </Typography>
                      </Box>
                      <Chip
                        size="small"
                        label={item.severity}
                        color={severityColor(item.severity)}
                        sx={{ textTransform: "capitalize", fontWeight: 600 }}
                      />
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </Box>
        </Collapse>
      </Box>
    </Box>
  );
}
