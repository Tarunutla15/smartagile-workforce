import React, { useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppDataContext } from '../Dashboards/EmployeeDBComponent/AppDataProvider';
import { isWorkRelatedCategory } from '../utils/workRelatedCategory';

const formatDuration = (durationInMinutes) => {
    const hours = Math.floor(durationInMinutes / 60); // Get the whole number of hours
    const minutes = Math.round(durationInMinutes % 60); // Get the remaining minutes after hours
  
    if (hours > 0 && minutes > 0) {
      return `${hours}hr ${minutes}min`; // If both hours and minutes are present
    } else if (hours > 0) {
      return `${hours}hr`; // If only hours
    } else {
      return `${minutes}min`; // If only minutes
    }
  };

const Shell = ({ children }) => (
  <div className="sa-surface relative overflow-hidden">
    <div className="absolute inset-0 sa-landing-mesh pointer-events-none" aria-hidden />
    <div className="relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-6">{children}</div>
  </div>
);

const ApplicationDetails = () => {
  const { filteredData, loading } = useContext(AppDataContext);
  const { appName } = useParams();
  const navigate = useNavigate();

  const filteredAppData = (filteredData || []).filter(
    (item) => item.applicationname?.trim().toLowerCase() === appName.trim().toLowerCase()
  );

  const sortedAppData = [...filteredAppData].sort(
    (a, b) => new Date(b.date) - new Date(a.date)
  );

  const BackLink = () => (
    <button
      type="button"
      onClick={() => navigate(-1)}
      className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-700 transition-colors hover:text-indigo-900"
    >
      <span aria-hidden>&larr;</span> Back
    </button>
  );

  if (loading) {
    return (
      <Shell>
        <BackLink />
        <div className="sa-card p-8 text-center text-slate-500">Loading…</div>
      </Shell>
    );
  }

  if (sortedAppData.length === 0) {
    return (
      <Shell>
        <BackLink />
        <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{appName}</h1>
        <div className="sa-card mt-4 p-8 text-center text-slate-500">
          No usage data found for this application in the selected period.
        </div>
      </Shell>
    );
  }

  const totalSeconds = sortedAppData.reduce((acc, r) => acc + (Number(r.duration) || 0), 0);

  return (
    <Shell>
      <BackLink />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="sa-stat-label">Application details</p>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{appName}</h1>
        </div>
        <div className="sa-card px-4 py-2 text-right">
          <p className="sa-stat-label">Total tracked</p>
          <p className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50">
            {formatDuration(Math.ceil(totalSeconds / 60))}
          </p>
        </div>
      </div>

      <div className="sa-card mt-5 overflow-hidden">
        <table className="sa-table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Category</th>
              <th>Duration</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {sortedAppData.map((item, index) => (
              <tr key={index}>
                <td className="font-medium text-slate-800 dark:text-slate-200">{item.task || '—'}</td>
                <td>
                  <span
                    className={
                      isWorkRelatedCategory(item.category)
                        ? 'sa-chip'
                        : 'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-slate-500/15'
                    }
                  >
                    {item.category || 'uncategorized'}
                  </span>
                </td>
                <td className="tabular-nums">{formatDuration(Math.ceil(item.duration / 60))}</td>
                <td className="text-slate-500">{item.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
};

export default ApplicationDetails;
