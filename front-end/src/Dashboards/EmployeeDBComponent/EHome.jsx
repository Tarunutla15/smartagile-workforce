import { PieChart } from '@mui/x-charts/PieChart';
import 'tailwindcss/tailwind.css';
import { Chart as ChartJS, ArcElement, Tooltip as ChartJSTooltip, Legend } from 'chart.js';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  TextField,
  MenuItem,
  Button,
  Chip,
  Grid,
  Stack,
  Tooltip,
} from '@mui/material';
import DesktopWindowsRoundedIcon from '@mui/icons-material/DesktopWindowsRounded';
import WorkHistoryOutlinedIcon from '@mui/icons-material/WorkHistoryOutlined';
import TimerOffOutlinedIcon from '@mui/icons-material/TimerOffOutlined';
import CrisisAlertIcon from '@mui/icons-material/CrisisAlert';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import FolderOpenRoundedIcon from '@mui/icons-material/FolderOpenRounded';
import AssignmentRoundedIcon from '@mui/icons-material/AssignmentRounded';
import React, { useContext, useState, useEffect, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AppDataContext } from './AppDataProvider';
import { api } from '../../api/client';
import { isWorkRelatedCategory } from '../../utils/workRelatedCategory';
import IntelligenceInsights from '../../components/IntelligenceInsights';
import IntelligenceSidePanel from '../../components/IntelligenceSidePanel';
import TopAppsWebsitesPanel from '../../components/TopAppsWebsitesPanel';

ChartJS.register(ArcElement, ChartJSTooltip, Legend);

/** Offline time: only "Windows Default Lock Screen" (see overviewStatsForRows). */
const WINDOWS_LOCK_SCREEN_APP = 'windows default lock screen';

function isWindowsLockScreenRow(r) {
  const n = String(r?.applicationname ?? '')
    .trim()
    .toLowerCase();
  return n === WINDOWS_LOCK_SCREEN_APP;
}

/** `duration` / `idle_seconds` from /api/appdata/ are in seconds (aggregated). */
function formatStatDurationFromSeconds(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  if (s <= 0) return '0m';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0 && m > 0 && r > 0) return `${h}h ${m}m ${r}s`;
  if (h > 0 && m > 0) return `${h}h ${m}m`;
  if (h > 0) return `${h}h`;
  if (m > 0 && r > 0) return `${m}m ${r}s`;
  if (m > 0) return `${m}m`;
  return `${r}s`;
}

function overviewStatsForRows(rows) {
  const list = Array.isArray(rows) ? rows : [];
  let totalSec = 0;
  let workSec = 0;
  let offlineSec = 0;
  for (const r of list) {
    const d = Math.max(0, Number(r?.duration) || 0);
    totalSec += d;
    if (isWindowsLockScreenRow(r)) offlineSec += d;
    // Do not count lock screen toward "work" — it can be mis-tagged and breaks work/active ratios.
    if (isWorkRelatedCategory(r?.category) && !isWindowsLockScreenRow(r)) workSec += d;
  }
  const activeSec = Math.max(0, totalSec - offlineSec);
  const productivityPct = totalSec > 0 ? Math.round((workSec * 100) / totalSec) : 0;
  const rawEffectiveness = activeSec > 0 ? (workSec * 100) / activeSec : 0;
  const effectivenessPct = Math.min(100, rawEffectiveness);
  return {
    totalSec,
    workSec,
    offlineSec,
    activeSec,
    productivityPct,
    effectivenessPct,
  };
}

const statAccent = '#4f46e5';
const cardHover = {
  borderColor: 'rgba(79, 70, 229, 0.35) !important',
  boxShadow: (t) => (t.palette.mode === 'dark' ? '0 8px 24px rgba(0,0,0,0.4)' : '0 8px 24px rgba(15, 23, 42, 0.1)'),
  transform: 'translateY(-2px)',
};

