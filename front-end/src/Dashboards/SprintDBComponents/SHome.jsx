import React from 'react';
import { LineChart, lineElementClasses } from '@mui/x-charts/LineChart';
import { BarChart } from '@mui/x-charts/BarChart';
import { Gauge, gaugeClasses } from '@mui/x-charts/Gauge';
import { PieChart } from '@mui/x-charts/PieChart';
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';
import { BRAND_CHART_COLORS } from '../../utils/chartTheme';

const STAT_CARDS = [
  { label: 'Sprint velocity', value: '23', unit: 'pts' },
  { label: 'Office time', value: '08:39', unit: 'h' },
  { label: 'Focus time', value: '06:12', unit: 'h' },
  { label: 'Open tasks', value: '14', unit: '' },
  { label: 'Completion', value: '78', unit: '%' },
];

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
  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint overview</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Velocity, burndown and task health for the active sprint.</p>

      <div className="mt-5 flex flex-wrap gap-3">
        {STAT_CARDS.map((c) => (
          <StatCard key={c.label} {...c} />
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-4">
        <Panel title="Velocity" subtitle="Commitment vs work completed per sprint">
          <VelocityChart />
        </Panel>
        <Panel title="Burndown" subtitle="Ideal vs actual remaining work">
          <BurnDownChart />
        </Panel>
        <Panel title="Task progress" subtitle="Share of sprint tasks done">
          <TaskProgress />
        </Panel>
      </div>

      <div className="mt-4 flex flex-wrap gap-4">
        <Panel title="Task distribution" subtitle="Planned vs completed by category">
          <TasksCharts />
        </Panel>
      </div>
    </div>
  );
};

const velocityProps = {
  height: 280,
  colors: BRAND_CHART_COLORS,
  xAxis: [{ data: ['Sprint 1', 'Sprint 2', 'Sprint 3', 'Sprint 4', 'Sprint 5'], scaleType: 'band' }],
};

const VelocityChart = () => (
  <BarChart
    {...velocityProps}
    series={[
      { data: [15, 20, 25, 27, 23], label: 'Commitment' },
      { data: [15, 15, 20, 26, 20], label: 'Work completed' },
    ]}
  />
);

const uData = [23, 90, 70, 50, 25, 0];
const pData = [65, 90, 80, 55, 45, 30];
const xLabels = ['1 Apr', '3 Apr', '5 Apr', '7 Apr', '9 Apr', '11 Apr'];

const BurnDownChart = () => (
  <LineChart
    height={280}
    colors={BRAND_CHART_COLORS}
    series={[
      { data: uData, label: 'Ideal', area: true, stack: 'total', showMark: false },
      { data: pData, label: 'Actual', area: true, stack: 'total', showMark: false },
    ]}
    xAxis={[{ scaleType: 'point', data: xLabels }]}
    sx={{ [`& .${lineElementClasses.root}`]: { display: 'none' } }}
  />
);

const TaskProgress = () => (
  <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 240 }}>
    <Gauge
      value={75}
      startAngle={-110}
      endAngle={110}
      height={220}
      width={260}
      sx={{
        [`& .${gaugeClasses.valueText}`]: { fontSize: 36, fontWeight: 800 },
        [`& .${gaugeClasses.valueArc}`]: { fill: '#4f46e5' },
      }}
      text={({ value }) => `${value}%`}
    />
  </Box>
);

const barChartsParams = {
  series: [
    { data: [68, 32, 8], label: 'Planned' },
    { data: [55, 23, 10], label: 'Completed' },
  ],
  height: 360,
  colors: BRAND_CHART_COLORS,
  xAxis: [{ data: ['Feature', 'Bug', 'Chore'], scaleType: 'band' }],
};

const pieChartsParams = {
  series: [
    {
      data: [
        { value: 68.16, label: 'Feature' },
        { value: 12.34, label: 'Bug' },
        { value: 7.34, label: 'Chore' },
        { value: 4.75, label: 'Spike' },
        { value: 3.75, label: 'Docs' },
        { value: 3.66, label: 'Other' },
      ],
      outerRadius: 120,
      innerRadius: 64,
      highlighted: { additionalRadius: 8 },
    },
  ],
  height: 360,
  colors: BRAND_CHART_COLORS,
  margin: { top: 20, bottom: 20 },
};

const TasksCharts = () => {
  const [chartType, setChartType] = React.useState('bar');
  const highlighted = 'item';
  const faded = 'global';

  const handleChartType = (event, newChartType) => {
    if (newChartType !== null) setChartType(newChartType);
  };

  return (
    <Stack spacing={1.5}>
      <ToggleButtonGroup
        value={chartType}
        exclusive
        onChange={handleChartType}
        aria-label="chart type"
        size="small"
        sx={{
          alignSelf: 'flex-start',
          '& .MuiToggleButton-root': {
            textTransform: 'capitalize',
            px: 2,
            borderColor: 'rgba(79, 70, 229,0.3)',
            color: '#4338ca',
            '&.Mui-selected': { bgcolor: 'rgba(79, 70, 229,0.12)', color: '#4338ca' },
          },
        }}
      >
        {['bar', 'pie'].map((type) => (
          <ToggleButton key={type} value={type}>
            {type}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      {chartType === 'bar' && (
        <BarChart
          {...barChartsParams}
          series={barChartsParams.series.map((s) => ({ ...s, highlightScope: { highlighted, faded } }))}
        />
      )}
      {chartType === 'pie' && (
        <PieChart
          {...pieChartsParams}
          series={pieChartsParams.series.map((s) => ({ ...s, highlightScope: { highlighted, faded } }))}
        />
      )}
    </Stack>
  );
};

export default SHome;
