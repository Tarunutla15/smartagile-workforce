import React from 'react';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import NotificationsBell from '../../components/NotificationsBell';
import Avatar from '@mui/material/Avatar';
import Tooltip from '@mui/material/Tooltip';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/system';
import PropTypes from 'prop-types';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import GHome from './GHome';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import { api, mediaUrl } from '../../api/client';
import { useSession } from '../../context/SessionContext';
import { DarkModeIconButton } from '../../theme/DarkModeToggle';
import DashboardAppBar, { headerIconSx, HEADER_HEIGHT } from '../../components/DashboardAppBar';

const GroupDashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname;
  const { user, clearSession, refreshSession } = useSession();
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
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <CssBaseline />
      <DashboardAppBar
        subtitle="Group workspace"
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
          <Tooltip title={user?.username || user?.email || 'Account'}>
            <Avatar
              alt={user?.username || ''}
              src={user?.profile_photo ? mediaUrl(user.profile_photo) : ''}
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
              {(user?.username?.[0] || user?.email?.[0] || '?').toUpperCase()}
            </Avatar>
          </Tooltip>
        }
      />
      <VerticalTabs/>
    </Box>
  );
};


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
          <Typography>{children}</Typography>
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

function a11yProps(index) {
  return {
    id: `vertical-tab-${index}`,
    'aria-controls': `vertical-tabpanel-${index}`,
  };
}

function VerticalTabs() {
  const [value, setValue] = React.useState(0);

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  return (
    <Box sx={{ flexGrow: 1, display: 'flex', minHeight: '100vh', pt: `${HEADER_HEIGHT}px` }}>
      <Tabs
        orientation="vertical"
        value={value}
        onChange={handleChange}
        aria-label="Group dashboard tabs"
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
        <Tab label="Dashboard" {...a11yProps(0)} />
      </Tabs>
      <Box sx={{ flexGrow: 1, overflow: 'auto', minWidth: 0 }}>
        <TabPanel value={value} index={0}>
          <GHome/>
        </TabPanel>
      </Box>
    </Box>
  );
}

export default GroupDashboard;