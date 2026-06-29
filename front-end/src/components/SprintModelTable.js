import React from 'react';

const SPRINTS = [
  { num: 1, start: '2022-01-01', end: '2022-01-14', goal: 'Implement user authentication', status: 'Done' },
  { num: 2, start: '2022-01-15', end: '2022-01-28', goal: 'Develop user profile module', status: 'In progress' },
];

const statusClass = (status) =>
  status === 'Done'
    ? 'inline-flex items-center rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-semibold text-violet-700 ring-1 ring-inset ring-violet-600/15'
    : 'sa-chip';

const SprintModelTable = () => {
  return (
    <div className="mx-auto max-w-[1100px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprint model</h1>
      <p className="mt-1 mb-4 text-sm text-slate-500 dark:text-slate-400">Planned sprints, dates and goals.</p>
      <div className="sa-card overflow-hidden">
        <table className="sa-table">
          <thead>
            <tr>
              <th>Sprint</th>
              <th>Start date</th>
              <th>End date</th>
              <th>Goal</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {SPRINTS.map((s) => (
              <tr key={s.num}>
                <td className="font-bold text-slate-900 dark:text-slate-100">#{s.num}</td>
                <td className="tabular-nums text-slate-500 dark:text-slate-400">{s.start}</td>
                <td className="tabular-nums text-slate-500 dark:text-slate-400">{s.end}</td>
                <td className="font-medium text-slate-800 dark:text-slate-200">{s.goal}</td>
                <td>
                  <span className={statusClass(s.status)}>{s.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SprintModelTable;
