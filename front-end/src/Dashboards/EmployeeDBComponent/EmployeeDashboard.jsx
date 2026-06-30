
import { Box, Tabs, Tab } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import TaskIcon from '@mui/icons-material/Task';
import AttendanceIcon from '@mui/icons-material/AccessTime';
import ProjectIcon from '@mui/icons-material/Folder';
import AppsIcon from '@mui/icons-material/Apps';
import SettingsIcon from '@mui/icons-material/Settings';
import EHome from './EHome';
import Tasks from './Tasks';
import Attendance from './Attendance';
import Projects from './Projects';
import AppsWebsites from './AppsWebsites';
import Settings from './Settings';
import IconButton from '@mui/material/IconButton';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import CssBaseline from '@mui/material/CssBaseline';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import { useNavigate, useLocation } from 'react-router-dom';
import React, { useState, useEffect, useContext } from 'react';
import { Link } from 'react-router-dom';
import { Menu, MenuItem } from '@mui/material';
import { AppDataContext } from './AppDataProvider';
import { useSession } from '../../context/SessionContext';
import { api, mediaUrl } from '../../api/client';
import TrackingDisclosureDialog from '../../components/TrackingDisclosureDialog';
import { DarkModeIconButton } from '../../theme/DarkModeToggle';
import DashboardAppBar, { headerIconSx } from '../../components/DashboardAppBar';
import NotificationsBell from '../../components/NotificationsBell';

const EmployeeDashboard = () => {
  const navigate = useNavigate();
  const { user, loading: sessionLoading, clearSession, refreshSession } = useSession();
  const { refetch: refreshUsageData, loading: usageLoading } = useContext(AppDataContext);

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
  const [anchorEl, setAnchorEl] = useState(null);
    const location = useLocation();
    const currentPath = location.pathname;
  
    const handleMenuOpen = (event) => {
      setAnchorEl(event.currentTarget);
    };
  
    const handleMenuClose = () => {
      setAnchorEl(null);
    };

  
    const menuItems = [
      { text: 'Organization (admin)', path: '/admin/dashboard', adminOnly: true },
      { text: 'Sprints', path: '/sprint-dashboard', adminOnly: false },
      { text: 'Employee profiles', path: '/admin/employee-profiles', adminOnly: true },
      { text: 'Group dashboard', path: '/group/dashboard', adminOnly: false },
      { text: 'Employee dashboard', path: '/employee/dashboard', adminOnly: false },
    ].filter((item) => !item.adminOnly || user?.role === 'admin');
    const [anchorE2, setAnchorE2] = useState(null);
    const handleMenuOpen1 = (event) => {
      setAnchorE2(event.currentTarget);
    };
  
    const handleMenuClose1 = () => {
      setAnchorE2(null);
    };
    const accountMenuItems = [
      { text: 'Profile', path: '/employee-profiles', type: 'link' },
      { text: 'Logout', type: 'logout' },
    ];

  if (sessionLoading || !user) {
    return null;
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <TrackingDisclosureDialog />
      <CssBaseline />
      <DashboardAppBar
        subtitle="My workspace"
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
            <Tooltip title="Refresh usage data">
              <span>
                <IconButton
                  sx={{ ...headerIconSx, '&:disabled': { color: 'rgba(255,255,255,0.5)' } }}
                  aria-label="Refresh usage data"
                  onClick={() => refreshUsageData?.()}
                  disabled={usageLoading}
                  size="small"
                >
                  <RefreshRoundedIcon
                    fontSize="small"
                    sx={{
                      animation: usageLoading ? 'spin 0.8s linear infinite' : 'none',
                      '@keyframes spin': {
                        from: { transform: 'rotate(0deg)' },
                        to: { transform: 'rotate(360deg)' },
                      },
                    }}
                  />
                </IconButton>
              </span>
            </Tooltip>
          </>
        }
        account={
          <>
            <Tooltip title={user?.username || user?.email || 'Account'}>
              <IconButton aria-label="Account menu" onClick={handleMenuOpen1} size="small" sx={{ ml: 0.5, p: 0.25 }}>
                <Avatar
                  alt={user?.username || ''}
                  src={user?.profile_photo ? mediaUrl(user.profile_photo) : ''}
                  sx={{
                    width: 36,
                    height: 36,
                    fontSize: 15,
                    fontWeight: 700,
                    bgcolor: 'rgba(255,255,255,0.20)',
                    color: '#fff',
                    boxShadow: '0 0 0 2px rgba(255,255,255,0.55)',
                  }}
                >
                  {(user?.username?.[0] || user?.email?.[0] || '?').toUpperCase()}
                </Avatar>
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={anchorE2}
              open={Boolean(anchorE2)}
              onClose={handleMenuClose1}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
              slotProps={{ paper: { sx: { mt: 1, borderRadius: 2, minWidth: 180 } } }}
            >
              {accountMenuItems.map((item) =>
                item.type === 'logout' ? (
                  <MenuItem
                    key={item.text}
                    onClick={() => {
                      handleMenuClose1();
                      handleLogout();
                    }}
                  >
                    {item.text}
                  </MenuItem>
                ) : (
                  <MenuItem component={Link} to={item.path} onClick={handleMenuClose1} key={item.path}>
                    {item.text}
                  </MenuItem>
                )
              )}
            </Menu>
          </>
        }
      />
      <VerticalTabs />
    </Box>
  );
};
const APP_BAR_HEIGHT = 64;
const SIDEBAR_WIDTH = 72;

