import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  CircularProgress,
  Paper,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { PieChart } from "@mui/x-charts/PieChart";
import { LineChart, lineElementClasses } from "@mui/x-charts/LineChart";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, LabelList, ResponsiveContainer,
} from "recharts";
import { BRAND_CHART_COLORS } from "../../utils/chartTheme";
import { getOrgSummary } from "../../api/sprints";

const Panel = ({ title, subtitle, children }) => (
  <Paper sx={{ p: 2, borderRadius: 2, flex: 1, minWidth: 0 }}>
    <Typography variant="overline" color="text.secondary">{title}</Typography>
    {subtitle && (
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        {subtitle}
      </Typography>
    )}
    {children}
  </Paper>
);

const Empty = ({ text = "No data in this range" }) => (
  <Box sx={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
    <Typography variant="body2" color="text.disabled">{text}</Typography>
  </Box>
);

export default function AdminOverviewCharts() {
  const [days, setDays] = useState(14);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSummary(await getOrgSummary({ days }));
    } catch (e) {
      setError("Could not load org analytics.");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  const t = summary?.totals;
  const members = summary?.members || [];
  const productivityData = members
    .filter((m) => m.focus_hours > 0)
    .map((m, i) => ({ id: i, value: m.focus_hours, label: m.username }));
  const projData = (summary?.project_status?.labels || []).map((name, i) => ({
    name,
    Completion: summary.project_status.completion[i],
  }));
  const perfData = members.map((m) => ({ name: m.username, Productivity: m.productivity_pct }));
  const office = summary?.time_tracking?.office_hours || [];
  const trendFocus = summary?.team_trend?.focus_hours || [];
  const dist = (summary?.task_distribution?.labels || [])
    .map((label, i) => ({ label, value: summary.task_distribution.values[i] }))
    .filter((d) => d.value > 0);

  return (
    <Box sx={{ mt: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: "text.primary" }}>
          Org analytics
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={days}
          onChange={(e, v) => v && setDays(v)}
        >
          <ToggleButton value={7} sx={{ textTransform: "none" }}>7d</ToggleButton>
          <ToggleButton value={14} sx={{ textTransform: "none" }}>14d</ToggleButton>
          <ToggleButton value={30} sx={{ textTransform: "none" }}>30d</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading && !summary ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : summary ? (
        <>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
            <Panel title="Active people">
              <Typography variant="h4">{t.active_people}<Typography component="span" variant="body2" color="text.secondary"> / {t.people}</Typography></Typography>
            </Panel>
            <Panel title="Focus hours">
              <Typography variant="h4" sx={{ color: "#10b981" }}>{t.focus_hours}h</Typography>
            </Panel>
            <Panel title="Productivity">
              <Typography variant="h4" sx={{ color: "#0ea5e9" }}>{t.productivity_pct}%</Typography>
            </Panel>
            <Panel title="Tasks">
              <Typography variant="h4" sx={{ color: "#f59e0b" }}>
                {t.done_tasks}<Typography component="span" variant="body2" color="text.secondary"> done · {t.open_tasks} open</Typography>
              </Typography>
            </Panel>
          </Stack>

          <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2 }}>
            <Panel title="Top performers" subtitle="Focus hours per person">
              {productivityData.length === 0 ? (
                <Empty text="No focus time tracked yet" />
              ) : (
                <PieChart
                  colors={BRAND_CHART_COLORS}
                  series={[
                    {
                      data: productivityData,
                      highlightScope: { faded: "global", highlighted: "item" },
                      faded: { innerRadius: 30, additionalRadius: -30, color: "gray" },
                      valueFormatter: (v) => `${v.value}h`,
                    },
                  ]}
                  slotProps={{
                    legend: { direction: "column", position: { vertical: "bottom", horizontal: "right" }, padding: 0 },
                  }}
                  height={220}
                />
              )}
            </Panel>
            <Panel title="Project status" subtitle="Completion % per project">
              {projData.length === 0 ? (
                <Empty text="No projects with tasks yet" />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={projData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="orgBarA" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#818cf8" stopOpacity={0.95} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
                    <YAxis domain={[0, 100]} hide />
                    <Tooltip cursor={{ fill: "rgba(79, 70, 229,0.06)" }} formatter={(v) => `${v}%`} />
                    <Bar dataKey="Completion" fill="url(#orgBarA)" barSize={40} radius={[12, 12, 0, 0]}>
                      <LabelList dataKey="Completion" position="top" formatter={(v) => `${v}%`} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Panel>
            <Panel title="Time tracking" subtitle="Org hours by weekday">
              {office.some((v) => v > 0) ? (
                <LineChart
                  height={220}
                  colors={BRAND_CHART_COLORS}
                  series={[{ data: office, label: "Hours tracked", area: true, showMark: false }]}
                  xAxis={[{ scaleType: "point", data: summary.time_tracking.labels }]}
                  sx={{ [`& .${lineElementClasses.root}`]: { display: "none" } }}
                />
              ) : (
                <Empty />
              )}
            </Panel>
          </Stack>

          <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
            <Panel title="Productivity by person" subtitle="Focus / tracked %">
              {perfData.length === 0 ? (
                <Empty />
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={perfData} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}>
                    <defs>
                      <linearGradient id="orgBarB" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.95} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
                    <YAxis domain={[0, 100]} hide />
                    <Tooltip cursor={{ fill: "rgba(79, 70, 229,0.06)" }} formatter={(v) => `${v}%`} />
                    <Bar dataKey="Productivity" fill="url(#orgBarB)" barSize={32} radius={[12, 12, 0, 0]}>
                      <LabelList dataKey="Productivity" position="top" formatter={(v) => `${v}%`} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Panel>
            <Panel title="Org focus trend" subtitle="Daily focus hours">
              {trendFocus.some((v) => v > 0) ? (
                <LineChart
                  height={240}
                  colors={BRAND_CHART_COLORS}
                  series={[{ data: trendFocus, label: "Focus hours" }]}
                  xAxis={[{ scaleType: "point", data: summary.team_trend.labels }]}
                />
              ) : (
                <Empty />
              )}
            </Panel>
            <Panel title="Task distribution" subtitle="Work items by status">
              {dist.length === 0 ? (
                <Empty text="No tasks yet" />
              ) : (
                <PieChart
                  colors={BRAND_CHART_COLORS}
                  series={[{ data: dist, innerRadius: 40, outerRadius: 90 }]}
                  height={240}
                  slotProps={{ legend: { hidden: false } }}
                />
              )}
            </Panel>
          </Stack>
        </>
      ) : null}
    </Box>
  );
}
