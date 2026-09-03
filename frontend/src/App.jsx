import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchHealthStatus } from './services/api';
import './App.css';

function App() {
  const [statusMessage, setStatusMessage] = useState('Checking...');

  useEffect(() => {
    let isMounted = true;

    async function checkBackend() {
      try {
        await fetchHealthStatus();
        if (isMounted) {
          setStatusMessage('Backend Connected');
        }
      } catch (error) {
        if (isMounted) {
          setStatusMessage('Backend Unavailable');
        }
      }
    }

    checkBackend();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="app-shell">
      <main className="hero-card">
        <nav className="page-nav">
          <Link className="nav-link" to="/">Home</Link>
          <Link className="nav-link" to="/report">Report an Issue</Link>
          <Link className="nav-link" to="/incidents">Incidents</Link>
        </nav>

        <h1>Municipality Crowd Verification System</h1>
        <p className="subtitle">Crowd-Report Verification and<br />Decision Support Platform</p>
        <div className="status-card">
          <span className="status-label">System Status:</span>
          <span className="status-value">{statusMessage}</span>
        </div>
      </main>
    </div>
  );
}

export default App;
