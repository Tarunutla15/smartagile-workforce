import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Stack,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Skeleton,
  Snackbar,
  Alert,
  Chip,
  alpha,
  useTheme,
} from "@mui/material";
import AddTaskRoundedIcon from "@mui/icons-material/AddTaskRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import DeleteOutlineRoundedIcon from "@mui/icons-material/DeleteOutlineRounded";
import RadioButtonUncheckedRoundedIcon from "@mui/icons-material/RadioButtonUncheckedRounded";
import HourglassEmptyRoundedIcon from "@mui/icons-material/HourglassEmptyRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import { formatDistanceToNow } from "date-fns";
import { api } from "../../api/client";

const TASK_POLL_MS = 45_000;

const STATUSES = [
  {
    value: "todo",
    label: "To do",
    Icon: RadioButtonUncheckedRoundedIcon,
  },
  {
    value: "inProgress",
    label: "In progress",
    Icon: HourglassEmptyRoundedIcon,
  },
  {
    value: "done",
    label: "Done",
    Icon: CheckCircleRoundedIcon,
  },
];

const statusMeta = (s) =>
  STATUSES.find((x) => x.value === s) || STATUSES[0];

function TaskCard({ task, onStatusChange, onDelete, busyId }) {
  const theme = useTheme();
  const busy = busyId === task.id;

  const created = task.created_at
    ? formatDistanceToNow(new Date(task.created_at), { addSuffix: true })
    : null;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2,
        border: "1px solid",
        borderColor: alpha(theme.palette.primary.main, 0.12),
        bgcolor: "background.paper",
        transition: "box-shadow 0.2s, border-color 0.2s, transform 0.15s",
        "&:hover": {
          borderColor: alpha(theme.palette.primary.main, 0.35),
          boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.08)}`,
        },
      }}
    >
      <Stack spacing={1.25}>
        <Typography
          variant="subtitle1"
          sx={{
            fontWeight: 600,
            lineHeight: 1.35,
            color: "text.primary",
          }}
        >
          {task.title}
        </Typography>
        <Stack direction="row" flexWrap="wrap" sx={{ gap: 0.75 }}>
          {task.task_origin === "assigned" ? (
            <Chip size="small" color="primary" label="Assigned to you" sx={{ alignSelf: "flex-start" }} />
          ) : (
            <Chip size="small" variant="outlined" label="Your task" sx={{ alignSelf: "flex-start" }} />
          )}
          {task.project_name ? (
            <Chip size="small" label={task.project_name} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          ) : null}
        </Stack>
        {created && (
          <Typography variant="caption" color="text.secondary">
            {created}
          </Typography>
        )}
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 140, flex: 1 }}>
            <InputLabel id={`status-${task.id}`}>Status</InputLabel>
            <Select
              labelId={`status-${task.id}`}
              label="Status"
              value={task.status}
              disabled={busy}
              onChange={(e) => onStatusChange(task, e.target.value)}
            >
              {STATUSES.map((s) => (
                <MenuItem key={s.value} value={s.value}>
                  {s.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <IconButton
            aria-label="Delete task"
            size="small"
            disabled={busy}
            onClick={() => onDelete(task)}
            sx={{
              color: "error.main",
              "&:hover": { bgcolor: alpha(theme.palette.error.main, 0.08) },
            }}
          >
            <DeleteOutlineRoundedIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Stack>
    </Paper>
  );
}

function Column({ status, tasks, onStatusChange, onDelete, busyId }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === "dark";
  const headingColor = isDark ? theme.palette.primary.light : theme.palette.primary.dark;
  const meta = statusMeta(status);
  const Icon = meta.Icon;

  return (
    <Paper
      elevation={0}
      sx={{
        flex: 1,
        minWidth: { xs: "100%", sm: 260 },
        maxWidth: { md: "100%" },
        borderRadius: 3,
        overflow: "hidden",
        border: "1px solid",
        borderColor: alpha(theme.palette.divider, 0.9),
        bgcolor: isDark ? alpha(theme.palette.common.white, 0.03) : alpha(theme.palette.grey[50], 0.8),
        display: "flex",
        flexDirection: "column",
        minHeight: 360,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: alpha(theme.palette.divider, 0.9),
          bgcolor: alpha(theme.palette.primary.main, isDark ? 0.16 : 0.06),
          display: "flex",
          alignItems: "center",
          gap: 1,
        }}
      >
        <Icon sx={{ color: "primary.main", fontSize: 22 }} />
        <Typography variant="subtitle2" fontWeight={700} sx={{ color: headingColor }}>
          {meta.label}
        </Typography>
        <Chip
          label={tasks.length}
          size="small"
          sx={{
            ml: "auto",
            height: 22,
            fontWeight: 700,
            bgcolor: alpha(theme.palette.primary.main, isDark ? 0.24 : 0.12),
            color: headingColor,
          }}
        />
      </Box>
      <Stack spacing={1.5} sx={{ p: 2, flex: 1, overflow: "auto" }}>
        {tasks.length === 0 ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ py: 4, textAlign: "center", px: 1 }}
          >
            No tasks here — add one or move items between columns.
          </Typography>
        ) : (
          tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onStatusChange={onStatusChange}
              onDelete={onDelete}
              busyId={busyId}
            />
          ))
        )}
      </Stack>
    </Paper>
  );
}

const Tasks = () => {
  const theme = useTheme();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTask, setNewTask] = useState("");
  const [newStatus, setNewStatus] = useState("todo");
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [toast, setToast] = useState({ open: false, message: "", severity: "error" });

  const showError = (message) => {
    setToast({ open: true, message, severity: "error" });
  };

  const fetchTasks = useCallback(async () => {
    try {
      const response = await api.get("/taskapi/tasks/");
      setTasks(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error("Error fetching tasks:", error);
      if (error.response?.status !== 401) {
        showError("Could not load tasks. Try again.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    const id = setInterval(fetchTasks, TASK_POLL_MS);
    const onVis = () => {
      if (document.visibilityState === "visible") fetchTasks();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [fetchTasks]);

  const byStatus = useMemo(() => {
    const map = { todo: [], inProgress: [], done: [] };
    tasks.forEach((t) => {
      const key = map[t.status] !== undefined ? t.status : "todo";
      map[key].push(t);
    });
    return map;
  }, [tasks]);

  const addTask = async (e) => {
    e.preventDefault();
    const title = newTask.trim();
    if (!title || submitting) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/taskapi/tasks/", {
        title,
        status: newStatus,
      });
      setTasks((prev) => [data, ...prev]);
      setNewTask("");
      setNewStatus("todo");
    } catch (error) {
      console.error("Error adding task:", error);
      showError(
        error.response?.data?.detail ||
          error.response?.data?.title?.[0] ||
          "Could not create task."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (task, status) => {
    if (status === task.status) return;
    const prev = tasks;
    setTasks((t) =>
      t.map((x) => (x.id === task.id ? { ...x, status } : x))
    );
    setBusyId(task.id);
    try {
      await api.patch(`/taskapi/tasks/${task.id}/`, { status });
    } catch (error) {
      console.error(error);
      setTasks(prev);
      showError("Could not update status.");
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (task) => {
    const prev = tasks;
    setTasks((t) => t.filter((x) => x.id !== task.id));
    setBusyId(task.id);
    try {
      await api.delete(`/taskapi/tasks/${task.id}/`);
    } catch (error) {
      console.error(error);
      setTasks(prev);
      showError("Could not delete task.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Box
      sx={{
        maxWidth: 1200,
        mx: "auto",
        pb: 4,
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        justifyContent="space-between"
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography
            variant="h5"
            sx={{
              fontWeight: 800,
              letterSpacing: "-0.02em",
              color: (t) => (t.palette.mode === "dark" ? t.palette.primary.light : t.palette.primary.dark),
            }}
          >
            My tasks
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Tasks <strong>assigned by your admin</strong> appear with “Assigned to you”. Use <strong>Add task</strong> for
            your own personal tasks anytime.
          </Typography>
        </Box>
        <IconButton
          onClick={() => {
            setLoading(true);
            fetchTasks();
          }}
          aria-label="Refresh tasks"
          sx={{
            alignSelf: { xs: "flex-end", sm: "center" },
            border: "1px solid",
            borderColor: alpha(theme.palette.primary.main, 0.25),
            bgcolor: "background.paper",
          }}
        >
          <RefreshRoundedIcon color="primary" />
        </IconButton>
      </Stack>

      {!loading && tasks.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>No tasks yet.</strong> If your admin has not assigned anything, this board stays empty until they do—or
          use <strong>Quick add</strong> below to create your own tasks anytime.
        </Alert>
      )}
      {!loading &&
        tasks.length > 0 &&
        !tasks.some((t) => t.task_origin === "assigned") && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <strong>No organization-assigned tasks yet.</strong> You only have personal tasks here. Work assigned by an
            admin will show the <strong>Assigned to you</strong> label.
          </Alert>
        )}

      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 2.5 },
          mb: 3,
          borderRadius: 3,
          border: "1px solid",
          borderColor: alpha(theme.palette.primary.main, 0.15),
          background: `linear-gradient(135deg, ${alpha(
            theme.palette.primary.main,
            theme.palette.mode === "dark" ? 0.18 : 0.06
          )} 0%, ${theme.palette.background.paper} 48%)`,
        }}
        component="form"
        onSubmit={addTask}
      >
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <AddTaskRoundedIcon color="primary" />
            <Typography variant="subtitle1" fontWeight={700}>
              Quick add
            </Typography>
          </Stack>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ xs: "stretch", sm: "flex-start" }}
          >
            <TextField
              fullWidth
              size="medium"
              placeholder="What do you need to do?"
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
              inputProps={{ maxLength: 100 }}
              sx={{
                "& .MuiOutlinedInput-root": {
                  borderRadius: 2,
                  bgcolor: "background.paper",
                },
              }}
            />
            <FormControl sx={{ minWidth: 160 }}>
              <InputLabel id="new-status">Initial column</InputLabel>
              <Select
                labelId="new-status"
                label="Initial column"
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                sx={{ borderRadius: 2, bgcolor: "background.paper" }}
              >
                {STATUSES.map((s) => (
                  <MenuItem key={s.value} value={s.value}>
                    {s.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              type="submit"
              variant="contained"
              disabled={submitting || !newTask.trim()}
              sx={{
                px: 3,
                py: 1.25,
                borderRadius: 2,
                fontWeight: 700,
                textTransform: "none",
                boxShadow: `0 8px 20px ${alpha(theme.palette.primary.main, 0.35)}`,
                background: `linear-gradient(90deg, #4338ca 0%, #4f46e5 100%)`,
                "&:hover": {
                  background: `linear-gradient(90deg, #3730a3 0%, #4338ca 100%)`,
                },
              }}
            >
              {submitting ? "Adding…" : "Add task"}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {loading ? (
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          {[1, 2, 3].map((i) => (
            <Skeleton
              key={i}
              variant="rounded"
              height={360}
              sx={{ flex: 1, borderRadius: 3 }}
            />
          ))}
        </Stack>
      ) : (
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          alignItems="stretch"
        >
          {STATUSES.map((s) => (
            <Column
              key={s.value}
              status={s.value}
              tasks={byStatus[s.value]}
              onStatusChange={handleStatusChange}
              onDelete={handleDelete}
              busyId={busyId}
            />
          ))}
        </Stack>
      )}

      <Snackbar
        open={toast.open}
        autoHideDuration={5000}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={toast.severity}
          variant="filled"
          onClose={() => setToast((t) => ({ ...t, open: false }))}
          sx={{ width: "100%" }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Tasks;
