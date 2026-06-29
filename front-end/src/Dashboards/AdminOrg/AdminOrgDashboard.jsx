import React, { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  CssBaseline,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Typography,
  Chip,
  Alert,
  Stack,
} from "@mui/material";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import PeopleIcon from "@mui/icons-material/People";
import FolderSpecialIcon from "@mui/icons-material/FolderSpecial";
import AssignmentIcon from "@mui/icons-material/Assignment";
import DashboardCustomizeIcon from "@mui/icons-material/DashboardCustomize";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import LogoutIcon from "@mui/icons-material/Logout";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import PrivacyTipIcon from "@mui/icons-material/PrivacyTip";
import { Link, useNavigate, useLocation } from "react-router-dom";
import DataCollectionMui from "../../components/DataCollectionMui";
import TrackingDisclosureDialog from "../../components/TrackingDisclosureDialog";
import AdminEmployeeActivityDialog from "./AdminEmployeeActivityDialog";
import AnalyticsOutlinedIcon from "@mui/icons-material/AnalyticsOutlined";
import { api } from "../../api/client";
import { useSession } from "../../context/SessionContext";

const DRAWER_W = 280;
const SIDEBAR_BG = "#0b1220";
const SIDEBAR_ACCENT = "#f59e0b";
const MAIN_BG = "#f1f5f9";

const NAV = [
  { id: "overview", label: "Overview", icon: DashboardCustomizeIcon },
  { id: "people", label: "People", icon: PeopleIcon },
  { id: "projects", label: "Projects & teams", icon: FolderSpecialIcon },
  { id: "tasks", label: "Task planning", icon: AssignmentIcon },
  { id: "data-privacy", label: "Data & privacy", icon: PrivacyTipIcon },
];

const emptyProjectForm = {
  name: "",
  description: "",
  lead_id: "",
  manager_id: "",
  member_ids: [],
};

const ADMIN_SECTIONS = new Set(["overview", "people", "projects", "tasks", "data-privacy"]);

