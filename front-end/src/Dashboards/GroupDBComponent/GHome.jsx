import React from 'react';
import { PieChart } from '@mui/x-charts/PieChart';
import {
  BarChart, Bar, XAxis, Tooltip, Legend, LabelList, ResponsiveContainer,
} from 'recharts';
import { LineChart, lineElementClasses } from '@mui/x-charts/LineChart';
import { BRAND_CHART_COLORS } from '../../utils/chartTheme';

const Panel = ({ title, children, className = '' }) => (
  <div className={`sa-panel sa-card-hover ${className}`}>
    <p className="sa-panel-title mb-2">{title}</p>
    {children}
  </div>
);

const GHome = () => {
  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Welcome to Group A</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Team productivity, project status and attendance at a glance.</p>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Productivity />
        <ProjectStatus />
        <TimeTracking />
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Performance />
        <TeamProductivity />
        <Attendance />
      </div>
    </div>
  );
};

const data = [
  { id: 0, value: 75, label: 'Emp1' },
  { id: 1, value: 85, label: 'Emp2' },
  { id: 2, value: 50, label: 'Emp3' },
  { id: 3, value: 80, label: 'Emp4' },
  { id: 4, value: 60, label: 'Emp5' },
];

const Productivity = () => (
  <Panel title="Productivity">
    <PieChart
      colors={BRAND_CHART_COLORS}
      series={[
        {
          data,
          highlightScope: { faded: 'global', highlighted: 'item' },
          faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
        },
      ]}
      slotProps={{
        legend: { direction: 'column', position: { vertical: 'bottom', horizontal: 'right' }, padding: 0 },
      }}
      height={220}
    />
  </Panel>
);

const projectData = [
  { name: 'Project A', ProjectCompletion: 70 },
  { name: 'Project B', ProjectCompletion: 45 },
  { name: 'Project C', ProjectCompletion: 85 },
];

const ProjectStatus = () => (
  <Panel title="Project status">
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={projectData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="brandBarA" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#818cf8" stopOpacity={0.95} />
            <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
          </linearGradient>
        </defs>
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip cursor={{ fill: 'rgba(79, 70, 229,0.06)' }} />
        <Legend />
        <Bar dataKey="ProjectCompletion" fill="url(#brandBarA)" barSize={40} radius={[12, 12, 0, 0]}>
          <LabelList dataKey="ProjectCompletion" position="top" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </Panel>
);

const uData = [10, 3, 12, 8, 15];
const xLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

const TimeTracking = () => (
  <Panel title="Time tracking">
    <LineChart
      height={220}
      colors={BRAND_CHART_COLORS}
      series={[{ data: uData, label: 'Hours worked', area: true, showMark: false }]}
      xAxis={[{ scaleType: 'point', data: xLabels }]}
      sx={{ [`& .${lineElementClasses.root}`]: { display: 'none' } }}
    />
  </Panel>
);

const performanceData = [
  { name: 'Emp 1', Performance: 90 },
  { name: 'Emp 2', Performance: 85 },
  { name: 'Emp 3', Performance: 80 },
  { name: 'Emp 4', Performance: 95 },
  { name: 'Emp 5', Performance: 88 },
];

const Performance = () => (
  <Panel title="Performance summary">
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={performanceData} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}>
        <defs>
          <linearGradient id="brandBarB" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.95} />
            <stop offset="95%" stopColor="#4f46e5" stopOpacity={0.95} />
          </linearGradient>
        </defs>
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip cursor={{ fill: 'rgba(79, 70, 229,0.06)' }} />
        <Legend />
        <Bar dataKey="Performance" fill="url(#brandBarB)" barSize={36} radius={[12, 12, 0, 0]}>
          <LabelList dataKey="Performance" position="top" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </Panel>
);

const productivity = [85, 88, 90, 92];
const week = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];

const TeamProductivity = () => (
  <Panel title="Team productivity">
    <LineChart
      height={240}
      colors={BRAND_CHART_COLORS}
      series={[{ data: productivity, label: 'Group productivity' }]}
      xAxis={[{ scaleType: 'point', data: week }]}
    />
  </Panel>
);

const attendance = [
  { label: 'Present', value: 80 },
  { label: 'Absent', value: 10 },
  { label: 'On leave', value: 5 },
];

const Attendance = () => (
  <Panel title="Attendance">
    <PieChart
      colors={BRAND_CHART_COLORS}
      series={[{ data: attendance, innerRadius: 40, outerRadius: 90 }]}
      height={240}
      slotProps={{ legend: { hidden: false } }}
    />
  </Panel>
);

export default GHome;