const StatCard = ({ title, value, icon, hint }) => {
  const inner = (
    <Card
      elevation={0}
      sx={{
        height: '100%',
        borderRadius: 2.5,
        border: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        background: (t) =>
          t.palette.mode === 'dark'
            ? 'linear-gradient(140deg, rgba(79, 70, 229,0.12) 0%, rgba(15,23,42,0.95) 60%)'
            : 'linear-gradient(140deg, #eef2ff 0%, #ffffff 55%, #f8fafc 100%)',
        transition: 'box-shadow 0.22s ease, border-color 0.22s ease, transform 0.22s ease',
        cursor: hint ? 'help' : 'default',
        '&:hover': cardHover,
      }}
    >
      <CardContent
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          py: 2.25,
          px: 2,
          '&:last-child': { pb: 2.25 },
        }}
      >
        <Box sx={{ minWidth: 0, pr: 1 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ textTransform: 'uppercase', letterSpacing: 0.55, fontWeight: 700, display: 'block' }}
          >
            {title}
          </Typography>
          <Typography
            variant="h5"
            sx={{ mt: 0.35, fontWeight: 800, letterSpacing: -0.4, lineHeight: 1.2, color: 'text.primary' }}
          >
            {value}
          </Typography>
        </Box>
        <Box
          aria-hidden
          sx={{
            color: statAccent,
            display: 'grid',
            placeItems: 'center',
            width: 48,
            height: 48,
            borderRadius: 2,
            flexShrink: 0,
            background: (t) =>
              t.palette.mode === 'dark' ? 'rgba(79, 70, 229, 0.18)' : 'rgba(79, 70, 229, 0.12)',
            border: 1,
            borderColor: 'rgba(79, 70, 229, 0.22)',
            fontSize: 24,
            '& .MuiSvgIcon-root': { fontSize: 28 },
          }}
        >
          {icon}
        </Box>
      </CardContent>
    </Card>
  );
  if (hint) {
    return (
      <Tooltip title={hint} arrow placement="top" enterNextDelay={400} leaveDelay={80}>
        {inner}
      </Tooltip>
    );
  }
  return inner;
};

const Productivity = () => {
  const { filteredData, loading } = useContext(AppDataContext);

  const { workSec, totalSec } = overviewStatsForRows(filteredData);
  const otherSec = Math.max(0, totalSec - workSec);
  const denom = totalSec > 0 ? totalSec : 1;
  const data = [
    { label: 'Work time', value: (workSec * 100) / denom },
    { label: 'Other', value: (otherSec * 100) / denom },
  ];

  return (
    <div>
      {!loading && (
        <PieChart
          series={[
            {
              data,
              highlightScope: { faded: 'global', highlighted: 'item' },
              faded: { innerRadius: 30, additionalRadius: -30, color: 'gray' },
            },
          ]}
          slotProps={{
            legend: {
              direction: 'column',
              position: { horizontal: 'right', vertical: 'top' },
              padding: -5,
            },
          }}
          height={200}
        />
      )}
      {loading && <p>Loading data...</p>}
    </div>
  );
};


const ProductivityChart = () => {
  return (
    <Stack spacing={2} sx={{ height: '100%' }}>
      <Box
        sx={{
          p: 2.25,
          borderRadius: 2.5,
          border: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          background: (t) =>
            t.palette.mode === 'dark'
              ? 'linear-gradient(160deg, rgba(79, 70, 229,0.1) 0%, rgba(15,23,42,0.95) 100%)'
              : 'linear-gradient(160deg, #eef2ff 0%, #ffffff 55%)',
          boxShadow: (t) => (t.palette.mode === 'dark' ? '0 2px 16px rgba(0,0,0,0.3)' : '0 2px 16px rgba(15, 23, 42, 0.07)'),
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5, letterSpacing: -0.2 }}>
          Top apps & websites
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5, lineHeight: 1.5 }}>
          Donut from your usage feed for the selected period — hover slices for time, click for details.
        </Typography>
        <TopAppsWebsitesPanel />
      </Box>
      <Box
        sx={{
          p: 2.25,
          borderRadius: 2.5,
          border: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          background: (t) =>
            t.palette.mode === 'dark'
              ? 'linear-gradient(165deg, rgba(79, 70, 229,0.1) 0%, rgba(15,23,42,0.95) 100%)'
              : 'linear-gradient(165deg, #eef2ff 0%, #ffffff 60%)',
          boxShadow: (t) => (t.palette.mode === 'dark' ? '0 2px 14px rgba(0,0,0,0.3)' : '0 2px 14px rgba(15, 23, 42, 0.06)'),
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5, letterSpacing: -0.2 }}>
          Productivity split
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
          Work vs non-work share of tracked rows in this period.
        </Typography>
        <Productivity />
      </Box>
    </Stack>
  );
};

