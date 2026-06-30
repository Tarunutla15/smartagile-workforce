import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import EastRoundedIcon from '@mui/icons-material/EastRounded';
import SouthRoundedIcon from '@mui/icons-material/SouthRounded';
import PersonAddAlt1RoundedIcon from '@mui/icons-material/PersonAddAlt1Rounded';
import PlayCircleFilledRoundedIcon from '@mui/icons-material/PlayCircleFilledRounded';
import StopCircleRoundedIcon from '@mui/icons-material/StopCircleRounded';
import TimerOutlinedIcon from '@mui/icons-material/TimerOutlined';
import ToggleButton from '@mui/material/ToggleButton';
import {
  getSprintBoard,
  getBacklog,
  getProjectMembers,
  getSprintItemEffort,
  getActiveTimer,
  startTimer,
  stopTimer,
  createWorkItem,
  updateWorkItem,
} from '../api/sprints';
import { useSprint } from '../Dashboards/SprintDBComponents/SprintContext';
import ItemDetailDrawer from '../Dashboards/SprintDBComponents/ItemDetailDrawer';

const STATUS_OPTIONS = [
  { value: 'todo', label: 'To Do' },
  { value: 'inProgress', label: 'In Progress' },
  { value: 'done', label: 'Done' },
];

const TYPE_OPTIONS = ['story', 'task', 'bug', 'chore', 'spike'];

const PRIORITY_COLOR = {
  urgent: '#dc2626',
  high: '#f59e0b',
  medium: '#6366f1',
  low: '#94a3b8',
  none: '#cbd5e1',
};

const TYPE_BG = {
  story: 'bg-emerald-50 text-emerald-700',
  task: 'bg-indigo-50 text-indigo-700',
  bug: 'bg-rose-50 text-rose-700',
  chore: 'bg-slate-100 text-slate-600',
  spike: 'bg-amber-50 text-amber-700',
};

