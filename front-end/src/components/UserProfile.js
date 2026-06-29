import React, { useEffect, useState, useCallback } from "react";
import {
  Box,
  Typography,
  Avatar,
  Button,
  Card,
  CardContent,
  Stack,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  alpha,
} from "@mui/material";
import ArrowBackIosNewRoundedIcon from "@mui/icons-material/ArrowBackIosNewRounded";
import PersonRoundedIcon from "@mui/icons-material/PersonRounded";
import FolderOpenRoundedIcon from "@mui/icons-material/FolderOpenRounded";
import AssignmentRoundedIcon from "@mui/icons-material/AssignmentRounded";
import RadioButtonUncheckedRoundedIcon from "@mui/icons-material/RadioButtonUncheckedRounded";
import HourglassEmptyRoundedIcon from "@mui/icons-material/HourglassEmptyRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { useSession } from "../context/SessionContext";
import { api, mediaUrl } from "../api/client";

const ACCENT = "#4f46e5";

const STATUS_LABELS = {
  todo: "To do",
  inProgress: "In progress",
  done: "Done",
};

function StatTile({ title, value, icon: Icon, loading }) {
  return (
    <Card
      elevation={0}
      sx={{
        height: "100%",
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5" sx={{ mt: 0.5, fontWeight: 700 }}>
              {loading ? "…" : value}
            </Typography>
          </Box>
          <Box sx={{ color: ACCENT, display: "flex", alignItems: "center" }} aria-hidden>
            <Icon />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

const UserProfile = () => {
  const navigate = useNavigate();
  const { user, loading: sessionLoading } = useSession();
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);

  const loadWork = useCallback(async () => {
    setDataLoading(true);
    try {
      const [tRes, pRes] = await Promise.all([
        api.get("/taskapi/tasks/"),
        api.get("/taskapi/my-projects/"),
      ]);
      setTasks(Array.isArray(tRes.data) ? tRes.data : []);
      setProjects(Array.isArray(pRes.data) ? pRes.data : []);
    } catch {
      setTasks([]);
      setProjects([]);
    } finally {
      setDataLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!sessionLoading && !user) {
      navigate("/login", { replace: true });
    }
  }, [sessionLoading, user, navigate]);

  // Depend on user.id only — full `user` changes reference on every /api/me/ parse and
  // calling refreshSession here caused an infinite loop (refresh → setUser → effect → refresh).
  useEffect(() => {
    if (!user?.id) return;
    loadWork();
  }, [user?.id, loadWork]);

  if (sessionLoading) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "#f1f5f9",
        }}
      >
        <Typography color="text.secondary">Loading…</Typography>
      </Box>
    );
  }

  if (!user) {
    return null;
  }

  const todoC = tasks.filter((t) => t.status === "todo").length;
  const progC = tasks.filter((t) => t.status === "inProgress").length;
  const doneC = tasks.filter((t) => t.status === "done").length;
  const openC = todoC + progC;
  const total = tasks.length;

  const dashboardPath =
    user.role === "admin" ? "/admin/dashboard" : "/employee/dashboard";

  const goToTasks = () => {
    if (user.role === "admin") {
      navigate("/admin/dashboard", { state: { adminSection: "tasks" } });
    } else {
      navigate("/employee/dashboard", { state: { dashboardTab: "tasks" } });
    }
  };

  const recent = [...tasks]
    .sort((a, b) => {
      const da = a.created_at ? new Date(a.created_at).getTime() : 0;
      const db = b.created_at ? new Date(b.created_at).getTime() : 0;
      return db - da;
    })
    .slice(0, 10);

  const displayName = user.username || user.email || "Account";
  const initial = (
    user.username?.[0] ||
    user.email?.[0] ||
    "?"
  ).toUpperCase();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f1f5f9", pb: 4 }}>
      <Box
        sx={{
          background:
            "linear-gradient(90deg, #4338ca 0%, #4f46e5 45%, #3730a3 100%)",
          color: "#fff",
          py: 2,
          px: { xs: 2, md: 4 },
        }}
      >
        <Button
          startIcon={<ArrowBackIosNewRoundedIcon sx={{ fontSize: 18 }} />}
          onClick={() => navigate(dashboardPath)}
          sx={{
            color: "inherit",
            textTransform: "none",
            fontWeight: 600,
            "&:hover": { bgcolor: alpha("#fff", 0.12) },
          }}
        >
          Back to dashboard
        </Button>
      </Box>

      <Box sx={{ maxWidth: 960, mx: "auto", px: { xs: 2, md: 3 }, mt: -3 }}>
        <Card
          elevation={0}
          sx={{
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={3}
              alignItems={{ sm: "center" }}
            >
              <Avatar
                src={
                  user.profile_photo ? mediaUrl(user.profile_photo) : undefined
                }
                alt=""
                sx={{
                  width: 96,
                  height: 96,
                  border: "4px solid",
                  borderColor: ACCENT,
                  bgcolor: alpha(ACCENT, 0.12),
                  fontSize: 40,
                  color: "#4338ca",
                  fontWeight: 700,
                }}
              >
                {initial}
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {displayName}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5 }}
                >
                  {user.email}
                </Typography>
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ mt: 1.5 }}
                  flexWrap="wrap"
                  useFlexGap
                >
                  <Chip
                    size="small"
                    icon={
                      <PersonRoundedIcon sx={{ fontSize: "18px !important" }} />
                    }
                    label={user.role === "admin" ? "Admin" : "Employee"}
                    sx={{
                      bgcolor: alpha(ACCENT, 0.12),
                      color: "#4338ca",
                      fontWeight: 600,
                    }}
                  />
                </Stack>
              </Box>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button
                  variant="outlined"
                  onClick={loadWork}
                  disabled={dataLoading}
                  sx={{
                    borderColor: ACCENT,
                    color: "#4338ca",
                    textTransform: "none",
                  }}
                >
                  Refresh
                </Button>
                <Button
                  variant="contained"
                  onClick={goToTasks}
                  sx={{
                    bgcolor: ACCENT,
                    textTransform: "none",
                    "&:hover": { bgcolor: "#4338ca" },
                  }}
                >
                  {user.role === "admin" ? "Task planning" : "Open tasks"}
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Projects"
              value={String(projects.length)}
              icon={FolderOpenRoundedIcon}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Open tasks"
              value={String(openC)}
              icon={AssignmentRoundedIcon}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="In progress"
              value={String(progC)}
              icon={HourglassEmptyRoundedIcon}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Done"
              value={String(doneC)}
              icon={CheckCircleRoundedIcon}
              loading={dataLoading}
            />
          </Grid>
        </Grid>

        <Card
          elevation={0}
          sx={{
            mt: 2,
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Task breakdown
            </Typography>
            <Stack spacing={1.25}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <RadioButtonUncheckedRoundedIcon
                  sx={{ fontSize: 20, color: "text.secondary" }}
                />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  To do
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {dataLoading ? "…" : todoC}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1}>
                <HourglassEmptyRoundedIcon
                  sx={{ fontSize: 20, color: "warning.main" }}
                />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  In progress
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {dataLoading ? "…" : progC}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1}>
                <CheckCircleRoundedIcon
                  sx={{ fontSize: 20, color: "success.main" }}
                />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  Done
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {dataLoading ? "…" : doneC}
                </Typography>
              </Stack>
            </Stack>
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              sx={{ mt: 2 }}
            >
              {total === 0 && !dataLoading
                ? "No tasks yet. Create or receive assignments from the Tasks tab."
                : !dataLoading
                  ? `${total} task${total === 1 ? "" : "s"} total.`
                  : null}
            </Typography>
          </CardContent>
        </Card>

        <Card
          elevation={0}
          sx={{
            mt: 2,
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5 }, pb: "16px !important" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Recent tasks
            </Typography>
            {dataLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading…
              </Typography>
            ) : recent.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Nothing to show yet.
              </Typography>
            ) : (
              <List dense disablePadding>
                {recent.map((t) => (
                  <ListItem
                    key={t.id}
                    sx={{
                      px: 0,
                      py: 1,
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      "&:last-child": { borderBottom: "none" },
                    }}
                  >
                    <ListItemText
                      primary={t.title}
                      primaryTypographyProps={{
                        fontWeight: 600,
                        noWrap: true,
                      }}
                      secondary={
                        <Stack
                          direction="row"
                          spacing={0.75}
                          flexWrap="wrap"
                          useFlexGap
                          sx={{ mt: 0.5 }}
                        >
                          <Chip
                            size="small"
                            label={
                              STATUS_LABELS[t.status] || t.status || "—"
                            }
                            sx={{ height: 22 }}
                          />
                          {t.task_origin === "assigned" ? (
                            <Chip
                              size="small"
                              color="primary"
                              label="Assigned"
                              sx={{ height: 22 }}
                            />
                          ) : (
                            <Chip
                              size="small"
                              variant="outlined"
                              label="Yours"
                              sx={{ height: 22 }}
                            />
                          )}
                          {t.project_name ? (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={t.project_name}
                              sx={{ height: 22 }}
                            />
                          ) : null}
                          {t.created_at ? (
                            <Typography
                              component="span"
                              variant="caption"
                              color="text.secondary"
                              sx={{ alignSelf: "center" }}
                            >
                              {formatDistanceToNow(new Date(t.created_at), {
                                addSuffix: true,
                              })}
                            </Typography>
                          ) : null}
                        </Stack>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default UserProfile;
