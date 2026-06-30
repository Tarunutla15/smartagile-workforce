// src/components/EmployeeDBComponent/SprintDashboard.jsx
import React, { useEffect } from 'react';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import NotificationsBell from '../../components/NotificationsBell';
import Avatar from '@mui/material/Avatar';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/system';
import PropTypes from 'prop-types';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import TextField from '@mui/material/TextField';
import Chip from '@mui/material/Chip';
import SHome from './SHome';
import SprintModelTable from '../../components/SprintModelTable';
import TaskBar from '../../components/TaskBar';
import SprintBurndownChart from '../../components/SprintBurndownChart';
import { SprintProvider, useSprint } from './SprintContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import Tooltip from '@mui/material/Tooltip';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import { api, mediaUrl } from '../../api/client';
import { useSession } from '../../context/SessionContext';
import { DarkModeIconButton } from '../../theme/DarkModeToggle';
import DashboardAppBar, { headerIconSx, HEADER_HEIGHT } from '../../components/DashboardAppBar';

const SprintDashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;
  const { user, loading: sessionLoading, clearSession, refreshSession } = useSession();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenuOpen = (event) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const menuItems = [
    { text: 'Organization (admin)', path: '/admin/dashboard', adminOnly: true },
    { text: 'Sprints', path: '/sprint-dashboard', adminOnly: false },
    { text: 'Employee profiles', path: '/admin/employee-profiles', adminOnly: true },
    { text: 'Group dashboard', path: '/group/dashboard', adminOnly: false },
    { text: 'Employee dashboard', path: '/employee/dashboard', adminOnly: false },
  ].filter((item) => !item.adminOnly || user?.role === 'admin');

  useEffect(() => {
    if (sessionLoading) return;
    if (!user) {
      navigate('/login', { replace: true });
    }
  }, [user, sessionLoading, navigate]);

  const handleLogout = async () => {
    try {
      const response = await api.post('/api/logout/', {});
      if (response.status === 200) {
        clearSession();
        await refreshSession({ quiet: true });
        navigate('/login');
      }
    } catch (error) {
      console.error('Error during logout', error);
    }
  };

  if (sessionLoading || !user) {
    return null;
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <CssBaseline />
      <DashboardAppBar
        subtitle="Sprints workspace"
        onMenuOpen={handleMenuOpen}
        navMenu={
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
            slotProps={{ paper: { sx: { mt: 1, borderRadius: 2, minWidth: 220 } } }}
          >
            {menuItems.map(
              (item) =>
                item.path !== currentPath && (
                  <MenuItem component={Link} to={item.path} onClick={handleMenuClose} key={item.path}>
                    {item.text.trim()}
                  </MenuItem>
                )
            )}
          </Menu>
        }
        actions={
          <>
            <DarkModeIconButton sx={headerIconSx} />
            <NotificationsBell sx={headerIconSx} />
            <Tooltip title="Log out">
              <IconButton sx={headerIconSx} onClick={handleLogout} size="small" aria-label="Log out">
                <LogoutIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </>
        }
        account={
          <Tooltip title={user.username || user.email || 'Account'}>
            <Avatar
              alt={user.username || ''}
              src={user.profile_photo ? mediaUrl(user.profile_photo) : ''}
              sx={{
                width: 36,
                height: 36,
                ml: 0.5,
                fontSize: 15,
                fontWeight: 700,
                bgcolor: 'rgba(255,255,255,0.20)',
                color: '#fff',
                boxShadow: '0 0 0 2px rgba(255,255,255,0.55)',
              }}
            >
              {(user.username?.[0] || user.email?.[0] || '?').toUpperCase()}
            </Avatar>
          </Tooltip>
        }
      />
      <SprintProvider>
        <VerticalTabs/>
      </SprintProvider>
    </Box>
  );
};


const STATUS_CHIP = {
  planned: { label: 'Planned', color: 'default' },
  active: { label: 'Active', color: 'success' },
  completed: { label: 'Completed', color: 'primary' },
};

