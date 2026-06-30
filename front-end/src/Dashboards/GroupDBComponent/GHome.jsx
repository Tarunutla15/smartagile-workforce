import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { PieChart } from '@mui/x-charts/PieChart';
import { LineChart, lineElementClasses } from '@mui/x-charts/LineChart';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, LabelList, ResponsiveContainer,
} from 'recharts';
import { BRAND_CHART_COLORS } from '../../utils/chartTheme';
import { listGroups, getGroupSummary } from '../../api/sprints';

const Panel = ({ title, subtitle, children, className = '' }) => (
  <div className={`sa-panel sa-card-hover ${className}`}>
    <p className="sa-panel-title mb-0.5">{title}</p>
    {subtitle && <p className="mb-2 text-xs text-slate-400">{subtitle}</p>}
    {children}
  </div>
);

const StatCard = ({ label, value, accent }) => (
  <div className="sa-card p-4">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
    <p className="mt-1 text-2xl font-bold" style={{ color: accent || '#0f172a' }}>{value}</p>
  </div>
);

const EmptyChart = ({ text = 'No data in this range' }) => (
  <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <span className="text-sm text-slate-400">{text}</span>
  </Box>
);

const GHome = () => {
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState('');
  const [days, setDays] = useState(14);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const gs = await listGroups();
        setGroups(gs);
        if (gs.length) setGroupId(gs[0].id);
        else setLoading(false);
      } catch (e) {
        setError('Could not load your groups.');
        setLoading(false);
      }
    })();
  }, []);

  const load = useCallback(async () => {
    if (!groupId) return;
    setLoading(true);
    setError('');
    try {
      const data = await getGroupSummary(groupId, { days });
      setSummary(data);
    } catch (e) {
      setError('Could not load this group.');
    } finally {
      setLoading(false);
    }
  }, [groupId, days]);

  useEffect(() => {
    load();
  }, [load]);

  const totals = summary?.totals;
  const members = summary?.members || [];

  return (
    <div className="mx-auto max-w-[1280px]">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {summary?.group?.name ? summary.group.name : 'Group dashboard'}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Team productivity, project status and focus time — live from the desktop agent.
          </p>
        </div>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <TextField
            select
            size="small"
            label="Group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
            sx={{ minWidth: 200 }}
            disabled={!groups.length}
          >
            {groups.map((g) => (
              <MenuItem key={g.id} value={g.id}>{g.name}</MenuItem>
            ))}
          </TextField>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={days}
            onChange={(e, v) => v && setDays(v)}
          >
            <ToggleButton value={7} sx={{ textTransform: 'none' }}>7d</ToggleButton>
            <ToggleButton value={14} sx={{ textTransform: 'none' }}>14d</ToggleButton>
            <ToggleButton value={30} sx={{ textTransform: 'none' }}>30d</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      </div>

      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

      {!groups.length && !loading && !error && (
        <Alert severity="info" sx={{ mt: 2 }}>
          You're not part of any project team yet. Ask an admin to add you to a project.
        </Alert>
      )}

      {loading && !summary ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : summary ? (
        <>
          {/* Stat cards */}
          <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Team members" value={totals.member_count} accent="#4f46e5" />
            <StatCard label="Focus hours" value={`${totals.focus_hours}h`} accent="#10b981" />
            <StatCard label="Productivity" value={`${totals.productivity_pct}%`} accent="#0ea5e9" />
            <StatCard
              label="Tasks"
              value={`${totals.done_tasks} done · ${totals.open_tasks} open`}
              accent="#f59e0b"
            />
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Productivity members={members} />
            <ProjectStatus status={summary.project_status} />
            <TimeTracking tracking={summary.time_tracking} />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Performance members={members} />
            <TeamProductivity trend={summary.team_trend} />
            <TaskDistribution dist={summary.task_distribution} />
          </div>
        </>
      ) : null}
    </div>
  );
};

