import React, { useCallback, useContext, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { PieChart } from "@mui/x-charts/PieChart";
import { Box, Stack, Typography, useMediaQuery, useTheme } from "@mui/material";
import BarChartOutlinedIcon from "@mui/icons-material/BarChartOutlined";
import { AppDataContext } from "../Dashboards/EmployeeDBComponent/AppDataProvider";

const ACCENT = "#0d9488";
const PIE_COLORS = [
  "#0d9488",
  "#2563eb",
  "#7c3aed",
  "#ea580c",
  "#db2777",
  "#ca8a04",
  "#4f46e5",
];

function formatMins(mins) {
  if (mins == null || !Number.isFinite(mins) || mins < 0) return "0 min";
  const m = Math.round(mins);
  if (m < 1) return "<1 min";
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (r === 0) return `${h} hr`;
  return `${h} hr ${r} min`;
}

/**
 * Donut only: hover = tooltip with time; click = app details (same route as before).
 */
export default function TopAppsWebsitesPanel() {
  const theme = useTheme();
  const isNarrow = useMediaQuery(theme.breakpoints.down("sm"));
  const navigate = useNavigate();
  const { filteredData, loading } = useContext(AppDataContext);

  /** Aggregated by app name; pie = top 7 + "Other" so the chart matches full-period desktop time. */
  const { allMins, pieRows, sliceColors } = useMemo(() => {
    if (!filteredData?.length) {
      return { allMins: 0, pieRows: [], sliceColors: [] };
    }
    const acc = {};
    for (const item of filteredData) {
      const key = (item.applicationname || "").trim().toLowerCase() || "—";
      const name = (item.applicationname || "").trim() || "—";
      const durationInMinutes = Number(item.duration) / 60;
      if (!acc[key]) acc[key] = { name, value: 0 };
      acc[key].value += durationInMinutes;
    }
    const sorted = Object.values(acc).sort((a, b) => b.value - a.value);
    const allMins = sorted.reduce((s, r) => s + r.value, 0);
    const top7 = sorted.slice(0, 7);
    const top7Sum = top7.reduce((s, r) => s + r.value, 0);
    const other = Math.max(0, allMins - top7Sum);
    const pieRows =
      other > 1e-6
        ? [
            ...top7,
            { name: "Other (remaining apps)", value: other, isOther: true },
          ]
        : [...top7];
    const sliceColors = pieRows.map((r, i) =>
      r.isOther ? "#64748b" : PIE_COLORS[i % PIE_COLORS.length]
    );
    return { allMins, pieRows, sliceColors };
  }, [filteredData]);

  const pieSeriesData = useMemo(
    () =>
      pieRows.map((r, i) => ({
        id: `app-${i}`,
        value: r.value,
        label: r.name.length > 40 ? `${r.name.slice(0, 38)}…` : r.name,
      })),
    [pieRows]
  );

  const handleItemClick = useCallback(
    (_event, identifier, item) => {
      const di =
        typeof identifier?.dataIndex === "number"
          ? identifier.dataIndex
          : typeof item?.dataIndex === "number"
            ? item.dataIndex
            : null;
      if (di == null || di < 0 || !pieRows[di] || pieRows[di].isOther) return;
      navigate(`/application-details/${encodeURIComponent(pieRows[di].name)}`);
    },
    [pieRows, navigate]
  );

  if (loading) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading…
      </Typography>
    );
  }

  if (!pieRows.length) {
    return (
      <Box
        sx={{
          py: 3,
          px: 2,
          textAlign: "center",
          borderRadius: 2,
          border: 1,
          borderColor: "divider",
          borderStyle: "dashed",
          bgcolor: (t) => (t.palette.mode === "dark" ? "action.hover" : "grey.50"),
        }}
      >
        <BarChartOutlinedIcon sx={{ color: "text.disabled", fontSize: 40, mb: 1 }} />
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 360, mx: "auto" }}>
          No app or site usage in this period. Try another date range, or make sure the desktop agent is
          running and sending data.
        </Typography>
      </Box>
    );
  }

  const chartSize = isNarrow ? 300 : 420;

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
          Share of <strong>active time</strong> in this period: <strong>top 7 apps</strong> plus{" "}
          <strong>Other</strong> when the rest of your time is outside those seven. <strong>Hover</strong> a
          slice for time and % of <em>all</em> app time; <strong>click</strong> a slice to open app
          details (not available for &quot;Other&quot;).
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block">
          Full period total (all apps):{" "}
          <strong style={{ color: ACCENT }}>{formatMins(allMins)}</strong>
        </Typography>
      </Box>

      <Box
        sx={{
          position: "relative",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: chartSize,
          maxWidth: "100%",
          borderRadius: 2,
          bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(0,0,0,0.25)" : "rgba(15, 23, 42, 0.03)"),
          border: 1,
          borderColor: "divider",
          py: { xs: 2, sm: 2.5 },
          px: 1,
          overflow: "hidden",
        }}
      >
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
            pointerEvents: "none",
            zIndex: 0,
            maxWidth: 160,
          }}
        >
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            sx={{ lineHeight: 1.2, textTransform: "uppercase", letterSpacing: 0.6, fontSize: 10 }}
          >
            Total
          </Typography>
          <Typography
            variant="h5"
            fontWeight={800}
            sx={{ color: ACCENT, lineHeight: 1.15, fontSize: { xs: "1.2rem", sm: "1.4rem" } }}
          >
            {formatMins(allMins)}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
            all apps, this period
          </Typography>
        </Box>

        <PieChart
          width={chartSize}
          height={chartSize}
          onItemClick={handleItemClick}
          margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
          colors={sliceColors}
          series={[
            {
              data: pieSeriesData,
              innerRadius: "40%",
              outerRadius: "88%",
              paddingAngle: 1.2,
              cornerRadius: 2,
              highlightScope: { fade: "global", highlighted: "item" },
              valueFormatter: (value, context) => {
                if (value == null) return "";
                const v = Number(value);
                if (!Number.isFinite(v)) return "";
                const timeStr = formatMins(v);
                const di = context?.dataIndex;
                if (di == null || allMins <= 0 || !pieRows[di]) return timeStr;
                const p = (pieRows[di].value / allMins) * 100;
                const pct = p < 0.5 ? "<1%" : `${p.toFixed(0)}%`;
                return `${timeStr} · ${pct} of all app time`;
              },
              arcLabel: () => "",
            },
          ]}
          slotProps={{
            legend: { hidden: true },
            tooltip: {
              trigger: "item",
            },
          }}
          sx={{
            position: "relative",
            zIndex: 1,
            maxWidth: "100%",
            cursor: "default",
            "& path": { cursor: "pointer" },
            "& .MuiPieArc-path": { cursor: "pointer" },
          }}
        />
      </Box>
    </Stack>
  );
}
