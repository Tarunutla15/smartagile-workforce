// src/components/EmployeeDBComponent/SprintDashboard.jsx
import React, { useEffect } from 'react';
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
import SHome from './SHome';
import SprintModelTable from '../../components/SprintModelTable';
import TaskBar from '../../components/TaskBar';
import SprintBurndownChart from '../../components/SprintBurndownChart';
import { useNavigate } from 'react-router-dom';
import LogoutIcon from '@mui/icons-material/Logout';
import { api, mediaUrl } from '../../api/client';
import { useSession } from '../../context/SessionContext';

const SprintDashboard = () => {
  const navigate = useNavigate();
  const { user, loading: sessionLoading, clearSession, refreshSession } = useSession();

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
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          backgroundColor: '#3f51b5',
          height:55
        }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            SmartAgile
          </Typography>
          
          <Avatar alt="User Avatar" src={user.profile_photo ? mediaUrl(user.profile_photo) : ''} />
          <IconButton color="inherit">
            <NotificationsIcon />
          </IconButton>
          <IconButton color="inherit" onClick={handleLogout}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
      <div className='mt-8'>
      <VerticalTabs/>
      </div>
      
      
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
    <Box sx={{ flexGrow: 1, display: 'flex', minHeight: '100vh', pt: 8 }}>
      <Tabs
        orientation="vertical"
        variant="scrollable"
        value={value}
        onChange={handleChange}
        aria-label="Sprint dashboard tabs"
        sx={{ borderRight: 1, borderColor: 'divider', minWidth: 160 }}
      >
        <Tab label="Home" />
        <Tab label="Sprint table" />
        <Tab label="Tasks" />
        <Tab label="Burndown" />
      </Tabs>
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
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
