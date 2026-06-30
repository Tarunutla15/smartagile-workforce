import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge,
  Box,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  Menu,
  Tooltip,
  Typography,
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone';
import { api } from '../api/client';

const POLL_MS = 45000;

const SEVERITY_COLOR = {
  critical: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
};

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/**
 * Header bell showing proactive nudges (Tier 2C). Polls the notifications API, shows an
 * unread badge, and opens a dropdown; clicking an item marks it read and deep-links to the
 * relevant page. `sx` lets the caller match header (white-on-gradient) styling.
 */
export default function NotificationsBell({ sx }) {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [anchorEl, setAnchorEl] = useState(null);
  const [loading, setLoading] = useState(false);
  const open = Boolean(anchorEl);
  const timerRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/api/notifications/?limit=20');
      setItems(data?.results || []);
      setUnread(data?.unread || 0);
    } catch {
      /* unauthenticated or offline — leave state as-is */
    }
  }, []);

  useEffect(() => {
    load();
    timerRef.current = setInterval(load, POLL_MS);
    return () => clearInterval(timerRef.current);
  }, [load]);

  const handleOpen = async (e) => {
    setAnchorEl(e.currentTarget);
    setLoading(true);
    await load();
    setLoading(false);
  };

  const markAllRead = async () => {
    try {
      await api.post('/api/notifications/read-all/');
      setUnread(0);
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch {
      /* ignore */
    }
  };

  const handleClick = async (n) => {
    setAnchorEl(null);
    if (!n.read) {
      try {
        await api.post(`/api/notifications/${n.id}/read/`);
        setUnread((u) => Math.max(0, u - 1));
      } catch {
        /* ignore */
      }
    }
    if (n.link) navigate(n.link);
  };

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton sx={sx} size="small" onClick={handleOpen} aria-label="Notifications">
          <Badge badgeContent={unread} color="error" max={99}>
            {unread > 0 ? (
              <NotificationsIcon fontSize="small" />
            ) : (
              <NotificationsNoneIcon fontSize="small" />
            )}
          </Badge>
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { width: 360, maxWidth: '92vw', maxHeight: 460 } } }}
      >
        <Box
          sx={{
            px: 2,
            py: 1.25,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Typography sx={{ fontWeight: 700 }}>Notifications</Typography>
          {unread > 0 && (
            <Button size="small" onClick={markAllRead}>
              Mark all read
            </Button>
          )}
        </Box>
        <Divider />
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={22} />
          </Box>
        )}
        {!loading && items.length === 0 && (
          <Box sx={{ px: 2, py: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              You're all caught up.
            </Typography>
          </Box>
        )}
        {!loading &&
          items.map((n) => (
            <Box
              key={n.id}
              onClick={() => handleClick(n)}
              sx={{
                px: 2,
                py: 1.25,
                cursor: 'pointer',
                display: 'flex',
                gap: 1.25,
                alignItems: 'flex-start',
                bgcolor: n.read ? 'transparent' : 'action.hover',
                '&:hover': { bgcolor: 'action.selected' },
                borderBottom: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Box
                sx={{
                  mt: 0.6,
                  width: 9,
                  height: 9,
                  borderRadius: '50%',
                  flexShrink: 0,
                  bgcolor: SEVERITY_COLOR[n.severity] || SEVERITY_COLOR.info,
                  opacity: n.read ? 0.35 : 1,
                }}
              />
              <Box sx={{ minWidth: 0, flexGrow: 1 }}>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: n.read ? 500 : 700, lineHeight: 1.3 }}
                >
                  {n.title}
                </Typography>
                {n.body && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    {n.body}
                  </Typography>
                )}
                <Typography variant="caption" color="text.disabled">
                  {timeAgo(n.created_at)}
                </Typography>
              </Box>
            </Box>
          ))}
      </Menu>
    </>
  );
}
