import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { Alert, Box, CircularProgress } from '@mui/material';
import { getSprintBurndown } from '../api/sprints';
import { useSprint } from '../Dashboards/SprintDBComponents/SprintContext';

ChartJS.register(LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip, Legend);

const options = {
  responsive: true,
  maintainAspectRatio: false,
  spanGaps: false,
  plugins: {
    legend: { position: 'top', labels: { usePointStyle: true, font: { weight: '600' } } },
    title: { display: false },
  },
  scales: {
    x: { title: { display: true, text: 'Day' }, grid: { display: false } },
    y: {
      title: { display: true, text: 'Remaining points' },
      beginAtZero: true,
      grid: { color: 'rgba(15,23,42,0.06)' },
    },
  },
};

const SprintBurndownChart = () => {
  const { sprintId, selectedSprint, refreshKey } = useSprint();
  const [bd, setBd] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sprintId) {
      setBd(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError('');
    getSprintBurndown(sprintId)
      .then((data) => active && setBd(data))
      .catch(() => active && setError('Could not load burndown.'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [sprintId, refreshKey]);

  const data = bd && {
    labels: bd.days,
    datasets: [
      {
        label: 'Ideal',
        data: bd.ideal,
        borderColor: '#94a3b8',
        backgroundColor: '#94a3b8',
        borderDash: [6, 6],
        pointRadius: 0,
        fill: false,
      },
      {
        label: 'Actual',
        data: bd.actual,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.12)',
        pointBackgroundColor: '#4f46e5',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  return (
    <div className="mx-auto max-w-[1000px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint burndown</h1>
      <p className="mt-1 mb-4 text-sm text-slate-500 dark:text-slate-400">
        {selectedSprint ? selectedSprint.name : 'Active sprint'} · remaining points vs the ideal trajectory
        {bd ? ` · committed ${bd.committed_points} pts` : ''}.
      </p>

      {!sprintId ? (
        <Alert severity="info">Select or create a sprint to see its burndown.</Alert>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : loading && !bd ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <div className="sa-card p-5" style={{ height: 420 }}>
          {data && <Line data={data} options={options} />}
        </div>
      )}
    </div>
  );
};

export default SprintBurndownChart;
