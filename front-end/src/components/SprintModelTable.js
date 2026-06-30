import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import DoneAllRoundedIcon from '@mui/icons-material/DoneAllRounded';
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded';
import { createSprint, startSprint, completeSprint } from '../api/sprints';
import { useSprint } from '../Dashboards/SprintDBComponents/SprintContext';

const STATUS = {
  planned: 'sa-chip',
  active: 'inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/15',
  completed: 'inline-flex items-center rounded-full bg-violet-50 px-2.5 py-0.5 text-xs font-semibold text-violet-700 ring-1 ring-inset ring-violet-600/15',
};

const SprintModelTable = () => {
  const {
    projectId,
    selectedProject,
    sprints,
    sprintId,
    setSprintId,
    loadingSprints,
    canManage,
    notifyChange,
  } = useSprint();

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', goal: '', start_date: '', end_date: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  const resetForm = () => setForm({ name: '', goal: '', start_date: '', end_date: '' });

  const handleCreate = async () => {
    if (!projectId || !form.name.trim()) return;
    setSaving(true);
    setError('');
    try {
      await createSprint({
        project: projectId,
        name: form.name.trim(),
        goal: form.goal.trim(),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      });
      setOpen(false);
      resetForm();
      notifyChange();
    } catch (e) {
      setError(e?.response?.data?.error || 'Could not create sprint.');
    } finally {
      setSaving(false);
    }
  };

  const handleStart = async (id) => {
    setBusyId(id);
    try {
      await startSprint(id);
      notifyChange();
    } finally {
      setBusyId(null);
    }
  };

  const handleComplete = async (id) => {
    setBusyId(id);
    try {
      await completeSprint(id, 'backlog');
      notifyChange();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto max-w-[1100px]">
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, mb: 2 }}>
        <Box>
          <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Sprints</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {selectedProject ? selectedProject.name : 'Select a project'} · plan, start and close sprints.
          </p>
        </Box>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<AddRoundedIcon />}
            onClick={() => setOpen(true)}
            disabled={!projectId}
          >
            New sprint
          </Button>
        )}
      </Box>

      {loadingSprints ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : sprints.length === 0 ? (
        <Alert severity="info">No sprints yet for this project.{canManage ? ' Create one to get started.' : ''}</Alert>
      ) : (
        <div className="sa-card overflow-hidden">
          <table className="sa-table">
            <thead>
              <tr>
                <th>Sprint</th>
                <th>Start</th>
                <th>End</th>
                <th>Points</th>
                <th>Done</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sprints.map((s) => (
                <tr key={s.id} className={s.id === sprintId ? 'bg-indigo-50/40' : undefined}>
                  <td className="font-bold text-slate-900 dark:text-slate-100">
                    {s.name}
                    {s.goal ? (
                      <span className="block text-xs font-normal text-slate-400">{s.goal}</span>
                    ) : null}
                  </td>
                  <td className="tabular-nums text-slate-500 dark:text-slate-400">{s.start_date || '—'}</td>
                  <td className="tabular-nums text-slate-500 dark:text-slate-400">{s.end_date || '—'}</td>
                  <td className="tabular-nums text-slate-700 dark:text-slate-300">{s.total_points}</td>
                  <td className="tabular-nums text-slate-700 dark:text-slate-300">
                    {s.done_count}/{s.item_count}
                  </td>
                  <td>
                    <span className={STATUS[s.status] || 'sa-chip'}>{s.status}</span>
                  </td>
                  <td>
                    <Stack direction="row" spacing={0.5}>
                      <Tooltip title="View on dashboard">
                        <IconButton size="small" onClick={() => setSprintId(s.id)}>
                          <VisibilityRoundedIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {canManage && s.status === 'planned' && (
                        <Tooltip title="Start sprint">
                          <span>
                            <IconButton size="small" color="success" disabled={busyId === s.id} onClick={() => handleStart(s.id)}>
                              <PlayArrowRoundedIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      {canManage && s.status === 'active' && (
                        <Tooltip title="Complete sprint (move unfinished to backlog)">
                          <span>
                            <IconButton size="small" color="primary" disabled={busyId === s.id} onClick={() => handleComplete(s.id)}>
                              <DoneAllRoundedIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </Stack>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New sprint</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Goal"
              value={form.goal}
              onChange={(e) => setForm({ ...form, goal: e.target.value })}
              fullWidth
              multiline
              minRows={2}
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="Start date"
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
              <TextField
                label="End date"
                type="date"
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              Committed points are snapshotted when you start the sprint.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving || !form.name.trim()}>
            {saving ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default SprintModelTable;