const HOME_STATUS_LABELS = { todo: 'To do', inProgress: 'In progress', done: 'Done' };

const EmployeeWorkSection = () => {
  const [projects, setProjects] = useState([]);
  const [taskList, setTaskList] = useState([]);
  const [workLoading, setWorkLoading] = useState(true);

  const load = useCallback(async () => {
    setWorkLoading(true);
    try {
      const [pr, ts] = await Promise.all([
        api.get('/taskapi/my-projects/'),
        api.get('/taskapi/tasks/'),
      ]);
      setProjects(Array.isArray(pr.data) ? pr.data : []);
      setTaskList(Array.isArray(ts.data) ? ts.data : []);
    } catch {
      setProjects([]);
      setTaskList([]);
    } finally {
      setWorkLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openCount = taskList.filter((t) => t.status !== 'done').length;
  const recentTasks = [...taskList].sort((a, b) => {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0;
    const db = b.created_at ? new Date(b.created_at).getTime() : 0;
    return db - da;
  }).slice(0, 6);

  return (
    <>
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' },
          mt: 0.5,
          mb: 0.5,
        }}
      >
        <StatCard
          title="My projects"
          value={workLoading ? '…' : String(projects.length)}
          icon={<FolderOpenRoundedIcon />}
          hint="Projects you’re a member of (from Organization → Projects)."
        />
        <StatCard
          title="Open tasks"
          value={workLoading ? '…' : String(openCount)}
          icon={<AssignmentRoundedIcon />}
          hint="Tasks not marked done — from assignments and tasks you created."
        />
      </Box>

      <Grid container spacing={2} alignItems="flex-start" sx={{ mt: 0.5 }}>
        <Grid item xs={12} lg={4}>
          <Box
            sx={{
              borderRadius: 2.5,
              overflow: 'hidden',
              border: 1,
              borderColor: 'divider',
              display: 'flex',
              flexDirection: 'column',
              background: (t) =>
                t.palette.mode === 'dark'
                  ? 'linear-gradient(180deg, rgba(15,23,42,0.9) 0%, #0f172a 100%)'
                  : 'linear-gradient(180deg, #f8fffe 0%, #ffffff 50%)',
              boxShadow: (t) => (t.palette.mode === 'dark' ? '0 4px 20px rgba(0,0,0,0.35)' : '0 4px 20px rgba(15, 23, 42, 0.07)'),
            }}
          >
            <Box
              sx={{
                p: 2.25,
                pb: 2,
                background: (t) =>
                  t.palette.mode === 'dark' ? 'rgba(79, 70, 229, 0.1)' : 'rgba(79, 70, 229, 0.08)',
                borderBottom: 1,
                borderColor: 'divider',
              }}
            >
              <Stack direction="row" alignItems="center" gap={1.5}>
                <Box
                  sx={{
                    width: 46,
                    height: 46,
                    borderRadius: 2,
                    display: 'grid',
                    placeItems: 'center',
                    bgcolor: 'rgba(79, 70, 229, 0.2)',
                    color: statAccent,
                    border: 1,
                    borderColor: 'rgba(79, 70, 229, 0.35)',
                  }}
                >
                  <FolderOpenRoundedIcon sx={{ fontSize: 26 }} />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: -0.3, lineHeight: 1.2 }}>
                    Projects & tasks
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.4 }}>
                    Mirrors the <strong>Projects</strong> and <strong>Tasks</strong> tabs — from your org and your own
                    work.
                  </Typography>
                </Box>
              </Stack>
            </Box>

            <Box sx={{ p: 2.5, flex: 1, display: 'flex', flexDirection: 'column' }}>
              {workLoading ? (
                <Typography variant="body2" color="text.secondary">
                  Loading…
                </Typography>
              ) : (
                <>
                  <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.25 }}>
                    <Typography variant="overline" sx={{ fontWeight: 800, letterSpacing: 0.6, color: 'text.secondary' }}>
                      Projects
                    </Typography>
                    <Chip
                      size="small"
                      label={projects.length}
                      sx={{ fontWeight: 800, bgcolor: 'rgba(79, 70, 229, 0.15)', color: 'primary.main' }}
                    />
                  </Stack>
                  {projects.length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 2, py: 1.5, px: 1.5, borderRadius: 2, bgcolor: (t) => (t.palette.mode === 'dark' ? 'action.hover' : 'grey.50') }}
                    >
                      No project yet. Your admin adds you from <strong>Organization → Projects</strong>.
                    </Typography>
                  ) : (
                    <Stack spacing={1.15} sx={{ mb: 2.5 }}>
                      {projects.slice(0, 4).map((p) => (
                        <Box
                          key={p.id}
                          sx={{
                            p: 1.4,
                            borderRadius: 2,
                            border: 1,
                            borderColor: 'divider',
                            bgcolor: 'background.paper',
                            transition: '0.2s ease',
                            '&:hover': {
                              borderColor: 'rgba(79, 70, 229, 0.45)',
                              boxShadow: (t) => (t.palette.mode === 'dark' ? '0 2px 10px rgba(0,0,0,0.3)' : '0 2px 12px rgba(15,23,42,0.08)'),
                            },
                          }}
                        >
                          <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
                            <Typography variant="body2" fontWeight={700} noWrap sx={{ minWidth: 0 }}>
                              {p.name}
                            </Typography>
                            <Chip
                              size="small"
                              label={p.your_role || 'member'}
                              variant="outlined"
                              sx={{ fontWeight: 600, borderColor: 'rgba(79, 70, 229, 0.5)', color: 'primary.main' }}
                            />
                          </Stack>
                        </Box>
                      ))}
                      {projects.length > 4 && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ pl: 0.5 }}>
                          +{projects.length - 4} more — use the <strong>Projects</strong> tab
                        </Typography>
                      )}
                    </Stack>
                  )}

                  <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.25, mt: 0.5 }}>
                    <Typography variant="overline" sx={{ fontWeight: 800, letterSpacing: 0.6, color: 'text.secondary' }}>
                      Recent tasks
                    </Typography>
                    <Chip
                      size="small"
                      label={taskList.length}
                      sx={{ fontWeight: 800, bgcolor: (t) => (t.palette.mode === 'dark' ? 'action.selected' : 'action.hover') }}
                    />
                  </Stack>
                  {taskList.length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ py: 1.5, lineHeight: 1.5 }}
                    >
                      No tasks yet. Use the <strong>Tasks</strong> tab to add work or wait for admin assignments.
                    </Typography>
                  ) : (
                    <Stack spacing={1.15} sx={{ mb: 2 }}>
                      {recentTasks.map((t) => (
                        <Box
                          key={t.id}
                          sx={{
                            p: 1.35,
                            borderRadius: 2,
                            border: 1,
                            borderColor: 'divider',
                            borderLeft: 4,
                            borderLeftColor:
                              t.status === 'done'
                                ? 'success.main'
                                : t.status === 'inProgress'
                                  ? 'warning.main'
                                  : 'grey.500',
                            bgcolor: (t2) => (t2.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'),
                            transition: '0.2s ease',
                            '&:hover': {
                              borderColor: 'rgba(79, 70, 229, 0.35)',
                              boxShadow: (t2) => (t2.palette.mode === 'dark' ? 2 : 1),
                            },
                          }}
                        >
                          <Typography variant="body2" fontWeight={700} sx={{ lineHeight: 1.3 }}>
                            {t.title}
                          </Typography>
                          <Stack direction="row" flexWrap="wrap" useFlexGap columnGap={0.75} rowGap={0.5} sx={{ mt: 0.75 }}>
                            <Chip
                              size="small"
                              label={HOME_STATUS_LABELS[t.status] || t.status}
                              color={t.status === 'done' ? 'success' : t.status === 'inProgress' ? 'warning' : 'default'}
                            />
                            {t.task_origin === 'assigned' ? (
                              <Chip size="small" color="primary" label="Assigned" />
                            ) : (
                              <Chip
                                size="small"
                                variant="outlined"
                                label="Yours"
                                sx={{ borderColor: 'rgba(79, 70, 229, 0.45)' }}
                              />
                            )}
                            {t.project_name ? (
                              <Chip size="small" variant="outlined" label={t.project_name} />
                            ) : null}
                          </Stack>
                          {t.created_at ? (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              display="block"
                              sx={{ mt: 0.9, fontWeight: 500 }}
                            >
                              {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
                            </Typography>
                          ) : null}
                        </Box>
                      ))}
                    </Stack>
                  )}
                  <Button
                    size="medium"
                    fullWidth
                    onClick={load}
                    disabled={workLoading}
                    variant="contained"
                    sx={{
                      mt: 2.5,
                      textTransform: 'none',
                      fontWeight: 700,
                      borderRadius: 2,
                      py: 1.1,
                      bgcolor: statAccent,
                      boxShadow: '0 2px 8px rgba(79, 70, 229, 0.35)',
                      '&:hover': { bgcolor: '#4338ca' },
                    }}
                  >
                    Refresh projects & tasks
                  </Button>
                </>
              )}
            </Box>
          </Box>
        </Grid>
        <Grid item xs={12} lg={5}>
          <ProductivityChart />
        </Grid>
        <Grid item xs={12} lg={3}>
          <IntelligenceSidePanel />
        </Grid>
      </Grid>
    </>
  );
};

