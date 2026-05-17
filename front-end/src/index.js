import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { AppDataProvider } from './Dashboards/EmployeeDBComponent/AppDataProvider';
import { SessionProvider } from './context/SessionContext';
import reportWebVitals from './reportWebVitals';

// Browsers (often with MUI, charts, or Collapse) can emit this during layout; CRA's overlay
// treats it as a runtime error. It is not an app bug—suppress so dev UX is usable.
window.addEventListener(
  'error',
  (e) => {
    const msg = String(e?.message || '');
    if (msg.includes('ResizeObserver loop')) {
      e.stopImmediatePropagation();
    }
  },
  true
);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <SessionProvider>
    <AppDataProvider>
      <App />
    </AppDataProvider>
  </SessionProvider>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