const Productivity = ({ members }) => {
  const data = members
    .filter((m) => m.focus_hours > 0)
    .map((m, i) => ({ id: i, value: m.focus_hours, label: m.username }));
  return (
    <Panel title="Productivity" subtitle="Focus hours per member">
      {data.length === 0 ? (
        <EmptyChart text="No focus time tracked yet" />
      ) : (
        <PieChart
          colors={BRAND_CHART_COLORS}
          series={[
            {
              data,
              highlightScope: { faded: 'global', highlighted: 'item' },
              faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
              valueFormatter: (v) => `${v.value}h`,
            },
          ]}
          slotProps={{
            legend: { direction: 'column', position: { vertical: 'bottom', horizontal: 'right' }, padding: 0 },
          }}
          height={220}
        />
      )}
    </Panel>
  );
};

const ProjectStatus = ({ status }) => {
  const data = (status?.labels || []).map((name, i) => ({
    name,
    ProjectCompletion: status.completion[i],
  }));
  return (
    <Panel title="Sprint status" subtitle="Completion % per sprint">
      {data.length === 0 ? (
        <EmptyChart text="No sprints yet" />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="brandBarA" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#818cf8" stopOpacity={0.95} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
              </linearGradient>
            </defs>
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis domain={[0, 100]} hide />
            <Tooltip cursor={{ fill: 'rgba(79, 70, 229,0.06)' }} formatter={(v) => `${v}%`} />
            <Bar dataKey="ProjectCompletion" fill="url(#brandBarA)" barSize={40} radius={[12, 12, 0, 0]}>
              <LabelList dataKey="ProjectCompletion" position="top" formatter={(v) => `${v}%`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Panel>
  );
};

const TimeTracking = ({ tracking }) => {
  const office = tracking?.office_hours || [];
  const hasData = office.some((v) => v > 0);
  return (
    <Panel title="Time tracking" subtitle="Team hours by weekday">
      {!hasData ? (
        <EmptyChart />
      ) : (
        <LineChart
          height={220}
          colors={BRAND_CHART_COLORS}
          series={[{ data: office, label: 'Hours tracked', area: true, showMark: false }]}
          xAxis={[{ scaleType: 'point', data: tracking.labels }]}
          sx={{ [`& .${lineElementClasses.root}`]: { display: 'none' } }}
        />
      )}
    </Panel>
  );
};

const Performance = ({ members }) => {
  const data = members.map((m) => ({ name: m.username, Performance: m.productivity_pct }));
  return (
    <Panel title="Performance summary" subtitle="Productivity % per member">
      {data.length === 0 ? (
        <EmptyChart />
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}>
            <defs>
              <linearGradient id="brandBarB" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.95} />
                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
              </linearGradient>
            </defs>
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis domain={[0, 100]} hide />
            <Tooltip cursor={{ fill: 'rgba(79, 70, 229,0.06)' }} formatter={(v) => `${v}%`} />
            <Bar dataKey="Performance" fill="url(#brandBarB)" barSize={36} radius={[12, 12, 0, 0]}>
              <LabelList dataKey="Performance" position="top" formatter={(v) => `${v}%`} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Panel>
  );
};

const TeamProductivity = ({ trend }) => {
  const focus = trend?.focus_hours || [];
  const hasData = focus.some((v) => v > 0);
  return (
    <Panel title="Team productivity" subtitle="Daily focus hours">
      {!hasData ? (
        <EmptyChart />
      ) : (
        <LineChart
          height={240}
          colors={BRAND_CHART_COLORS}
          series={[{ data: focus, label: 'Focus hours' }]}
          xAxis={[{ scaleType: 'point', data: trend.labels }]}
        />
      )}
    </Panel>
  );
};

const TaskDistribution = ({ dist }) => {
  const data = (dist?.labels || [])
    .map((label, i) => ({ label, value: dist.values[i] }))
    .filter((d) => d.value > 0);
  return (
    <Panel title="Task distribution" subtitle="Work items by status">
      {data.length === 0 ? (
        <EmptyChart text="No tasks yet" />
      ) : (
        <PieChart
          colors={BRAND_CHART_COLORS}
          series={[{ data, innerRadius: 40, outerRadius: 90 }]}
          height={240}
          slotProps={{ legend: { hidden: false } }}
        />
      )}
    </Panel>
  );
};

export default GHome;
