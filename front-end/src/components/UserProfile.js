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
  LinearProgress,
  alpha,
} from "@mui/material";
import ArrowBackIosNewRoundedIcon from "@mui/icons-material/ArrowBackIosNewRounded";
import PersonRoundedIcon from "@mui/icons-material/PersonRounded";
import FolderOpenRoundedIcon from "@mui/icons-material/FolderOpenRounded";
import AssignmentRoundedIcon from "@mui/icons-material/AssignmentRounded";
import RadioButtonUncheckedRoundedIcon from "@mui/icons-material/RadioButtonUncheckedRounded";
import HourglassEmptyRoundedIcon from "@mui/icons-material/HourglassEmptyRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { useSession } from "../context/SessionContext";
import { api, mediaUrl } from "../api/client";
import { APPBAR_GRADIENT } from "../utils/chartTheme";

const ACCENT = "#4f46e5";
const C_INDIGO = "#4f46e5";
const C_AMBER = "#f59e0b";
const C_SKY = "#0ea5e9";
const C_GREEN = "#22c55e";

const STATUS_LABELS = {
  todo: "To do",
  inProgress: "In progress",
  done: "Done",
};

function StatTile({ title, value, icon: Icon, color = ACCENT, loading }) {
  return (
    <Card
      elevation={0}
      sx={{
        height: "100%",
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        transition: "transform .18s ease, box-shadow .18s ease, border-color .18s ease",
        "&:hover": { transform: "translateY(-3px)", boxShadow: 4, borderColor: alpha(color, 0.5) },
      }}
    >
      <CardContent sx={{ py: 2.25, "&:last-child": { pb: 2.25 } }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 46,
              height: 46,
              borderRadius: 2.5,
              display: "grid",
              placeItems: "center",
              color,
              bgcolor: alpha(color, 0.14),
              flexShrink: 0,
            }}
            aria-hidden
          >
            <Icon />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="h5" sx={{ fontWeight: 800, lineHeight: 1.1 }}>
              {loading ? "…" : value}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {title}
            </Typography>
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
          bgcolor: "background.default",
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
  const donePct = total > 0 ? Math.round((doneC / total) * 100) : 0;

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
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", pb: 5 }}>
      <Box sx={{ maxWidth: 1000, mx: "auto", px: { xs: 2, md: 3 }, pt: { xs: 2, md: 3 } }}>
        <Button
          startIcon={<ArrowBackIosNewRoundedIcon sx={{ fontSize: 16 }} />}
          onClick={() => navigate(dashboardPath)}
          sx={{
            color: "text.secondary",
            textTransform: "none",
            fontWeight: 600,
            mb: 1.5,
            "&:hover": { bgcolor: "action.hover", color: "text.primary" },
          }}
        >
          Back to dashboard
        </Button>

        {/* Hero */}
        <Card
          elevation={0}
          sx={{
            borderRadius: 4,
            color: "#fff",
            background: APPBAR_GRADIENT,
            position: "relative",
            overflow: "hidden",
            boxShadow: "0 18px 40px rgba(79, 70, 229, 0.30)",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(120% 120% at 100% 0%, rgba(255,255,255,0.18), rgba(255,255,255,0) 55%)",
              pointerEvents: "none",
            }}
          />
          <CardContent sx={{ p: { xs: 2.5, sm: 3.5 }, position: "relative" }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={{ xs: 2, sm: 3 }}
              alignItems={{ sm: "center" }}
            >
              <Avatar
                src={user.profile_photo ? mediaUrl(user.profile_photo) : undefined}
                alt=""
                sx={{
                  width: 92,
                  height: 92,
                  fontSize: 38,
                  fontWeight: 800,
                  color: "#fff",
                  bgcolor: "rgba(255,255,255,0.18)",
                  boxShadow: "0 0 0 4px rgba(255,255,255,0.45)",
                }}
              >
                {initial}
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: "-0.02em" }} noWrap>
                  {displayName}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.25, color: "rgba(255,255,255,0.82)" }} noWrap>
                  {user.email}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} flexWrap="wrap" useFlexGap>
                  <Chip
                    size="small"
                    icon={<PersonRoundedIcon sx={{ fontSize: "18px !important", color: "#fff !important" }} />}
                    label={user.role === "admin" ? "Admin" : "Employee"}
                    sx={{
                      bgcolor: "rgba(255,255,255,0.18)",
                      color: "#fff",
                      fontWeight: 700,
                      border: "1px solid rgba(255,255,255,0.28)",
                    }}
                  />
                  {!dataLoading && (
                    <Chip
                      size="small"
                      label={`${donePct}% complete`}
                      sx={{
                        bgcolor: "rgba(255,255,255,0.12)",
                        color: "#fff",
                        fontWeight: 600,
                        border: "1px solid rgba(255,255,255,0.24)",
                      }}
                    />
                  )}
                </Stack>
              </Box>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button
                  variant="outlined"
                  startIcon={<RefreshRoundedIcon />}
                  onClick={loadWork}
                  disabled={dataLoading}
                  sx={{
                    color: "#fff",
                    borderColor: "rgba(255,255,255,0.5)",
                    textTransform: "none",
                    fontWeight: 600,
                    "&:hover": { borderColor: "#fff", bgcolor: "rgba(255,255,255,0.12)" },
                    "&:disabled": { color: "rgba(255,255,255,0.5)", borderColor: "rgba(255,255,255,0.25)" },
                  }}
                >
                  Refresh
                </Button>
                <Button
                  variant="contained"
                  disableElevation
                  onClick={goToTasks}
                  sx={{
                    bgcolor: "#fff",
                    color: "#4338ca",
                    textTransform: "none",
                    fontWeight: 700,
                    "&:hover": { bgcolor: "rgba(255,255,255,0.88)" },
                  }}
                >
                  {user.role === "admin" ? "Task planning" : "Open tasks"}
                </Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>

        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Projects"
              value={String(projects.length)}
              icon={FolderOpenRoundedIcon}
              color={C_INDIGO}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Open tasks"
              value={String(openC)}
              icon={AssignmentRoundedIcon}
              color={C_AMBER}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="In progress"
              value={String(progC)}
              icon={HourglassEmptyRoundedIcon}
              color={C_SKY}
              loading={dataLoading}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatTile
              title="Done"
              value={String(doneC)}
              icon={CheckCircleRoundedIcon}
              color={C_GREEN}
              loading={dataLoading}
            />
          </Grid>
        </Grid>

        <Card
          elevation={0}
          sx={{
            mt: 2,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                Task breakdown
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {dataLoading ? "" : `${doneC}/${total} done`}
              </Typography>
            </Stack>

            <LinearProgress
              variant={dataLoading ? "indeterminate" : "determinate"}
              value={donePct}
              sx={{
                height: 10,
                borderRadius: 999,
                mb: 2,
                bgcolor: (t) => (t.palette.mode === "dark" ? "rgba(255,255,255,0.08)" : "rgba(15,23,42,0.06)"),
                "& .MuiLinearProgress-bar": {
                  borderRadius: 999,
                  background: `linear-gradient(90deg, ${C_INDIGO}, ${C_GREEN})`,
                },
              }}
            />

            <Stack spacing={1.25}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <RadioButtonUncheckedRoundedIcon sx={{ fontSize: 20, color: "text.secondary" }} />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  To do
                </Typography>
                <Typography variant="body2" fontWeight={700}>
                  {dataLoading ? "…" : todoC}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1}>
                <HourglassEmptyRoundedIcon sx={{ fontSize: 20, color: C_SKY }} />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  In progress
                </Typography>
                <Typography variant="body2" fontWeight={700}>
                  {dataLoading ? "…" : progC}
                </Typography>
              </Stack>
              <Stack direction="row" alignItems="center" spacing={1}>
                <CheckCircleRoundedIcon sx={{ fontSize: 20, color: C_GREEN }} />
                <Typography variant="body2" sx={{ flex: 1 }}>
                  Done
                </Typography>
                <Typography variant="body2" fontWeight={700}>
                  {dataLoading ? "…" : doneC}
                </Typography>
              </Stack>
            </Stack>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
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
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
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
