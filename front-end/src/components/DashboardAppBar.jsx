import React from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Box from '@mui/material/Box';
import MenuIcon from '@mui/icons-material/Menu';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import { APPBAR_GRADIENT, APPBAR_SHADOW } from '../utils/chartTheme';

export const HEADER_HEIGHT = 64;

// White icon-button styling for use on the gradient header.
export const headerIconSx = { color: '#fff' };

// Translucent rounded "pill" that groups header action buttons.
export const headerActionPillSx = {
  display: 'flex',
  alignItems: 'center',
  gap: 0.25,
  p: 0.5,
  borderRadius: 999,
  bgcolor: 'rgba(255,255,255,0.12)',
  border: '1px solid rgba(255,255,255,0.16)',
};

/** Brand lockup: glassy logo badge + product name + uppercase eyebrow. */
export function BrandMark({ subtitle }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexGrow: 1, minWidth: 0 }}>
      <Box
        sx={{
          width: 38,
          height: 38,
          borderRadius: 2.5,
          display: 'grid',
          placeItems: 'center',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.30), rgba(255,255,255,0.08))',
          boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.35)',
          flexShrink: 0,
        }}
      >
        <BoltRoundedIcon sx={{ color: '#fff', fontSize: 22 }} />
      </Box>
      <Box sx={{ minWidth: 0, lineHeight: 1 }}>
        <Typography
          noWrap
          sx={{ fontWeight: 800, fontSize: 17, letterSpacing: '-0.02em', color: '#fff', lineHeight: 1.15 }}
        >
          SmartAgile
        </Typography>
        {subtitle && (
          <Typography
            noWrap
            sx={{
              color: 'rgba(255,255,255,0.78)',
              fontWeight: 700,
              fontSize: 10,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
            }}
          >
            {subtitle}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

/**
 * Shared modern header used across every dashboard.
 *
 * Props:
 * - subtitle:   uppercase eyebrow under "SmartAgile" (e.g. "Sprints workspace")
 * - onMenuOpen: click handler for the hamburger (omit to hide the button)
 * - navMenu:    the <Menu> element rendered next to the hamburger
 * - actions:    nodes placed inside the translucent action pill (toggle/notifications/etc.)
 * - account:    node placed after the pill (avatar / account menu)
 */
export default function DashboardAppBar({ subtitle, onMenuOpen, navMenu, actions, account }) {
  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        background: APPBAR_GRADIENT,
        boxShadow: APPBAR_SHADOW,
        backdropFilter: 'saturate(140%) blur(8px)',
        borderBottom: '1px solid rgba(255,255,255,0.10)',
      }}
    >
      <Toolbar sx={{ minHeight: HEADER_HEIGHT, height: HEADER_HEIGHT, gap: 1.25, px: { xs: 1.5, sm: 2.5 } }}>
        {onMenuOpen && (
          <Tooltip title="Menu">
            <IconButton
              edge="start"
              aria-label="Open navigation menu"
              onClick={onMenuOpen}
              sx={{
                color: '#fff',
                bgcolor: 'rgba(255,255,255,0.12)',
                borderRadius: 2,
                '&:hover': { bgcolor: 'rgba(255,255,255,0.22)' },
              }}
            >
              <MenuIcon />
            </IconButton>
          </Tooltip>
        )}
        {navMenu}
        <BrandMark subtitle={subtitle} />
        {actions && <Box sx={headerActionPillSx}>{actions}</Box>}
        {account}
      </Toolbar>
    </AppBar>
  );
}