export default function AdminOrgDashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, clearSession, refreshSession } = useSession();
  const [section, setSection] = useState("overview");
  const [people, setPeople] = useState([]);
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);

  const [projectDialog, setProjectDialog] = useState({ open: false, editing: null });
  const [projectForm, setProjectForm] = useState(emptyProjectForm);

  const [activityEmployee, setActivityEmployee] = useState(null);
  const [taskDialog, setTaskDialog] = useState(false);
  const [taskForm, setTaskForm] = useState({
    title: "",
    status: "todo",
    assignee_id: "",
    project: "",
  });

  const employees = people;
  const loadPeople = useCallback(async () => {
    const { data } = await api.get("/api/check_data/");
    setPeople(Array.isArray(data.data) ? data.data : []);
  }, []);

  const loadProjects = useCallback(async () => {
    const { data } = await api.get("/taskapi/admin/projects/");
    setProjects(Array.isArray(data) ? data : []);
  }, []);

  const loadTasks = useCallback(async () => {
    const { data } = await api.get("/taskapi/admin/tasks/");
    setTasks(Array.isArray(data) ? data : []);
  }, []);

  const refresh = useCallback(async () => {
    setLoadError("");
    setBusy(true);
    try {
      await Promise.all([loadPeople(), loadProjects(), loadTasks()]);
    } catch (e) {
      setLoadError(e.response?.data?.error || "Could not load org data.");
    } finally {
      setBusy(false);
    }
  }, [loadPeople, loadProjects, loadTasks]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const s = location.state?.adminSection;
    if (s && ADMIN_SECTIONS.has(s)) {
      setSection(s);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  const handleLogout = async () => {
    try {
      await api.post("/api/logout/", {});
      clearSession();
      await refreshSession({ quiet: true });
      navigate("/login");
    } catch {
      /* ignore */
    }
  };

  const openNewProject = () => {
    setProjectForm(emptyProjectForm);
    setProjectDialog({ open: true, editing: null });
  };

  const openEditProject = (p) => {
    setProjectForm({
      name: p.name,
      description: p.description || "",
      lead_id: p.lead?.id ?? "",
      manager_id: p.manager?.id ?? "",
      member_ids: (p.members || []).map((m) => m.id),
    });
    setProjectDialog({ open: true, editing: p });
  };

  const saveProject = async () => {
    setBusy(true);
    try {
      const payload = {
        name: projectForm.name.trim(),
        description: projectForm.description,
        lead_id: projectForm.lead_id === "" ? null : Number(projectForm.lead_id),
        manager_id: projectForm.manager_id === "" ? null : Number(projectForm.manager_id),
        member_ids: projectForm.member_ids.map(Number),
      };
      if (projectDialog.editing) {
        await api.patch(`/taskapi/admin/projects/${projectDialog.editing.id}/`, payload);
      } else {
        await api.post("/taskapi/admin/projects/", payload);
      }
      setProjectDialog({ open: false, editing: null });
      await loadProjects();
    } catch (e) {
      setLoadError(JSON.stringify(e.response?.data || e.message));
    } finally {
      setBusy(false);
    }
  };

  const deleteProject = async (p) => {
    if (!window.confirm(`Delete project “${p.name}”?`)) return;
    setBusy(true);
    try {
      await api.delete(`/taskapi/admin/projects/${p.id}/`);
      await loadProjects();
    } catch (e) {
      setLoadError(JSON.stringify(e.response?.data || e.message));
    } finally {
      setBusy(false);
    }
  };

  const saveTask = async () => {
    setBusy(true);
    try {
      await api.post("/taskapi/admin/tasks/", {
        title: taskForm.title.trim(),
        status: taskForm.status,
        assignee_id: taskForm.assignee_id === "" ? null : Number(taskForm.assignee_id),
        project: taskForm.project === "" ? null : Number(taskForm.project),
      });
      setTaskDialog(false);
      setTaskForm({ title: "", status: "todo", assignee_id: "", project: "" });
      await loadTasks();
    } catch (e) {
      setLoadError(JSON.stringify(e.response?.data || e.message));
    } finally {
      setBusy(false);
    }
  };

  const deleteTask = async (t) => {
    if (!window.confirm(`Delete task “${t.title}”?`)) return;
    try {
      await api.delete(`/taskapi/admin/tasks/${t.id}/`);
      await loadTasks();
    } catch (e) {
      setLoadError(JSON.stringify(e.response?.data || e.message));
    }
  };

  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column", bgcolor: SIDEBAR_BG, color: "#e2e8f0" }}>
      <Toolbar sx={{ px: 2, gap: 1, borderBottom: "1px solid rgba(148,163,184,0.15)" }}>
        <AdminPanelSettingsIcon sx={{ color: SIDEBAR_ACCENT }} />
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
            Organization
          </Typography>
          <Typography variant="caption" sx={{ color: "#94a3b8" }}>
            Admin control
          </Typography>
        </Box>
      </Toolbar>
      <List sx={{ flex: 1, py: 1 }}>
        {NAV.map((item) => {
          const Icon = item.icon;
          const sel = section === item.id;
          return (
            <ListItemButton
              key={item.id}
              selected={sel}
              onClick={() => setSection(item.id)}
              sx={{
                mx: 1,
                borderRadius: 1,
                mb: 0.5,
                "&.Mui-selected": { bgcolor: "rgba(245, 158, 11, 0.12)", borderLeft: `3px solid ${SIDEBAR_ACCENT}` },
              }}
            >
              <ListItemIcon sx={{ color: sel ? SIDEBAR_ACCENT : "#94a3b8", minWidth: 40 }}>
                <Icon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2", fontWeight: sel ? 600 : 400 }} />
            </ListItemButton>
          );
        })}
      </List>
      <Box sx={{ p: 2, borderTop: "1px solid rgba(148,163,184,0.15)" }}>
        <Button
          fullWidth
          component={Link}
          to="/employee/dashboard"
          startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
          sx={{ color: "#e2e8f0", justifyContent: "flex-start", mb: 1 }}
        >
          Employee dashboard
        </Button>
        <Button
          fullWidth
          component={Link}
          to="/group/dashboard"
          endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
          sx={{ color: "#e2e8f0", justifyContent: "flex-start", mb: 1 }}
        >
          Group dashboard
        </Button>
        <Button
          fullWidth
          component={Link}
          to="/admin/sprint-dashboard"
          endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
          sx={{ color: "#e2e8f0", justifyContent: "flex-start", mb: 1 }}
        >
          Sprint & burndown
        </Button>
        <Button
          fullWidth
          component={Link}
          to="/admin/employee-profiles"
          endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
          sx={{ color: "#e2e8f0", justifyContent: "flex-start", mb: 1 }}
        >
          Employee profiles
        </Button>
        <Typography variant="caption" display="block" sx={{ color: "#64748b", mb: 1, px: 0.5 }}>
          Signed in as {user?.username || user?.email}
        </Typography>
        <Button fullWidth startIcon={<LogoutIcon />} onClick={handleLogout} sx={{ color: "#fca5a5" }}>
          Log out
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: MAIN_BG }}>
      <AdminEmployeeActivityDialog
        open={Boolean(activityEmployee)}
        onClose={() => setActivityEmployee(null)}
        employee={activityEmployee}
      />
      <TrackingDisclosureDialog />
      <CssBaseline />
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_W,
          flexShrink: 0,
          "& .MuiDrawer-paper": { width: DRAWER_W, boxSizing: "border-box", border: "none" },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flex: 1, p: 3, minWidth: 0 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, color: "#0f172a" }}>
              {NAV.find((n) => n.id === section)?.label}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {section === "data-privacy"
                ? "What the desktop agent and server store, who can see it, and retention—same facts employees see, with admin visibility called out."
                : "Plan projects, assign leads and managers, build teams, and distribute work—separate from the employee workspace."}
            </Typography>
          </Box>
          {section !== "data-privacy" && (
            <Button variant="outlined" onClick={refresh} disabled={busy}>
              Refresh data
            </Button>
          )}
        </Stack>

        {loadError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setLoadError("")}>
            {loadError}
          </Alert>
        )}

        {section === "overview" && (
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Paper sx={{ p: 2, flex: 1, borderRadius: 2 }}>
              <Typography variant="overline" color="text.secondary">
                People
              </Typography>
              <Typography variant="h3">{people.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Accounts in the org
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: 1, borderRadius: 2 }}>
              <Typography variant="overline" color="text.secondary">
                Projects
              </Typography>
              <Typography variant="h3">{projects.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Active project records
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: 1, borderRadius: 2 }}>
              <Typography variant="overline" color="text.secondary">
                Tasks
              </Typography>
              <Typography variant="h3">{tasks.length}</Typography>
              <Typography variant="body2" color="text.secondary">
                Planned / assigned tasks
              </Typography>
            </Paper>
          </Stack>
        )}

        {section === "people" && (
          <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: "#e2e8f0" }}>
                  <TableCell>ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell align="right">Activity</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.id}</TableCell>
                    <TableCell>{row.username}</TableCell>
                    <TableCell>{row.email}</TableCell>
                    <TableCell>
                      <Chip size="small" label={row.role} color={row.role === "admin" ? "warning" : "default"} />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<AnalyticsOutlinedIcon fontSize="small" />}
                        onClick={() => setActivityEmployee(row)}
                        sx={{ textTransform: "none", borderColor: "#cbd5e1", color: "#0f172a" }}
                      >
                        View work vs other
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {section === "projects" && (
          <Box>
            <Button variant="contained" startIcon={<AddIcon />} onClick={openNewProject} sx={{ mb: 2, bgcolor: "#0f172a" }}>
              New project
            </Button>
            <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "#e2e8f0" }}>
                    <TableCell>Name</TableCell>
                    <TableCell>Lead</TableCell>
                    <TableCell>Manager</TableCell>
                    <TableCell>Team size</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {projects.map((p) => (
                    <TableRow key={p.id} hover>
                      <TableCell>
                        <Typography fontWeight={600}>{p.name}</Typography>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {p.description}
                        </Typography>
                      </TableCell>
                      <TableCell>{p.lead ? `${p.lead.username}` : "—"}</TableCell>
                      <TableCell>{p.manager ? `${p.manager.username}` : "—"}</TableCell>
                      <TableCell>{(p.members || []).length}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => openEditProject(p)} aria-label="Edit">
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => deleteProject(p)} aria-label="Delete">
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {section === "data-privacy" && (
          <Paper sx={{ p: { xs: 2, sm: 3 }, borderRadius: 2, maxWidth: 800 }}>
            <DataCollectionMui showAdminAudience />
            <Button component={Link} to="/data-collection" variant="outlined" size="small" sx={{ mt: 2 }} target="_blank" rel="noopener noreferrer">
              Open public disclosure page
            </Button>
          </Paper>
        )}

        {section === "tasks" && (
          <Box>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setTaskDialog(true)} sx={{ mb: 2, bgcolor: "#0f172a" }}>
              Assign task
            </Button>
            <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "#e2e8f0" }}>
                    <TableCell>Title</TableCell>
                    <TableCell>Project</TableCell>
                    <TableCell>Assignee</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tasks.map((t) => (
                    <TableRow key={t.id} hover>
                      <TableCell>{t.title}</TableCell>
                      <TableCell>{t.project_name || "—"}</TableCell>
                      <TableCell>{t.assignee ? t.assignee.username : "—"}</TableCell>
                      <TableCell>
                        <Chip size="small" label={t.status} />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton size="small" color="error" onClick={() => deleteTask(t)} aria-label="Delete">
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Box>

      <Dialog open={projectDialog.open} onClose={() => setProjectDialog({ open: false, editing: null })} maxWidth="sm" fullWidth>
        <DialogTitle>{projectDialog.editing ? "Edit project" : "Create project"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Project name"
              fullWidth
              required
              value={projectForm.name}
              onChange={(e) => setProjectForm((f) => ({ ...f, name: e.target.value }))}
            />
            <TextField
              label="Description"
              fullWidth
              multiline
              minRows={2}
              value={projectForm.description}
              onChange={(e) => setProjectForm((f) => ({ ...f, description: e.target.value }))}
            />
            <FormControl fullWidth>
              <InputLabel>Project lead</InputLabel>
              <Select
                label="Project lead"
                value={projectForm.lead_id === "" ? "" : projectForm.lead_id}
                onChange={(e) => setProjectForm((f) => ({ ...f, lead_id: e.target.value }))}
              >
                <MenuItem value="">None</MenuItem>
                {people.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.username} ({p.email})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Project manager</InputLabel>
              <Select
                label="Project manager"
                value={projectForm.manager_id === "" ? "" : projectForm.manager_id}
                onChange={(e) => setProjectForm((f) => ({ ...f, manager_id: e.target.value }))}
              >
                <MenuItem value="">None</MenuItem>
                {people.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.username} ({p.email})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Team members</InputLabel>
              <Select
                label="Team members"
                multiple
                value={projectForm.member_ids}
                onChange={(e) => setProjectForm((f) => ({ ...f, member_ids: e.target.value }))}
                renderValue={(selected) =>
                  selected
                    .map((id) => people.find((x) => x.id === id)?.username || id)
                    .join(", ")
                }
              >
                {people.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.username} ({p.role})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProjectDialog({ open: false, editing: null })}>Cancel</Button>
          <Button variant="contained" onClick={saveProject} disabled={!projectForm.name.trim() || busy}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={taskDialog} onClose={() => setTaskDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign task</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Title"
              fullWidth
              required
              value={taskForm.title}
              onChange={(e) => setTaskForm((f) => ({ ...f, title: e.target.value }))}
            />
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                label="Status"
                value={taskForm.status}
                onChange={(e) => setTaskForm((f) => ({ ...f, status: e.target.value }))}
              >
                <MenuItem value="todo">To do</MenuItem>
                <MenuItem value="inProgress">In progress</MenuItem>
                <MenuItem value="done">Done</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Project</InputLabel>
              <Select
                label="Project"
                value={taskForm.project === "" ? "" : taskForm.project}
                onChange={(e) => setTaskForm((f) => ({ ...f, project: e.target.value }))}
              >
                <MenuItem value="">None</MenuItem>
                {projects.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Assignee</InputLabel>
              <Select
                label="Assignee"
                value={taskForm.assignee_id === "" ? "" : taskForm.assignee_id}
                onChange={(e) => setTaskForm((f) => ({ ...f, assignee_id: e.target.value }))}
              >
                <MenuItem value="">Unassigned</MenuItem>
                {people.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.username}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTaskDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={saveTask} disabled={!taskForm.title.trim() || busy}>
            Create task
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
