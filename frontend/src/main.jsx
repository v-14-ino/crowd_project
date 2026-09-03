import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import IncidentDrilldown from './pages/IncidentDrilldown';
import TrackReport from './pages/TrackReport';
import ReportIssue from './ReportIssue';
import Login from './pages/Login';
import { getAuthToken } from './services/api';
import './index.css';
import './App.css';

const ProtectedRoute = ({ children }) => {
  const token = getAuthToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard/:incidentId" element={<ProtectedRoute><IncidentDrilldown /></ProtectedRoute>} />
        <Route path="/incidents" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/incidents/:incidentId" element={<ProtectedRoute><IncidentDrilldown /></ProtectedRoute>} />
        <Route path="/report" element={<ReportIssue />} />
        <Route path="/track" element={<TrackReport />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