function ItemCard({
  item, onStatus, onToBacklog, onAssignMe, onAssign, busy, currentUserId, canManage, members,
  effort, isTiming, onStartTimer, onStopTimer, onOpen,
}) {
  const mine = item.assignee && item.assignee.id === currentUserId;
  // Status is editable by managers (any task) or the assignee (their own task).
  const canEditStatus = canManage || mine;
  const focusH = effort?.focus_hours;
  return (
    <div className={`sa-card p-3 mb-2 ${isTiming ? 'ring-2 ring-emerald-400' : mine ? 'ring-1 ring-indigo-300' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={() => onOpen(item)}
          className="text-left text-sm font-semibold text-slate-800 hover:text-indigo-600 hover:underline dark:text-slate-100"
          title="Open details"
        >
          {item.title}
        </button>
        <span
          className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full"
          title={`Priority: ${item.priority}`}
          style={{ backgroundColor: PRIORITY_COLOR[item.priority] || PRIORITY_COLOR.none }}
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${TYPE_BG[item.item_type] || TYPE_BG.task}`}>
          {item.item_type}
        </span>
        {item.story_points != null && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
            {item.story_points} pts
          </span>
        )}
        {focusH > 0 && (
          <span
            className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700"
            title="Actual focus time tracked on this task"
          >
            <TimerOutlinedIcon sx={{ fontSize: 12 }} />
            {focusH}h
          </span>
        )}
        {!canManage &&
          (item.assignee ? (
            <span className={`text-[11px] ${mine ? 'font-semibold text-indigo-600' : 'text-slate-400'}`}>
              @{item.assignee.username}
            </span>
          ) : (
            <span className="text-[11px] italic text-slate-300">unassigned</span>
          ))}
        {isTiming && (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
            recording
          </span>
        )}
      </div>
      <div className="mt-2 flex items-center gap-1">
        <TextField
          select
          size="small"
          value={item.status}
          onChange={(e) => onStatus(item, e.target.value)}
          disabled={busy || !canEditStatus}
          sx={{ minWidth: 124, '& .MuiInputBase-input': { py: 0.5, fontSize: 12 } }}
        >
          {STATUS_OPTIONS.map((o) => (
            <MenuItem key={o.value} value={o.value} sx={{ fontSize: 12 }}>
              {o.label}
            </MenuItem>
          ))}
        </TextField>

        {/* Manager/admin: assign to anyone. Employee: self-assign only when unassigned. */}
        {canManage ? (
          <TextField
            select
            size="small"
            value={item.assignee?.id ?? ''}
            onChange={(e) => onAssign(item, e.target.value === '' ? null : Number(e.target.value))}
            disabled={busy}
            SelectProps={{ displayEmpty: true }}
            sx={{ minWidth: 120, '& .MuiInputBase-input': { py: 0.5, fontSize: 12 } }}
          >
            <MenuItem value="" sx={{ fontSize: 12, fontStyle: 'italic' }}>
              Unassigned
            </MenuItem>
            {members.map((m) => (
              <MenuItem key={m.id} value={m.id} sx={{ fontSize: 12 }}>
                {m.username}
              </MenuItem>
            ))}
          </TextField>
        ) : (
          !item.assignee && (
            <Tooltip title="Assign to me">
              <span>
                <IconButton size="small" color="primary" disabled={busy} onClick={() => onAssignMe(item)}>
                  <PersonAddAlt1RoundedIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </span>
            </Tooltip>
          )
        )}

        {/* Focus timer: only the assignee tracks their own work. */}
        {mine && (
          isTiming ? (
            <Tooltip title="Stop focus timer">
              <span>
                <IconButton size="small" color="error" disabled={busy} onClick={onStopTimer}>
                  <StopCircleRoundedIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </span>
            </Tooltip>
          ) : (
            <Tooltip title="Start focus timer (attributes your tracked time to this task)">
              <span>
                <IconButton size="small" color="success" disabled={busy} onClick={() => onStartTimer(item)}>
                  <PlayCircleFilledRoundedIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </span>
            </Tooltip>
          )
        )}

        {/* Moving items in/out of the sprint is planning -> managers only. */}
        {canManage && (
          <Tooltip title="Move to backlog">
            <span>
              <IconButton size="small" disabled={busy} onClick={() => onToBacklog(item)}>
                <SouthRoundedIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </span>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

const TaskBar = () => {
  const { user, projectId, sprintId, selectedSprint, canManage, refreshKey, notifyChange } = useSprint();
  const currentUserId = user?.id;
  const [columns, setColumns] = useState([]);
  const [backlog, setBacklog] = useState([]);
  const [members, setMembers] = useState([]);
  const [effortMap, setEffortMap] = useState({});
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [showBacklog, setShowBacklog] = useState(true);
  const [mine, setMine] = useState(false);
  const [draft, setDraft] = useState({ title: '', item_type: 'task', story_points: '' });
  const [detailItemId, setDetailItemId] = useState(null);

  const load = useCallback(async () => {
    if (!sprintId) {
      setColumns([]);
      setBacklog([]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [board, back, mem, eff, timer] = await Promise.all([
        getSprintBoard(sprintId),
        projectId ? getBacklog(projectId) : Promise.resolve([]),
        canManage && projectId ? getProjectMembers(projectId) : Promise.resolve([]),
        getSprintItemEffort(sprintId).catch(() => ({ items: {} })),
        getActiveTimer().catch(() => ({ active: false })),
      ]);
      setColumns(board.columns || []);
      setBacklog(back || []);
      setMembers(mem || []);
      setEffortMap(eff.items || {});
      setActiveTaskId(timer.active ? timer.task_id : null);
    } catch (e) {
      setError('Could not load the board.');
    } finally {
      setLoading(false);
    }
  }, [sprintId, projectId, canManage]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const mutate = async (fn, id) => {
    setBusyId(id ?? 'new');
    try {
      await fn();
      await load();
      notifyChange();
    } catch (e) {
      setError('Action failed.');
    } finally {
      setBusyId(null);
    }
  };

  const handleStatus = (item, status) =>
    mutate(() => updateWorkItem(item.id, { status }), item.id);

  const handleToBacklog = (item) =>
    mutate(() => updateWorkItem(item.id, { sprint: null }), item.id);

  const handleToSprint = (item) =>
    mutate(() => updateWorkItem(item.id, { sprint: sprintId }), item.id);

  const handleAssignMe = (item) =>
    mutate(() => updateWorkItem(item.id, { assignee_id: currentUserId }), item.id);

  const handleAssign = (item, assigneeId) =>
    mutate(() => updateWorkItem(item.id, { assignee_id: assigneeId }), item.id);

  const handleStartTimer = async (item) => {
    setBusyId(item.id);
    try {
      await startTimer(item.id);
      setActiveTaskId(item.id);
    } catch (e) {
      setError('Could not start timer.');
    } finally {
      setBusyId(null);
    }
  };

  const handleStopTimer = async () => {
    setBusyId(activeTaskId);
    try {
      await stopTimer();
      setActiveTaskId(null);
    } catch (e) {
      setError('Could not stop timer.');
    } finally {
      setBusyId(null);
    }
  };

  const visibleItems = (items) =>
    mine ? items.filter((i) => i.assignee && i.assignee.id === currentUserId) : items;

  const handleAdd = () => {
    if (!draft.title.trim() || !sprintId) return;
    mutate(
      () =>
        createWorkItem({
          project: projectId,
          sprint: sprintId,
          title: draft.title.trim(),
          item_type: draft.item_type,
          story_points: draft.story_points === '' ? null : Number(draft.story_points),
        }),
      'new'
    ).then(() => setDraft({ title: '', item_type: 'task', story_points: '' }));
  };

  if (!sprintId) {
    return (
      <div className="mx-auto max-w-[1280px]">
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Board</h1>
        <Alert severity="info" sx={{ mt: 2 }}>Select or create a sprint to use the board.</Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1280px]">
      <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
        Board
      </h1>
      <p className="mt-1 mb-3 text-sm text-slate-500 dark:text-slate-400">
        {selectedSprint?.name} · drag-free status updates and backlog planning.
      </p>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Quick add (managers/admin only); employees use "Assign to me" + status. */}
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
        {canManage && (
          <>
            <TextField
              size="small"
              placeholder="Add a work item…"
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              sx={{ minWidth: 260 }}
            />
            <TextField
              select
              size="small"
              value={draft.item_type}
              onChange={(e) => setDraft({ ...draft, item_type: e.target.value })}
              sx={{ minWidth: 110 }}
            >
              {TYPE_OPTIONS.map((t) => (
                <MenuItem key={t} value={t} sx={{ textTransform: 'capitalize' }}>
                  {t}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              type="number"
              placeholder="pts"
              value={draft.story_points}
              onChange={(e) => setDraft({ ...draft, story_points: e.target.value })}
              sx={{ width: 90 }}
            />
            <Button
              variant="contained"
              startIcon={<AddRoundedIcon />}
              onClick={handleAdd}
              disabled={!draft.title.trim() || busyId === 'new'}
            >
              Add
            </Button>
          </>
        )}
        <Box sx={{ flexGrow: 1 }} />
        <ToggleButton
          value="mine"
          selected={mine}
          onChange={() => setMine((v) => !v)}
          size="small"
          sx={{ textTransform: 'none' }}
        >
          Only my items
        </ToggleButton>
      </Stack>

      {loading && columns.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {columns.map((col) => {
            const items = visibleItems(col.items);
            return (
              <div key={col.key} className="sa-panel">
                <div className="mb-2 flex items-center justify-between">
                  <p className="sa-panel-title">{col.label}</p>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-500 dark:bg-slate-700 dark:text-slate-200">
                    {items.length}
                  </span>
                </div>
                {items.length === 0 ? (
                  <p className="py-6 text-center text-xs text-slate-400">Nothing here</p>
                ) : (
                  items.map((item) => (
                    <ItemCard
                      key={item.id}
                      item={item}
                      busy={busyId === item.id}
                      currentUserId={currentUserId}
                      canManage={canManage}
                      members={members}
                      effort={effortMap[item.id]}
                      isTiming={activeTaskId === item.id}
                      onStatus={handleStatus}
                      onToBacklog={handleToBacklog}
                      onAssignMe={handleAssignMe}
                      onAssign={handleAssign}
                      onStartTimer={handleStartTimer}
                      onStopTimer={handleStopTimer}
                      onOpen={(it) => setDetailItemId(it.id)}
                    />
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Backlog */}
      <Box sx={{ mt: 4 }}>
        <Button size="small" onClick={() => setShowBacklog((v) => !v)} sx={{ textTransform: 'none' }}>
          {showBacklog ? 'Hide' : 'Show'} backlog ({backlog.length})
        </Button>
        <Collapse in={showBacklog}>
          <div className="sa-card mt-2 p-3">
            {backlog.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                Backlog is empty.
              </Typography>
            ) : (
              backlog.map((item) => (
                <div key={item.id} className="flex items-center justify-between border-b border-slate-100 py-2 last:border-0 dark:border-slate-700">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${TYPE_BG[item.item_type] || TYPE_BG.task}`}>
                      {item.item_type}
                    </span>
                    <button
                      type="button"
                      onClick={() => setDetailItemId(item.id)}
                      className="text-left text-sm text-slate-700 hover:text-indigo-600 hover:underline dark:text-slate-200"
                    >
                      {item.title}
                    </button>
                    {item.story_points != null && (
                      <Chip size="small" label={`${item.story_points} pts`} variant="outlined" />
                    )}
                  </div>
                  {canManage && (
                    <Tooltip title="Add to current sprint">
                      <span>
                        <IconButton size="small" color="primary" disabled={busyId === item.id} onClick={() => handleToSprint(item)}>
                          <EastRoundedIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                </div>
              ))
            )}
          </div>
        </Collapse>
      </Box>

      <ItemDetailDrawer
        itemId={detailItemId}
        open={detailItemId != null}
        onClose={() => setDetailItemId(null)}
        members={members}
        onChanged={() => {
          load();
          notifyChange();
        }}
      />
    </div>
  );
};

export default TaskBar;
