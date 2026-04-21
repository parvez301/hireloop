import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Dev-mode auth bypass: seed localStorage so API calls use the dev-bypass token.
// Only activates on localhost when no real token is present.
// Set VITE_USE_REAL_AUTH=true in .env.local to exercise real Cognito Hosted UI locally.
if (
  import.meta.env.DEV &&
  window.location.hostname === 'localhost' &&
  !localStorage.getItem('ca:idToken') &&
  import.meta.env.VITE_USE_REAL_AUTH !== 'true'
) {
  localStorage.setItem('ca:idToken', 'dev-bypass');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