const EHome = () => {
  const {
    dateFilter,
    setStartDate,
    setEndDate,
    startDate,
    endDate,
    filteredData,
    loading,
    handleDateFilterChange,
    applyDateFilter,
  } = useContext(AppDataContext);

  const { totalSec, workSec, offlineSec, productivityPct, effectivenessPct } = overviewStatsForRows(filteredData);
  const desktopDisplay = formatStatDurationFromSeconds(totalSec);
  const workDisplay = formatStatDurationFromSeconds(workSec);
  const offlineDisplay = formatStatDurationFromSeconds(offlineSec);
  const effectivenessDisplay =
    totalSec > 0 && offlineSec < totalSec ? `${effectivenessPct.toFixed(2)}%` : '—';

  if (loading) {
    return (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <Typography color="text.secondary">Loading…</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1280, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={2} sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Overview
        </Typography>
        <Stack direction="row" flexWrap="wrap" alignItems="center" spacing={1}>
          <FormControl size="small" variant="outlined" sx={{ minWidth: 140 }}>
            <InputLabel id="date-filter-label">Period</InputLabel>
            <Select labelId="date-filter-label" value={dateFilter} onChange={handleDateFilterChange} label="Period">
              <MenuItem value="Today">Today</MenuItem>
              <MenuItem value="Yesterday">Yesterday</MenuItem>
              <MenuItem value="This Week">This week</MenuItem>
              <MenuItem value="Custom">Custom</MenuItem>
            </Select>
          </FormControl>
          {dateFilter === 'Custom' && (
            <>
              <TextField
                size="small"
                label="From"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                size="small"
                label="To"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </>
          )}
          <Button variant="contained" onClick={applyDateFilter} sx={{ bgcolor: statAccent, '&:hover': { bgcolor: '#4338ca' } }}>
            Apply
          </Button>
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)',
            lg: 'repeat(5, minmax(0, 1fr))',
          },
        }}
      >
        <StatCard
          title="Desktop time"
          value={desktopDisplay}
          icon={<DesktopWindowsRoundedIcon />}
          hint="Total tracked on-desktop seconds in your usage feed for the selected period (after Apply)."
        />
        <StatCard
          title="Time at work"
          value={workDisplay}
          icon={<WorkHistoryOutlinedIcon />}
          hint="Work-tagged duration excluding “Windows Default Lock Screen” (same period)."
        />
        <StatCard
          title="Offline time"
          value={offlineDisplay}
          icon={<TimerOffOutlinedIcon />}
          hint="Time on the “Windows Default Lock Screen” app only (tracked duration for that foreground title in the selected period)."
        />
        <StatCard
          title="Effectiveness"
          value={effectivenessDisplay}
          icon={<CrisisAlertIcon />}
          hint="Work time (excl. lock screen) ÷ active time (desktop − lock screen), capped at 100%."
        />
        <StatCard
          title="Productivity"
          value={`${productivityPct}%`}
          icon={<TrendingUpIcon />}
          hint="Work-tagged time excl. lock screen ÷ total desktop time for the period."
        />
      </Box>

      <IntelligenceInsights />

      <EmployeeWorkSection />
    </Box>
  );
};

export default EHome;
