import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchIncident, fetchIncidents } from './services/api';
import './App.css';

function Incidents() {
  const { incidentId } = useParams();
  const [incidents, setIncidents] = useState([]);
  const [incidentDetails, setIncidentDetails] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);

      try {
        if (incidentId) {
          const detail = await fetchIncident(incidentId);
          setIncidentDetails(detail);
        } else {
          const list = await fetchIncidents(1, 50);
          setIncidents(list);
        }
      } catch (err) {
        setError(err?.detail || err.message || 'Failed to load incidents');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [incidentId]);

  if (loading) {
    return (
      <div className="app-shell">
        <main className="hero-card">
          <p>Loading incidents...</p>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-shell">
        <main className="hero-card">
          <p className="error-message">{error}</p>
          <Link className="nav-link" to="/incidents">Back to incidents</Link>
        </main>
      </div>
    );
  }

  if (incidentId && incidentDetails) {
    return (
      <div className="app-shell">
        <main className="hero-card">
          <nav className="page-nav">
            <Link className="nav-link" to="/">Home</Link>
            <Link className="nav-link" to="/report">Report an Issue</Link>
            <Link className="nav-link" to="/incidents">Incidents</Link>
          </nav>

          <h1>Incident {incidentDetails.incident_id}</h1>
          <p>Category: {incidentDetails.category}</p>
          <p>Issue Type: {incidentDetails.issue_type}</p>
          <p>Zone: {incidentDetails.zone}</p>
          <p>Status: {incidentDetails.status}</p>
          <p>Created: {new Date(incidentDetails.created_at).toLocaleString()}</p>
          <p>Updated: {new Date(incidentDetails.updated_at).toLocaleString()}</p>

          <div className="section-card">
            <h2>Reports</h2>
            <ul>
              {incidentDetails.reports.map((reportId) => (
                <li key={reportId}>{reportId}</li>
              ))}
            </ul>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <main className="hero-card">
        <nav className="page-nav">
          <Link className="nav-link" to="/">Home</Link>
          <Link className="nav-link" to="/report">Report an Issue</Link>
          <Link className="nav-link" to="/incidents">Incidents</Link>
        </nav>

        <h1>Incidents</h1>
        <p className="subtitle">Recent correlated incident groups.</p>

        <div className="section-card">
          <ul className="incident-list">
            {incidents.map((incident) => (
              <li key={incident.incident_id} className="incident-item">
                <Link to={`/incidents/${incident.incident_id}`}>{incident.incident_id}</Link>
                <div>{incident.category} / {incident.issue_type}</div>
                <div>Status: {incident.status}</div>
                <div>Created: {new Date(incident.created_at).toLocaleString()}</div>
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  );
}

export default Incidents;
