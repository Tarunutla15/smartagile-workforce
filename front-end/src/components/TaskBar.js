import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { BRAND_CHART_COLORS } from '../utils/chartTheme';

ChartJS.register(ArcElement, Tooltip, Legend);

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, font: { size: 11 } } },
  },
};

const makeData = (label, labels, values) => ({
  labels,
  datasets: [
    {
      label,
      data: values,
      backgroundColor: BRAND_CHART_COLORS,
      borderColor: '#fff',
      borderWidth: 2,
    },
  ],
});

const SECTIONS = [
  makeData('Completed tasks', ['Task 1', 'Task 2', 'Task 3', 'Task 4', 'Task 5'], [20, 30, 40, 50, 60]),
  makeData('DoD checklist', ['Criteria 1', 'Criteria 2', 'Criteria 3', 'Criteria 4', 'Criteria 5'], [40, 30, 20, 50, 60]),
  makeData('Acceptance criteria', ['Criteria A', 'Criteria B', 'Criteria C', 'Criteria D', 'Criteria E'], [60, 25, 45, 30, 50]),
  makeData('Comments & discussions', ['Positive', 'Neutral', 'Negative', 'Feedback', 'Suggestions'], [45, 30, 25, 40, 35]),
  makeData('Attachments & resources', ['Image', 'Document', 'Link', 'Video', 'Audio'], [50, 25, 35, 45, 30]),
  makeData('Peer reviews', ['Positive', 'Neutral', 'Negative', 'Feedback', 'Suggestions'], [40, 30, 30, 35, 45]),
];

const TITLES = [
  'Completed tasks (closed)',
  'Definition of Done (DoD) checklist',
  'Acceptance criteria',
  'Comments and discussions',
  'Attachments and resources',
  'Peer reviews',
];

const TaskBar = () => {
  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Task breakdown</h1>
      <p className="mt-1 mb-4 text-sm text-slate-500 dark:text-slate-400">Distribution across task quality and review dimensions.</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((data, i) => (
          <div key={TITLES[i]} className="sa-panel sa-card-hover">
            <p className="sa-panel-title mb-2">{TITLES[i]}</p>
            <div style={{ height: 260 }}>
              <Pie data={data} options={pieOptions} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TaskBar;
