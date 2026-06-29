import React from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import NotificationsIcon from '@mui/icons-material/Notifications';
import Avatar from '@mui/material/Avatar';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/system';
import PropTypes from 'prop-types';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import GHome from './GHome';
import { useNavigate } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import { api, mediaUrl } from '../../api/client';
import { useSession } from '../../context/SessionContext';
import { APPBAR_GRADIENT, APPBAR_SHADOW } from '../../utils/chartTheme';
import { DarkModeIconButton } from '../../theme/DarkModeToggle';

const GroupDashboard = () => {
  const navigate = useNavigate();
  const { user, clearSession, refreshSession } = useSession();

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
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          background: APPBAR_GRADIENT,
          boxShadow: APPBAR_SHADOW,
        }}
      >
        <Toolbar sx={{ minHeight: 56, height: 56, gap: 1 }}>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1, fontWeight: 700, letterSpacing: '-0.02em' }}>
            SmartAgile <Box component="span" sx={{ fontWeight: 500, opacity: 0.85 }}>· Group</Box>
          </Typography>
          <DarkModeIconButton />
          <IconButton color="inherit" size="small">
            <NotificationsIcon />
          </IconButton>
          <Avatar
            alt=""
            src={user?.profile_photo ? mediaUrl(user.profile_photo) : ''}
            sx={{ width: 32, height: 32 }}
          />
          <IconButton color="inherit" onClick={handleLogout} size="small" aria-label="Log out">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
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
    <Box sx={{ flexGrow: 1, display: 'flex', minHeight: '100vh', pt: '56px' }}>
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
          boxShadow: '4px 0 24px rgba(15, 23, 42, 0.05)',
          pt: 1,
          '& .MuiTab-root': {
            textTransform: 'none',
            alignItems: 'flex-start',
            fontWeight: 600,
            color: '#64748b',
            minHeight: 48,
            '&.Mui-selected': { color: '#4338ca', bgcolor: 'rgba(79, 70, 229,0.08)' },
          },
          '& .MuiTabs-indicator': { left: 0, width: 3, borderRadius: '0 4px 4px 0', bgcolor: '#4f46e5' },
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