const a11yProps = (index) => ({
  id: `vertical-tab-${index}`,
  'aria-controls': `vertical-tabpanel-${index}`,
});

const TabPanel = (props) => {
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
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const TAB_FROM_STATE = {
  home: 0,
  tasks: 1,
  attendance: 2,
  projects: 3,
  apps: 4,
  settings: 5,
};

const VerticalTabs = () => {
  const [value, setValue] = useState(0);
  const location = useLocation();
  const navigate = useNavigate();

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  useEffect(() => {
    const key = location.state?.dashboardTab;
    if (key == null) return;
    const idx = TAB_FROM_STATE[key];
    if (idx == null) return;
    setValue(idx);
    navigate(location.pathname, { replace: true, state: {} });
  }, [location.state, location.pathname, navigate]);

  return (
    <Box
      component="main"
      sx={{
        display: 'flex',
        width: '100%',
        minHeight: '100vh',
        pt: `${APP_BAR_HEIGHT}px`,
      }}
    >
      <Box
        sx={{
          position: 'fixed',
          top: APP_BAR_HEIGHT,
          left: 0,
          width: SIDEBAR_WIDTH,
          height: `calc(100vh - ${APP_BAR_HEIGHT}px)`,
          bgcolor: 'background.paper',
          borderRight: 1,
          borderColor: 'divider',
          boxShadow: '4px 0 24px rgba(15, 23, 42, 0.06)',
          zIndex: (theme) => theme.zIndex.drawer,
        }}
      >
        <Tabs
          orientation="vertical"
          variant="scrollable"
          scrollButtons="auto"
          value={value}
          onChange={handleChange}
          aria-label="Employee dashboard sections"
          sx={{
            pt: 1,
            '& .MuiTab-root': {
              textTransform: 'none',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 64,
              minWidth: SIDEBAR_WIDTH,
              maxWidth: SIDEBAR_WIDTH,
              px: 0.5,
              fontSize: 9,
              color: '#64748b',
              '&.Mui-selected': {
                fontWeight: 700,
                fontSize: 9,
                color: '#4338ca',
                bgcolor: 'rgba(79, 70, 229, 0.08)',
              },
            },
            '& .MuiTab-wrapper': {
              flexDirection: 'column',
              gap: 0.25,
            },
            '& .MuiTabs-indicator': {
              left: 0,
              width: 3,
              borderRadius: '0 4px 4px 0',
              bgcolor: '#4f46e5',
            },
          }}
        >
          <Tab icon={<DashboardIcon fontSize="small" />} label="Home" {...a11yProps(0)} />
          <Tab icon={<TaskIcon fontSize="small" />} label="Tasks" {...a11yProps(1)} />
          <Tab icon={<AttendanceIcon fontSize="small" />} label="Attendance" {...a11yProps(2)} />
          <Tab icon={<ProjectIcon fontSize="small" />} label="Projects" {...a11yProps(3)} />
          <Tab icon={<AppsIcon fontSize="small" />} label="Apps" {...a11yProps(4)} />
          <Tab icon={<SettingsIcon fontSize="small" />} label="Settings" {...a11yProps(5)} />
        </Tabs>
      </Box>
      <Box
        sx={{
          flexGrow: 1,
          ml: `${SIDEBAR_WIDTH}px`,
          width: `calc(100% - ${SIDEBAR_WIDTH}px)`,
          minWidth: 0,
          bgcolor: 'background.default',
        }}
      >
        <TabPanel value={value} index={0}>
          <EHome />
        </TabPanel>
        <TabPanel value={value} index={1}>
          <Tasks />
        </TabPanel>
        <TabPanel value={value} index={2}>
          <Attendance />
        </TabPanel>
        <TabPanel value={value} index={3}>
          <Projects />
        </TabPanel>
        <TabPanel value={value} index={4}>
          <AppsWebsites />
        </TabPanel>
        <TabPanel value={value} index={5}>
          <Settings />
        </TabPanel>
        
      </Box>
    </Box>
  );
};

export default EmployeeDashboard;