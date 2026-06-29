import React from 'react';
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

// Registering required elements with Chart.js
ChartJS.register(LineElement, PointElement, LinearScale, Title, CategoryScale, Tooltip, Legend);

const SprintBurndownChart = () => {
  const data = {
    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7', 'Day 8', 'Day 9', 'Day 10'],
    datasets: [
      {
        label: 'Actual burndown',
        data: [100, 94, 81, 76, 65, 58, 44, 33, 26, 14],
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.12)',
        pointBackgroundColor: '#4f46e5',
        tension: 0.35,
        fill: true,
      },
      {
        label: 'Ideal burndown',
        data: [100, 90, 80, 70, 60, 50, 40, 30, 20, 10],
        borderColor: '#94a3b8',
        backgroundColor: '#94a3b8',
        borderDash: [6, 6],
        pointRadius: 0,
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true, font: { weight: '600' } } },
      title: { display: false },
    },
    scales: {
      x: { title: { display: true, text: 'Days' }, grid: { display: false } },
      y: {
        title: { display: true, text: 'Remaining work (hours)' },
        beginAtZero: true,
        grid: { color: 'rgba(15,23,42,0.06)' },
      },
    },
  };

  return (
    <div className="mx-auto max-w-[1000px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint burndown</h1>
      <p className="mt-1 mb-4 text-sm text-slate-500 dark:text-slate-400">Remaining work vs the ideal trajectory across the sprint.</p>
      <div className="sa-card p-5" style={{ height: 420 }}>
        <Line data={data} options={options} />
      </div>
    </div>
  );
};

export default SprintBurndownChart;