function daysLeft(endDate) {
  if (!endDate) return null;
  const end = new Date(`${endDate}T23:59:59`);
  const diff = Math.ceil((end - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

function SprintSelectorBar() {
  const {
    projects,
    projectId,
    setProjectId,
    sprints,
    sprintId,
    setSprintId,
    selectedSprint,
    loadingProjects,
  } = useSprint();

  const left = daysLeft(selectedSprint?.end_date);

  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 2,
        px: 3,
        py: 1.5,
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <TextField
        select
        size="small"
        label="Project"
        value={projectId ?? ''}
        onChange={(e) => setProjectId(Number(e.target.value))}
        sx={{ minWidth: 220 }}
        disabled={loadingProjects || projects.length === 0}
      >
        {projects.length === 0 && <MenuItem value="">No projects</MenuItem>}
        {projects.map((p) => (
          <MenuItem key={p.id} value={p.id}>
            {p.name}
          </MenuItem>
        ))}
      </TextField>

      <TextField
        select
        size="small"
        label="Sprint"
        value={sprintId ?? ''}
        onChange={(e) => setSprintId(Number(e.target.value))}
        sx={{ minWidth: 220 }}
        disabled={sprints.length === 0}
      >
        {sprints.length === 0 && <MenuItem value="">No sprints</MenuItem>}
        {sprints.map((s) => (
          <MenuItem key={s.id} value={s.id}>
            {s.name}
          </MenuItem>
        ))}
      </TextField>

      {selectedSprint && (
        <>
          <Chip
            size="small"
            label={STATUS_CHIP[selectedSprint.status]?.label || selectedSprint.status}
            color={STATUS_CHIP[selectedSprint.status]?.color || 'default'}
            variant={selectedSprint.status === 'planned' ? 'outlined' : 'filled'}
          />
          {selectedSprint.goal && (
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 360 }} noWrap>
              {selectedSprint.goal}
            </Typography>
          )}
          {left !== null && selectedSprint.status === 'active' && (
            <Typography variant="caption" color={left < 0 ? 'error.main' : 'text.secondary'}>
              {left < 0 ? `${Math.abs(left)}d overdue` : `${left}d left`}
            </Typography>
          )}
        </>
      )}
    </Box>
  );
}


function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`vertical-tabpanel-${index}`}
      aria-labelledby={`vertical-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

TabPanel.propTypes = {
  children: PropTypes.node,
  index: PropTypes.number.isRequired,
  value: PropTypes.number.isRequired,
};

function VerticalTabs() {
  const [value, setValue] = React.useState(0);

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  return (
    <Box sx={{ flexGrow: 1, display: 'flex', minHeight: '100vh', pt: `${HEADER_HEIGHT}px` }}>
      <Tabs
        orientation="vertical"
        variant="scrollable"
        scrollButtons="auto"
        value={value}
        onChange={handleChange}
        aria-label="Sprint dashboard tabs"
        sx={{
          minWidth: 168,
          bgcolor: 'background.paper',
          borderRight: 1,
          borderColor: 'divider',
          boxShadow: (t) =>
            t.palette.mode === 'dark' ? '4px 0 24px rgba(0, 0, 0, 0.4)' : '4px 0 24px rgba(15, 23, 42, 0.05)',
          pt: 1,
          '& .MuiTab-root': {
            textTransform: 'none',
            alignItems: 'flex-start',
            fontWeight: 600,
            color: 'text.secondary',
            minHeight: 48,
            '&.Mui-selected': {
              color: 'primary.main',
              bgcolor: (t) =>
                t.palette.mode === 'dark' ? 'rgba(129, 140, 248, 0.16)' : 'rgba(79, 70, 229, 0.08)',
            },
          },
          '& .MuiTabs-indicator': { left: 0, width: 3, borderRadius: '0 4px 4px 0', bgcolor: 'primary.main' },
        }}
      >
        <Tab label="Overview" />
        <Tab label="Sprints" />
        <Tab label="Board" />
        <Tab label="Burndown" />
      </Tabs>
      <Box sx={{ flexGrow: 1, overflow: 'auto', minWidth: 0 }}>
        <SprintSelectorBar />
        <TabPanel value={value} index={0}>
          <SHome />
        </TabPanel>
        <TabPanel value={value} index={1}>
          <SprintModelTable />
        </TabPanel>
        <TabPanel value={value} index={2}>
          <TaskBar />
        </TabPanel>
        <TabPanel value={value} index={3}>
          <SprintBurndownChart />
        </TabPanel>
      </Box>
    </Box>
  );
}

export default SprintDashboard;
