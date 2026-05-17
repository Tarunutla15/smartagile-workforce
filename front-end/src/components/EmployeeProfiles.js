import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  CssBaseline,
  Dialog,
  DialogContent,
  DialogTitle,
  Drawer,
  InputAdornment,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Typography,
  Avatar,
  Chip,
  Alert,
  IconButton,
} from "@mui/material";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import BadgeIcon from "@mui/icons-material/Badge";
import SearchIcon from "@mui/icons-material/Search";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import FolderSpecialIcon from "@mui/icons-material/FolderSpecial";
import AssignmentIcon from "@mui/icons-material/Assignment";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import LogoutIcon from "@mui/icons-material/Logout";
import { Link, useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { api, mediaUrl } from "../api/client";
import { useSession } from "../context/SessionContext";

const DRAWER_W = 280;
const SIDEBAR_BG = "#0b1220";
const SIDEBAR_ACCENT = "#f59e0b";
const MAIN_BG = "#f1f5f9";

const TASK_STATUS = {
  todo: "To do",
  inProgress: "In progress",
  done: "Done",
};

function taskStatsForUser(tasks, userId) {
  const mine = tasks.filter((t) => t.assignee?.id === userId);
  const open = mine.filter((t) => t.status !== "done").length;
  const done = mine.filter((t) => t.status === "done").length;
  return { total: mine.length, open, done };
}

function projectsForUser(projects, userId) {
  return projects.filter((p) => {
    if (p.lead?.id === userId || p.manager?.id === userId) return true;
    return (p.members || []).some((m) => m.id === userId);
  });
}

function tasksForUser(tasks, userId) {
  return tasks.filter((t) => t.assignee?.id === userId);
}

export default function EmployeeProfiles() {
  const navigate = useNavigate();
  const { user, clearSession, refreshSession } = useSession();
  const [people, setPeople] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const [peopleRes, taskRes, projRes] = await Promise.all([
        api.get("/api/check_data/"),
        api.get("/taskapi/admin/tasks/"),
        api.get("/taskapi/admin/projects/"),
      ]);
      const list = peopleRes.data?.data;
      setPeople(Array.isArray(list) ? list : []);
      const td = taskRes.data;
      setTasks(Array.isArray(td) ? td : []);
      const pd = projRes.data;
      setProjects(Array.isArray(pd) ? pd : []);
    } catch (e) {
      setError(e.response?.data?.error || "Could not load directory.");
      setPeople([]);
      setTasks([]);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return people;
    return people.filter(
      (p) =>
        (p.username || "").toLowerCase().includes(q) ||
        (p.email || "").toLowerCase().includes(q) ||
        String(p.id).includes(q)
    );
  }, [people, query]);

  const drawer = (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: SIDEBAR_BG,
        color: "#e2e8f0",
      }}
    >
      <Toolbar
        sx={{ px: 2, gap: 1, borderBottom: "1px solid rgba(148,163,184,0.15)" }}
      >
        <AdminPanelSettingsIcon sx={{ color: SIDEBAR_ACCENT }} />
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
            Admin
          </Typography>
          <Typography variant="caption" sx={{ color: "#94a3b8" }}>
            People directory
          </Typography>
        </Box>
      </Toolbar>
      <List sx={{ flex: 1, py: 1 }}>
        <ListItemButton
          component={Link}
          to="/admin/dashboard"
          sx={{
            mx: 1,
            borderRadius: 1,
            mb: 0.5,
            color: "#e2e8f0",
            "&:hover": { bgcolor: "rgba(148,163,184,0.08)" },
          }}
        >
          <ListItemIcon sx={{ color: "#94a3b8", minWidth: 40 }}>
            <AdminPanelSettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText
            primary="Organization"
            primaryTypographyProps={{ variant: "body2", fontWeight: 500 }}
          />
        </ListItemButton>
        <ListItemButton
          selected
          sx={{
            mx: 1,
            borderRadius: 1,
            mb: 0.5,
            "&.Mui-selected": {
              bgcolor: "rgba(245, 158, 11, 0.12)",
              borderLeft: `3px solid ${SIDEBAR_ACCENT}`,
            },
          }}
        >
          <ListItemIcon sx={{ color: SIDEBAR_ACCENT, minWidth: 40 }}>
            <BadgeIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText
            primary="Employee profiles"
            primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
          />
        </ListItemButton>
      </List>
      <Box sx={{ p: 2, borderTop: "1px solid rgba(148,163,184,0.15)" }}>
        <Button
          fullWidth
          component={Link}
          to="/admin/sprint-dashboard"
          endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
          sx={{ color: "#e2e8f0", justifyContent: "flex-start", mb: 1 }}
        >
          Sprint & burndown
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

  const detailTasks = selected ? tasksForUser(tasks, selected.id) : [];
  const detailProjects = selected ? projectsForUser(projects, selected.id) : [];

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: MAIN_BG }}>
      <CssBaseline />
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_W,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_W,
            boxSizing: "border-box",
            border: "none",
          },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flex: 1, p: { xs: 2, sm: 3 }, minWidth: 0 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", sm: "flex-start" }}
          spacing={2}
          sx={{ mb: 3 }}
        >
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: "#0f172a", letterSpacing: "-0.02em" }}>
              Employee profiles
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 560 }}>
              Browse everyone in your organization, see assigned tasks and project involvement. Data comes from the same
              sources as Organization → People and Task planning.
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<RefreshRoundedIcon />}
            onClick={load}
            disabled={loading}
            sx={{
              bgcolor: "#0f766e",
              textTransform: "none",
              fontWeight: 600,
              "&:hover": { bgcolor: "#115e59" },
              alignSelf: { xs: "stretch", sm: "center" },
            }}
          >
            Refresh
          </Button>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
            {error}
          </Alert>
        )}

        <TextField
          fullWidth
          size="small"
          placeholder="Search by name, email, or ID…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{
            mb: 2,
            maxWidth: 400,
            "& .MuiOutlinedInput-root": { bgcolor: "#fff", borderRadius: 2 },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: "text.secondary" }} />
              </InputAdornment>
            ),
          }}
        />

        <TableContainer
          component={Paper}
          elevation={0}
          sx={{
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
            overflowX: "auto",
          }}
        >
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, bgcolor: "#e2e8f0", py: 1.5 }}>Member</TableCell>
                <TableCell sx={{ fontWeight: 700, bgcolor: "#e2e8f0" }}>Email</TableCell>
                <TableCell sx={{ fontWeight: 700, bgcolor: "#e2e8f0" }}>Role</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, bgcolor: "#e2e8f0" }}>
                  Assigned tasks
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, bgcolor: "#e2e8f0" }}>
                  Open
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, bgcolor: "#e2e8f0" }}>
                  Done
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                      Loading directory…
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                      {people.length === 0
                        ? "No accounts found."
                        : "No matches for your search."}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((p) => {
                  const { total, open, done } = taskStatsForUser(tasks, p.id);
                  const initial = (p.username?.[0] || p.email?.[0] || "?").toUpperCase();
                  return (
                    <TableRow
                      key={p.id}
                      hover
                      onClick={() => setSelected(p)}
                      sx={{ cursor: "pointer", "&:last-child td": { borderBottom: 0 } }}
                    >
                      <TableCell>
                        <Stack direction="row" alignItems="center" spacing={1.5}>
                          <Avatar
                            src={p.profile_photo ? mediaUrl(p.profile_photo) : undefined}
                            sx={{ width: 40, height: 40, bgcolor: "rgba(15, 118, 110, 0.12)", color: "#0f766e" }}
                          >
                            {initial}
                          </Avatar>
                          <Box>
                            <Typography variant="body2" fontWeight={600}>
                              {p.username || "—"}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID {p.id}
                            </Typography>
                          </Box>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{p.email}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={p.role === "admin" ? "Admin" : "Employee"}
                          sx={{
                            fontWeight: 600,
                            bgcolor: p.role === "admin" ? "rgba(245, 158, 11, 0.15)" : "rgba(15, 118, 110, 0.1)",
                            color: p.role === "admin" ? "#b45309" : "#0f766e",
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">{total}</TableCell>
                      <TableCell align="right">{open}</TableCell>
                      <TableCell align="right">{done}</TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
          Click a row for tasks and projects for that person.
        </Typography>
      </Box>

      <Dialog
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2 } }}
      >
        {selected && (
          <>
            <DialogTitle
              sx={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: 2,
                pb: 1,
              }}
            >
              <Stack direction="row" spacing={2} alignItems="center">
                <Avatar
                  src={selected.profile_photo ? mediaUrl(selected.profile_photo) : undefined}
                  sx={{ width: 64, height: 64, bgcolor: "rgba(15, 118, 110, 0.15)", color: "#0f766e", fontSize: 28 }}
                >
                  {(selected.username?.[0] || selected.email?.[0] || "?").toUpperCase()}
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight={700}>
                    {selected.username}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selected.email}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
                    <Chip size="small" label={`ID ${selected.id}`} variant="outlined" />
                    <Chip
                      size="small"
                      label={selected.role === "admin" ? "Admin" : "Employee"}
                      sx={{
                        fontWeight: 600,
                        bgcolor:
                          selected.role === "admin"
                            ? "rgba(245, 158, 11, 0.15)"
                            : "rgba(15, 118, 110, 0.1)",
                        color: selected.role === "admin" ? "#b45309" : "#0f766e",
                      }}
                    />
                  </Stack>
                </Box>
              </Stack>
              <IconButton aria-label="Close" onClick={() => setSelected(null)} size="small">
                <CloseRoundedIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers sx={{ pt: 2 }}>
              <Stack spacing={3}>
                <Box>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
                    <FolderSpecialIcon sx={{ color: "#0f766e", fontSize: 22 }} />
                    <Typography variant="subtitle1" fontWeight={700}>
                      Projects ({detailProjects.length})
                    </Typography>
                  </Stack>
                  {detailProjects.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      Not listed on any project as lead, manager, or member.
                    </Typography>
                  ) : (
                    <Stack spacing={1}>
                      {detailProjects.map((pr) => (
                        <Paper
                          key={pr.id}
                          variant="outlined"
                          sx={{ p: 1.5, borderRadius: 2, bgcolor: "#fff" }}
                        >
                          <Typography fontWeight={600}>{pr.name}</Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {pr.description || "No description"}
                          </Typography>
                        </Paper>
                      ))}
                    </Stack>
                  )}
                </Box>

                <Box>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
                    <AssignmentIcon sx={{ color: "#0f766e", fontSize: 22 }} />
                    <Typography variant="subtitle1" fontWeight={700}>
                      Assigned tasks ({detailTasks.length})
                    </Typography>
                  </Stack>
                  {detailTasks.length === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      No tasks assigned to this user yet. Add assignments from Organization → Task planning.
                    </Typography>
                  ) : (
                    <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow sx={{ bgcolor: "#f8fafc" }}>
                            <TableCell sx={{ fontWeight: 600 }}>Title</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Project</TableCell>
                            <TableCell sx={{ fontWeight: 600 }}>Created</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {detailTasks.map((t) => (
                            <TableRow key={t.id}>
                              <TableCell>
                                <Typography variant="body2" fontWeight={500}>
                                  {t.title}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  size="small"
                                  label={TASK_STATUS[t.status] || t.status}
                                  sx={{ height: 24 }}
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">
                                  {t.project_name || "—"}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">
                                  {t.created_at
                                    ? formatDistanceToNow(new Date(t.created_at), { addSuffix: true })
                                    : "—"}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )}
                </Box>
              </Stack>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  );
}
