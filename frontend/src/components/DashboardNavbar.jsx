import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getAuthToken, setAuthToken } from '../services/api';

export default function DashboardNavbar({ backendStatus = 'Connected', onRefresh }) {
  const location = useLocation();
  const navigate = useNavigate();
  const token = getAuthToken();

  const handleLogout = () => {
    setAuthToken(null);
    navigate('/login');
  };

  const isCurrent = (path) => {
    if (path === '/' && (location.pathname === '/' || location.pathname === '/dashboard' || location.pathname === '/incidents')) {
      return true;
    }
    return location.pathname === path;
  };

  return (
    <header className="dashboard-header">
      <div className="header-left">
        <div className="municipality-brand">
          <div className="crest-icon">🏛️</div>
          <div>
            <div className="header-title">Municipal Operations Dashboard</div>
            <div className="header-subtitle">Crowd-Report Verification & Decision Support System</div>
          </div>
        </div>
      </div>

      <nav className="header-nav">
        <Link
          to="/dashboard"
          className={`nav-btn ${isCurrent('/dashboard') ? 'active' : ''}`}
        >
          📊 Officer Dashboard
        </Link>
        <Link
          to="/report"
          className={`nav-btn ${isCurrent('/report') ? 'active' : ''}`}
        >
          📝 Citizen Report Form
        </Link>
      </nav>

      <div className="header-right">
        <div className={`connection-pill ${backendStatus === 'Connected' ? 'online' : 'offline'}`}>
          <span className="dot"></span>
          <span>{backendStatus === 'Connected' ? 'Live System Online' : 'Backend Offline'}</span>
        </div>
        {onRefresh && (
          <button className="btn-refresh" onClick={onRefresh} title="Refresh data">
            🔄 Refresh
          </button>
        )}
        {token && (
          <button className="btn-logout" onClick={handleLogout} style={{ marginLeft: '10px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', padding: '0.4rem 0.75rem', borderRadius: '4px', cursor: 'pointer' }}>
            Logout
          </button>
        )}
      </div>
    </header>
  );
}
