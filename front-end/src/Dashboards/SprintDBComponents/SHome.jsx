import React, { useEffect, useState } from 'react';
import { LineChart } from '@mui/x-charts/LineChart';
import { BarChart } from '@mui/x-charts/BarChart';
import { Gauge, gaugeClasses } from '@mui/x-charts/Gauge';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { BRAND_CHART_COLORS } from '../../utils/chartTheme';
import { getSprintReport, getSprintEffort } from '../../api/sprints';
import { useSprint } from './SprintContext';

const hours = (h) => (h == null ? '0' : Number(h).toFixed(1));

const StatCard = ({ label, value, unit }) => (
  <div className="sa-card sa-card-hover flex-1 min-w-[160px] p-4">
    <p className="sa-stat-label">{label}</p>
    <p className="sa-stat-value">
      {value}
      {unit ? <span className="ml-1 text-base font-semibold text-slate-400">{unit}</span> : null}
    </p>
  </div>
);

const Panel = ({ title, subtitle, children }) => (
  <div className="sa-panel flex-1 min-w-[300px]">
    <p className="sa-panel-title">{title}</p>
    {subtitle ? <p className="mt-0.5 mb-2 text-xs text-slate-500">{subtitle}</p> : <div className="mb-2" />}
    {children}
  </div>
);

const SHome = () => {
  const { sprintId, selectedSprint, refreshKey } = useSprint();
  const [report, setReport] = useState(null);
  const [effort, setEffort] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sprintId) {
      setReport(null);
      setEffort(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([getSprintReport(sprintId), getSprintEffort(sprintId)])
      .then(([rep, eff]) => {
        if (!active) return;
        setReport(rep);
        setEffort(eff);
      })
      .catch(() => active && setError('Could not load sprint analytics.'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [sprintId, refreshKey]);

  if (!sprintId) {
    return (
      <div className="mx-auto max-w-[1280px]">
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint overview</h1>
        <Alert severity="info" sx={{ mt: 2 }}>
          No sprint selected. Create one in the <strong>Sprints</strong> tab to see velocity, burndown and focus time.
        </Alert>
      </div>
    );
  }

  const summary = report?.summary;
  const velocity = report?.velocity;
  const burndown = report?.burndown;
  const distribution = report?.distribution;

  const statCards = [
    { label: 'Sprint velocity', value: velocity ? velocity.average_velocity : '—', unit: 'pts' },
    { label: 'Office time', value: hours(effort?.office_hours), unit: 'h' },
    { label: 'Focus time', value: hours(effort?.focus_hours), unit: 'h' },
    { label: 'Open tasks', value: summary ? summary.open_count : '—', unit: '' },
    { label: 'Completion', value: summary ? summary.completion_pct : '—', unit: '%' },
  ];

  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint overview</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {selectedSprint ? selectedSprint.name : 'Active sprint'} · velocity, burndown and focus time.
      </p>

      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

      {loading && !report ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <div className="mt-5 flex flex-wrap gap-3">
            {statCards.map((c) => (
              <StatCard key={c.label} {...c} />
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-4">
            <Panel title="Velocity" subtitle="Commitment vs completed points per sprint">
              <VelocityChart velocity={velocity} />
            </Panel>
            <Panel title="Burndown" subtitle="Ideal vs actual remaining points">
              <BurnDownChart burndown={burndown} />
            </Panel>
            <Panel title="Completion" subtitle="Share of sprint items done">
              <CompletionGauge value={summary?.completion_pct ?? 0} />
            </Panel>
          </div>

          <div className="mt-4 flex flex-wrap gap-4">
            <Panel title="Work-item distribution" subtitle="Planned vs completed by type">
              <DistributionChart distribution={distribution} />
            </Panel>
          </div>
        </>
      )}
    </div>
  );
};

const EmptyChart = ({ height = 280 }) => (
  <Box sx={{ display: 'grid', placeItems: 'center', height }}>
    <span className="text-sm text-slate-400">No data yet</span>
  </Box>
);

const VelocityChart = ({ velocity }) => {
  if (!velocity || !velocity.labels?.length) return <EmptyChart />;
  return (
    <BarChart
      height={280}
      colors={BRAND_CHART_COLORS}
      xAxis={[{ data: velocity.labels, scaleType: 'band' }]}
      series={[
        { data: velocity.commitment, label: 'Commitment' },
        { data: velocity.completed, label: 'Completed' },
      ]}
    />
  );
};

const BurnDownChart = ({ burndown }) => {
  if (!burndown || !burndown.days?.length) return <EmptyChart />;
  return (
    <LineChart
      height={280}
      colors={['#94a3b8', '#4f46e5']}
      xAxis={[{ scaleType: 'point', data: burndown.days }]}
      series={[
        { data: burndown.ideal, label: 'Ideal', showMark: false },
        { data: burndown.actual, label: 'Actual', showMark: false, connectNulls: false },
      ]}
    />
  );
};

const CompletionGauge = ({ value }) => (
  <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 240 }}>
    <Gauge
      value={Math.round(value)}
      startAngle={-110}
      endAngle={110}
      height={220}
      width={260}
      sx={{
        [`& .${gaugeClasses.valueText}`]: { fontSize: 36, fontWeight: 800 },
        [`& .${gaugeClasses.valueArc}`]: { fill: '#4f46e5' },
      }}
      text={({ value: v }) => `${v}%`}
    />
  </Box>
);

const DistributionChart = ({ distribution }) => {
  if (!distribution || !distribution.labels?.length) return <EmptyChart height={360} />;
  return (
    <BarChart
      height={360}
      colors={BRAND_CHART_COLORS}
      xAxis={[{ data: distribution.labels, scaleType: 'band' }]}
      series={[
        { data: distribution.planned, label: 'Planned' },
        { data: distribution.completed, label: 'Completed' },
      ]}
    />
  );
};

export default SHome;
