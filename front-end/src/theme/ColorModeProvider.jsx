import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';

const STORAGE_KEY = 'sa-theme';
const ColorModeContext = createContext({ mode: 'light', toggleMode: () => {}, setMode: () => {} });

export const useColorMode = () => useContext(ColorModeContext);

function getInitialMode() {
  if (typeof window === 'undefined') return 'light';
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
  } catch {
    /* ignore */
  }
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

export const ColorModeProvider = ({ children }) => {
  const [mode, setMode] = useState(getInitialMode);

  // Drive Tailwind's `dark` class + persist the choice.
  useEffect(() => {
    const root = document.documentElement;
    if (mode === 'dark') root.classList.add('dark');
    else root.classList.remove('dark');
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  const toggleMode = useCallback(() => {
    setMode((m) => (m === 'dark' ? 'light' : 'dark'));
  }, []);

  // MUI theme: indigo primary, violet secondary, mode-aware surfaces.
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: '#4f46e5' },
          secondary: { main: '#7c3aed' },
          ...(mode === 'dark'
            ? { background: { default: '#0b1120', paper: '#0f172a' } }
            : { background: { default: '#f1f5f9', paper: '#ffffff' } }),
        },
        shape: { borderRadius: 12 },
        typography: {
          fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
        },
      }),
    [mode]
  );

  const value = useMemo(() => ({ mode, toggleMode, setMode }), [mode, toggleMode]);

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </ColorModeContext.Provider>
  );
};

export default ColorModeProvider;
